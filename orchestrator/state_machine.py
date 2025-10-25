"""State machine orchestrator for durable resume bullet revision workflow."""

import argparse
import json
import sys
from enum import Enum
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from agents.jd_parser import JDParser
from agents.rewriter import Rewriter
from agents.scorer import Scorer
from agents.validator import Validator
from agents.fused_processor import FusedProcessor
from ops.logging import logger
from ops.ulid_gen import generate_job_id
from ops.redis_cache import get_jd_cache
from schemas.models import (
    BulletDiff,
    BulletResult,
    JobInput,
    JobOutput,
    JobState,
    LogEntry,
    Summary,
)


class State(str, Enum):
    """State machine states."""

    INGEST = "INGEST"
    EXTRACT_SIGNALS = "EXTRACT_SIGNALS"
    PROCESS = "PROCESS"
    VALIDATE = "VALIDATE"
    OUTPUT = "OUTPUT"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


class StateMachine:
    """
    Durable state machine for resume bullet revision workflow.

    Executes 6 states in sequence with logging and retries.
    """

    def __init__(self):
        self.jd_parser = JDParser()
        self.rewriter = Rewriter()
        self.scorer = Scorer()
        self.validator = Validator()
        self.fused_processor = FusedProcessor()
        self.redis_cache = get_jd_cache()

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the state machine.

        Args:
            input_data: Job input data

        Returns:
            Dict: Job output
        """
        # Parse and validate input
        job_input = JobInput(**input_data)

        # Generate job_id if missing
        if not job_input.job_id:
            job_input.job_id = generate_job_id()

        # Initialize state
        state = JobState(job_id=job_input.job_id, input_data=job_input)

        current_state = State.INGEST

        try:
            # Execute state transitions
            while current_state not in [State.COMPLETED, State.FAILED]:
                if current_state == State.INGEST:
                    current_state = self._ingest(state)
                elif current_state == State.EXTRACT_SIGNALS:
                    current_state = self._extract_signals(state)
                elif current_state == State.PROCESS:
                    current_state = self._process(state)
                elif current_state == State.VALIDATE:
                    current_state = self._validate(state)
                elif current_state == State.OUTPUT:
                    current_state = self._output(state)

            if current_state == State.FAILED:
                raise RuntimeError("State machine ended in FAILED state")

            # Build final output
            return self._build_output(state)

        except Exception as e:
            # Log error
            log_entry = logger.error(
                stage="state_machine",
                msg=f"Job failed: {str(e)}",
                job_id=state.job_id,
                error=str(e),
            )
            state.add_log(log_entry)
            raise

    def _ingest(self, state: JobState) -> State:
        """
        INGEST state: Resolve JD, normalize text, compute hashes.

        Args:
            state: Current job state

        Returns:
            State: Next state
        """
        log_entry = logger.info(stage="INGEST", msg="Starting ingestion", job_id=state.job_id)
        state.add_log(log_entry)

        # Get JD text (manual text input only)
        if not state.input_data.jd_text:
            raise ValueError("jd_text is required")
        
        state.jd_text = state.input_data.jd_text

        # Normalize JD
        state.jd_text = self.jd_parser.normalize_text(state.jd_text)

        # Compute JD hash
        state.jd_hash = str(hash(state.jd_text))

        # Normalize bullets (remove empties)
        state.normalized_bullets = [b.strip() for b in state.input_data.bullets if b.strip()]

        if not state.normalized_bullets:
            raise ValueError("No valid bullets provided")

        # Treat all bullets as achievements (simplified - no categorization)
        state.achievement_bullets = state.normalized_bullets
        state.skill_bullets = []
        state.metadata_bullets = []

        log_entry = logger.info(
            stage="INGEST",
            msg=f"Ingested {len(state.normalized_bullets)} bullets",
            job_id=state.job_id,
            jd_hash=state.jd_hash,
        )
        state.add_log(log_entry)

        return State.EXTRACT_SIGNALS

    def _extract_signals(self, state: JobState) -> State:
        """
        EXTRACT_SIGNALS state: Parse JD and extract key terms with Redis caching.

        Args:
            state: Current job state

        Returns:
            State: Next state
        """
        log_entry = logger.info(
            stage="EXTRACT_SIGNALS", msg="Extracting JD signals", job_id=state.job_id
        )
        state.add_log(log_entry)

        # Check cache first
        cached_signals = self.redis_cache.get(state.jd_hash)
        if cached_signals:
            state.jd_signals = cached_signals
            log_entry = logger.info(
                stage="EXTRACT_SIGNALS",
                msg=f"Retrieved cached JD signals with {len(state.jd_signals.top_terms)} terms",
                job_id=state.job_id,
                cache_hit=True
            )
            state.add_log(log_entry)
        else:
            # Parse JD using hybrid approach (local + LLM fallback)
            state.jd_signals = self.jd_parser.parse(jd_text=state.jd_text)
            
            # Cache result
            self.redis_cache.set(state.jd_hash, state.jd_signals)
            
            log_entry = logger.info(
                stage="EXTRACT_SIGNALS",
                msg=f"Extracted {len(state.jd_signals.top_terms)} key terms and cached result",
                job_id=state.job_id,
                top_terms=state.jd_signals.top_terms[:5],
                cache_hit=False
            )
            state.add_log(log_entry)

        return State.PROCESS

    def _process(self, state: JobState) -> State:
        """
        PROCESS state: Combined rewrite + score stage using fused processor.

        Args:
            state: Current job state

        Returns:
            State: Next state
        """
        log_entry = logger.info(
            stage="PROCESS",
            msg=f"Processing {len(state.achievement_bullets)} bullets with fused processor",
            job_id=state.job_id,
        )
        state.add_log(log_entry)

        # Use fused processor for batch rewrite + score
        state.scored_results = self.fused_processor.process_batch(
            bullets=state.achievement_bullets,
            role=state.input_data.role,
            jd_signals=state.jd_signals,
            settings=state.input_data.settings
        )

        # Add skill bullets and metadata bullets as-is
        from schemas.models import BulletResult, BulletScores, BulletDiff
        
        # Add skill bullets (preserve as-is with basic scores)
        for skill_bullet in state.skill_bullets:
            bullet_result = BulletResult(
                original=skill_bullet,
                revised=[skill_bullet],
                scores=BulletScores(relevance=50, impact=50, clarity=50),
                notes="Skill bullet preserved as-is",
                diff=BulletDiff(removed=[], added_terms=[])
            )
            state.scored_results.append(bullet_result)

        # Add metadata bullets (preserve as-is)
        for metadata_bullet in state.metadata_bullets:
            bullet_result = BulletResult(
                original=metadata_bullet,
                revised=[metadata_bullet],
                scores=BulletScores(relevance=50, impact=50, clarity=50),
                notes="Metadata bullet preserved as-is",
                diff=BulletDiff(removed=[], added_terms=[])
            )
            state.scored_results.append(bullet_result)

        log_entry = logger.info(
            stage="PROCESS",
            msg=f"Processed {len(state.scored_results)} bullets total",
            job_id=state.job_id,
            achievement_bullets=len(state.achievement_bullets),
            skill_bullets=len(state.skill_bullets),
            metadata_bullets=len(state.metadata_bullets),
        )
        state.add_log(log_entry)

        return State.VALIDATE

    def _validate(self, state: JobState) -> State:
        """
        VALIDATE state: Check PII and factual consistency.

        Args:
            state: Current job state

        Returns:
            State: Next state
        """
        log_entry = logger.info(stage="VALIDATE", msg="Validating bullets", job_id=state.job_id)
        state.add_log(log_entry)

        all_flags = []

        # Validate each result
        for result in state.scored_results:
            for i, revised_text in enumerate(result.revised):
                validation_result, corrected_text = self.validator.validate(
                    original=result.original,
                    revised=revised_text,
                    apply_fixes=True,
                    jd_signals=state.jd_signals,  # Pass JD signals for hard tool checking
                )

                # Update revised text if corrected
                result.revised[i] = corrected_text

                # Collect flags
                if validation_result.flags:
                    all_flags.extend(validation_result.flags)

        # Store unique flags
        state.red_flags = list(set(all_flags))

        log_entry = logger.info(
            stage="VALIDATE",
            msg=f"Validation complete, {len(state.red_flags)} flags raised",
            job_id=state.job_id,
            flags=state.red_flags[:5],
        )
        state.add_log(log_entry)

        return State.OUTPUT

    def _output(self, state: JobState) -> State:
        """
        OUTPUT state: Assemble final output.

        Args:
            state: Current job state

        Returns:
            State: Next state
        """
        log_entry = logger.info(stage="OUTPUT", msg="Assembling output", job_id=state.job_id)
        state.add_log(log_entry)

        return State.COMPLETED

    def _build_output(self, state: JobState) -> dict[str, Any]:
        """
        Build final output from state.

        Args:
            state: Final job state

        Returns:
            Dict: Job output
        """
        # Compute coverage
        all_revised = []
        for result in state.scored_results:
            all_revised.extend(result.revised)

        coverage = self.scorer.compute_coverage(
            all_revised_bullets=all_revised, jd_signals=state.jd_signals
        )

        # Build summary
        summary = Summary(
            role=state.input_data.role, top_terms=state.jd_signals.top_terms, coverage=coverage
        )

        # Convert logs
        log_entries = [LogEntry(**log) for log in state.logs]

        # Build output
        output = JobOutput(
            job_id=state.job_id,
            summary=summary,
            results=state.scored_results,
            red_flags=state.red_flags,
            logs=log_entries,
        )

        return output.model_dump()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="ATS Resume Bullet Revisor")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--out", default="out/result.json", help="Path to output JSON file")

    args = parser.parse_args()

    # Load input
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)

    with open(input_path, encoding="utf-8") as f:
        input_data = json.load(f)

    # Run state machine
    try:
        sm = StateMachine()
        output = sm.execute(input_data)

        # Write output
        output_path = Path(args.out)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)

        # Print summary
        print("\n" + "=" * 60)
        print("JOB COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print(f"Job ID: {output['job_id']}")
        print(f"Role: {output['summary']['role']}")
        print(f"\nTop JD Terms: {', '.join(output['summary']['top_terms'][:10])}")
        print("\nCoverage:")
        print(f"  Hit: {len(output['summary']['coverage']['hit'])} terms")
        print(f"  Miss: {len(output['summary']['coverage']['miss'])} terms")

        if output["red_flags"]:
            print(f"\nRed Flags ({len(output['red_flags'])}):")
            for flag in output["red_flags"][:5]:
                print(f"  - {flag}")

        print(f"\nResults written to: {args.out}")
        print("=" * 60 + "\n")

        sys.exit(0)

    except Exception as e:
        print("\n" + "=" * 60)
        print("JOB FAILED")
        print("=" * 60)
        print(f"Error: {str(e)}")
        print("=" * 60 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
