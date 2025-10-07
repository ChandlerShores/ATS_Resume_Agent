"""State machine orchestrator for durable resume bullet revision workflow."""

import sys
import json
import argparse
from enum import Enum
from typing import Dict, Any, List
from pathlib import Path

from ops.logging import logger
from ops.ulid_gen import generate_job_id
from ops.hashing import compute_jd_hash
from ops.dlq import dlq
from ops.retry import PermanentError

from schemas.models import (
    JobInput,
    JobOutput,
    JobState,
    BulletResult,
    BulletDiff,
    Summary,
    LogEntry
)

from agents.jd_parser import JDParser
from agents.rewriter import Rewriter
from agents.scorer import Scorer
from agents.validator import Validator

from orchestrator.idempotency import idempotency_manager


class State(str, Enum):
    """State machine states."""
    INGEST = "INGEST"
    EXTRACT_SIGNALS = "EXTRACT_SIGNALS"
    REWRITE = "REWRITE"
    SCORE_SELECT = "SCORE_SELECT"
    VALIDATE = "VALIDATE"
    OUTPUT = "OUTPUT"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


class StateMachine:
    """
    Durable state machine for resume bullet revision workflow.
    
    Executes 6 states in sequence with logging, retries, and idempotency.
    """
    
    def __init__(self):
        self.jd_parser = JDParser()
        self.rewriter = Rewriter()
        self.scorer = Scorer()
        self.validator = Validator()
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
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
        state = JobState(
            job_id=job_input.job_id,
            input_data=job_input
        )
        
        current_state = State.INGEST
        
        try:
            # Execute state transitions
            while current_state not in [State.COMPLETED, State.FAILED]:
                if current_state == State.INGEST:
                    current_state = self._ingest(state)
                elif current_state == State.EXTRACT_SIGNALS:
                    current_state = self._extract_signals(state)
                elif current_state == State.REWRITE:
                    current_state = self._rewrite(state)
                elif current_state == State.SCORE_SELECT:
                    current_state = self._score_select(state)
                elif current_state == State.VALIDATE:
                    current_state = self._validate(state)
                elif current_state == State.OUTPUT:
                    current_state = self._output(state)
            
            if current_state == State.FAILED:
                raise RuntimeError("State machine ended in FAILED state")
            
            # Build final output
            return self._build_output(state)
        
        except Exception as e:
            # Log error and add to DLQ
            log_entry = logger.error(
                stage="state_machine",
                msg=f"Job failed: {str(e)}",
                job_id=state.job_id,
                error=str(e)
            )
            state.add_log(log_entry)
            
            dlq.add_entry(
                job_id=state.job_id,
                stage=current_state.value,
                reason=str(e),
                input_data=input_data
            )
            
            raise
    
    def _ingest(self, state: JobState) -> State:
        """
        INGEST state: Resolve JD, normalize text, compute hashes.
        
        Args:
            state: Current job state
            
        Returns:
            State: Next state
        """
        log_entry = logger.info(
            stage="INGEST",
            msg="Starting ingestion",
            job_id=state.job_id
        )
        state.add_log(log_entry)
        
        # Resolve JD text
        if state.input_data.jd_url:
            state.jd_text = self.jd_parser.fetch_jd_from_url(state.input_data.jd_url)
        elif state.input_data.jd_text:
            state.jd_text = state.input_data.jd_text
        else:
            raise ValueError("Either jd_text or jd_url must be provided")
        
        # Normalize JD
        state.jd_text = self.jd_parser.normalize_text(state.jd_text)
        
        # Compute JD hash
        state.jd_hash = compute_jd_hash(state.jd_text)
        
        # Normalize bullets (remove empties)
        state.normalized_bullets = [
            b.strip() for b in state.input_data.bullets if b.strip()
        ]
        
        if not state.normalized_bullets:
            raise ValueError("No valid bullets provided")
        
        # Check idempotency
        idem_key = idempotency_manager.compute_key(
            job_id=state.job_id,
            jd_hash=state.jd_hash,
            bullets=state.normalized_bullets,
            settings=state.input_data.settings.model_dump()
        )
        
        cached_result = idempotency_manager.get_cached_result(idem_key)
        if cached_result:
            log_entry = logger.info(
                stage="INGEST",
                msg="Returning cached result (idempotent)",
                job_id=state.job_id,
                idempotency_key=idem_key
            )
            state.add_log(log_entry)
            # Return cached result directly
            # For now, skip to OUTPUT with cached data
            # TODO: Properly handle cached results
        
        log_entry = logger.info(
            stage="INGEST",
            msg=f"Ingested {len(state.normalized_bullets)} bullets",
            job_id=state.job_id,
            jd_hash=state.jd_hash
        )
        state.add_log(log_entry)
        
        return State.EXTRACT_SIGNALS
    
    def _extract_signals(self, state: JobState) -> State:
        """
        EXTRACT_SIGNALS state: Parse JD and extract key terms.
        
        Args:
            state: Current job state
            
        Returns:
            State: Next state
        """
        log_entry = logger.info(
            stage="EXTRACT_SIGNALS",
            msg="Extracting JD signals",
            job_id=state.job_id
        )
        state.add_log(log_entry)
        
        # Parse JD
        state.jd_signals = self.jd_parser.parse(jd_text=state.jd_text)
        
        log_entry = logger.info(
            stage="EXTRACT_SIGNALS",
            msg=f"Extracted {len(state.jd_signals.top_terms)} key terms",
            job_id=state.job_id,
            top_terms=state.jd_signals.top_terms[:5]
        )
        state.add_log(log_entry)
        
        return State.REWRITE
    
    def _rewrite(self, state: JobState) -> State:
        """
        REWRITE state: Generate bullet variants.
        
        Args:
            state: Current job state
            
        Returns:
            State: Next state
        """
        log_entry = logger.info(
            stage="REWRITE",
            msg=f"Rewriting {len(state.normalized_bullets)} bullets",
            job_id=state.job_id
        )
        state.add_log(log_entry)
        
        # Rewrite all bullets
        state.raw_rewrites = self.rewriter.rewrite_all(
            bullets=state.normalized_bullets,
            role=state.input_data.role,
            jd_signals=state.jd_signals,
            metrics=state.input_data.metrics,
            extra_context=state.input_data.extra_context or "",
            max_words=state.input_data.settings.max_len,
            num_variants=state.input_data.settings.variants
        )
        
        total_variants = sum(len(variants) for variants in state.raw_rewrites.values())
        
        log_entry = logger.info(
            stage="REWRITE",
            msg=f"Generated {total_variants} variants",
            job_id=state.job_id,
            count=total_variants
        )
        state.add_log(log_entry)
        
        return State.SCORE_SELECT
    
    def _score_select(self, state: JobState) -> State:
        """
        SCORE_SELECT state: Score variants and compute coverage.
        
        Args:
            state: Current job state
            
        Returns:
            State: Next state
        """
        log_entry = logger.info(
            stage="SCORE_SELECT",
            msg="Scoring variants",
            job_id=state.job_id
        )
        state.add_log(log_entry)
        
        # Score each bullet's variants
        for original_bullet, variants in state.raw_rewrites.items():
            revised_texts = [v.text for v in variants]
            
            # Score the first variant (or could score all and pick best)
            # For now, return both variants with same scoring approach
            if variants:
                scores, explanation = self.scorer.score_variant(
                    original=original_bullet,
                    revised=variants[0].text,
                    role=state.input_data.role,
                    jd_signals=state.jd_signals
                )
                
                # Create bullet result
                bullet_result = BulletResult(
                    original=original_bullet,
                    revised=revised_texts,
                    scores=scores,
                    notes=variants[0].rationale,
                    diff=BulletDiff(removed=[], added_terms=[])  # Will be computed in validation
                )
                
                state.scored_results.append(bullet_result)
        
        # Compute coverage
        all_revised = []
        for result in state.scored_results:
            all_revised.extend(result.revised)
        
        coverage = self.scorer.compute_coverage(
            all_revised_bullets=all_revised,
            jd_signals=state.jd_signals
        )
        
        log_entry = logger.info(
            stage="SCORE_SELECT",
            msg=f"Scored {len(state.scored_results)} bullets",
            job_id=state.job_id,
            coverage_hit=len(coverage.hit),
            coverage_miss=len(coverage.miss)
        )
        state.add_log(log_entry)
        
        return State.VALIDATE
    
    def _validate(self, state: JobState) -> State:
        """
        VALIDATE state: Check grammar, active voice, PII, etc.
        
        Args:
            state: Current job state
            
        Returns:
            State: Next state
        """
        log_entry = logger.info(
            stage="VALIDATE",
            msg="Validating bullets",
            job_id=state.job_id
        )
        state.add_log(log_entry)
        
        all_flags = []
        
        # Validate each result
        for result in state.scored_results:
            for i, revised_text in enumerate(result.revised):
                validation_result, corrected_text = self.validator.validate(
                    original=result.original,
                    revised=revised_text,
                    apply_fixes=True
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
            flags=state.red_flags[:5]
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
        log_entry = logger.info(
            stage="OUTPUT",
            msg="Assembling output",
            job_id=state.job_id
        )
        state.add_log(log_entry)
        
        return State.COMPLETED
    
    def _build_output(self, state: JobState) -> Dict[str, Any]:
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
            all_revised_bullets=all_revised,
            jd_signals=state.jd_signals
        )
        
        # Build summary
        summary = Summary(
            role=state.input_data.role,
            top_terms=state.jd_signals.top_terms,
            coverage=coverage
        )
        
        # Convert logs
        log_entries = [LogEntry(**log) for log in state.logs]
        
        # Build output
        output = JobOutput(
            job_id=state.job_id,
            summary=summary,
            results=state.scored_results,
            red_flags=state.red_flags,
            logs=log_entries
        )
        
        return output.model_dump()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="ATS Resume Bullet Revisor"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to input JSON file"
    )
    parser.add_argument(
        "--out",
        default="out/result.json",
        help="Path to output JSON file"
    )
    
    args = parser.parse_args()
    
    # Load input
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)
    
    with open(input_path, 'r', encoding='utf-8') as f:
        input_data = json.load(f)
    
    # Run state machine
    try:
        sm = StateMachine()
        output = sm.execute(input_data)
        
        # Write output
        output_path = Path(args.out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)
        
        # Print summary
        print("\n" + "="*60)
        print("JOB COMPLETED SUCCESSFULLY")
        print("="*60)
        print(f"Job ID: {output['job_id']}")
        print(f"Role: {output['summary']['role']}")
        print(f"\nTop JD Terms: {', '.join(output['summary']['top_terms'][:10])}")
        print(f"\nCoverage:")
        print(f"  Hit: {len(output['summary']['coverage']['hit'])} terms")
        print(f"  Miss: {len(output['summary']['coverage']['miss'])} terms")
        
        if output['red_flags']:
            print(f"\nRed Flags ({len(output['red_flags'])}):")
            for flag in output['red_flags'][:5]:
                print(f"  - {flag}")
        
        print(f"\nResults written to: {args.out}")
        print("="*60 + "\n")
        
        sys.exit(0)
    
    except Exception as e:
        print("\n" + "="*60)
        print("JOB FAILED")
        print("="*60)
        print(f"Error: {str(e)}")
        print("="*60 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

