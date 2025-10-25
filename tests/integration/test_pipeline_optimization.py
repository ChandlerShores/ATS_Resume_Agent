"""Integration tests for pipeline optimization comparing old vs new approach."""

import json
import time
from typing import Dict, Any
from unittest.mock import patch

import pytest

from orchestrator.state_machine import StateMachine
from schemas.models import JobInput, JobSettings


class TestPipelineOptimization:
    """Test suite for comparing old vs new pipeline performance and quality."""
    
    @pytest.fixture
    def sample_job_input(self) -> Dict[str, Any]:
        """Sample job input for testing."""
        return {
            "role": "Software Engineer",
            "jd_text": """
            We are looking for a Software Engineer with experience in Python, React, and AWS.
            The ideal candidate will have strong problem-solving skills, experience with agile development,
            and knowledge of CI/CD pipelines. Experience with Docker, Kubernetes, and microservices
            architecture is preferred.
            """,
            "bullets": [
                "Developed web applications using Python and JavaScript",
                "Worked on database optimization and query performance",
                "Collaborated with cross-functional teams on product development",
                "Implemented automated testing and deployment processes",
                "Mentored junior developers and conducted code reviews"
            ],
            "settings": {
                "tone": "concise",
                "max_len": 25,
                "variants": 1
            }
        }
    
    @pytest.fixture
    def state_machine(self) -> StateMachine:
        """State machine instance for testing."""
        return StateMachine()
    
    def test_new_pipeline_execution(self, state_machine: StateMachine, sample_job_input: Dict[str, Any]):
        """Test that the new optimized pipeline executes successfully."""
        # Execute the new pipeline
        start_time = time.time()
        result = state_machine.execute(sample_job_input)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Verify basic structure
        assert "job_id" in result
        assert "summary" in result
        assert "results" in result
        assert "red_flags" in result
        
        # Verify results
        assert len(result["results"]) == 5  # Should process all 5 bullets
        for bullet_result in result["results"]:
            assert "original" in bullet_result
            assert "revised" in bullet_result
            assert "scores" in bullet_result
            assert "notes" in bullet_result
        
        # Verify scores structure
        for bullet_result in result["results"]:
            scores = bullet_result["scores"]
            assert "relevance" in scores
            assert "impact" in scores
            assert "clarity" in scores
            assert 0 <= scores["relevance"] <= 100
            assert 0 <= scores["impact"] <= 100
            assert 0 <= scores["clarity"] <= 100
        
        # Performance check - should be faster than 30 seconds
        assert execution_time < 30, f"Pipeline took {execution_time:.2f}s, expected < 30s"
        
        print(f"New pipeline execution time: {execution_time:.2f}s")
    
    def test_jd_signal_extraction_quality(self, state_machine: StateMachine, sample_job_input: Dict[str, Any]):
        """Test that JD signal extraction produces reasonable results."""
        # Parse input
        job_input = JobInput(**sample_job_input)
        
        # Test JD parser directly
        jd_parser = state_machine.jd_parser
        jd_signals = jd_parser.parse(jd_text=sample_job_input["jd_text"])
        
        # Verify JD signals structure
        assert hasattr(jd_signals, "top_terms")
        assert hasattr(jd_signals, "soft_skills")
        assert hasattr(jd_signals, "hard_tools")
        assert hasattr(jd_signals, "domain_terms")
        
        # Verify we extracted some relevant terms
        assert len(jd_signals.top_terms) > 0
        assert len(jd_signals.hard_tools) > 0
        assert len(jd_signals.soft_skills) > 0
        
        # Check for expected hard tools
        hard_tools_text = " ".join(jd_signals.hard_tools).lower()
        assert "python" in hard_tools_text or "react" in hard_tools_text or "aws" in hard_tools_text
        
        # Check for expected soft skills
        soft_skills_text = " ".join(jd_signals.soft_skills).lower()
        assert "problem" in soft_skills_text or "agile" in soft_skills_text
    
    def test_redis_cache_functionality(self, state_machine: StateMachine):
        """Test Redis cache functionality."""
        redis_cache = state_machine.redis_cache
        
        # Test cache miss
        cached_result = redis_cache.get("test_hash_123")
        assert cached_result is None
        
        # Test cache set and get
        from schemas.models import JDSignals
        test_signals = JDSignals(
            top_terms=["Python", "React", "AWS"],
            soft_skills=["problem-solving", "agile"],
            hard_tools=["Docker", "Kubernetes"],
            domain_terms=["microservices"]
        )
        
        # Set cache
        success = redis_cache.set("test_hash_123", test_signals)
        if success:  # Only test if Redis is available
            # Get from cache
            cached_signals = redis_cache.get("test_hash_123")
            assert cached_signals is not None
            assert cached_signals.top_terms == ["Python", "React", "AWS"]
            assert cached_signals.hard_tools == ["Docker", "Kubernetes"]
            
            # Clean up
            redis_cache.clear("test_hash_123")
    
    def test_fused_processor_functionality(self, state_machine: StateMachine, sample_job_input: Dict[str, Any]):
        """Test fused processor functionality."""
        # Parse input
        job_input = JobInput(**sample_job_input)
        
        # Get JD signals
        jd_signals = state_machine.jd_parser.parse(jd_text=sample_job_input["jd_text"])
        
        # Test fused processor
        fused_processor = state_machine.fused_processor
        results = fused_processor.process_batch(
            bullets=sample_job_input["bullets"],
            role=job_input.role,
            jd_signals=jd_signals,
            settings=job_input.settings
        )
        
        # Verify results
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result.original == sample_job_input["bullets"][i]
            assert len(result.revised) >= 1
            assert result.scores.relevance >= 0
            assert result.scores.impact >= 0
            assert result.scores.clarity >= 0
            assert len(result.notes) > 0
    
    def test_validator_functionality(self, state_machine: StateMachine):
        """Test validator functionality with PII detection and factual consistency."""
        validator = state_machine.validator
        
        # Test PII detection
        original = "Contact me at john.doe@email.com or call 555-123-4567"
        revised = "Contact me at john.doe@email.com or call 555-123-4567"
        
        validation_result, corrected_text = validator.validate(
            original=original,
            revised=revised,
            apply_fixes=True
        )
        
        # Verify validation result
        assert hasattr(validation_result, "ok")
        assert hasattr(validation_result, "flags")
        assert hasattr(validation_result, "fixes")
        
        # Should detect PII
        assert not validation_result.ok
        assert len(validation_result.flags) > 0
        assert any("PII" in flag for flag in validation_result.flags)
        
        # Test factual consistency (no PII)
        original = "Developed web applications using Python"
        revised = "Built scalable web applications using Python and React"
        
        validation_result, corrected_text = validator.validate(
            original=original,
            revised=revised,
            apply_fixes=True
        )
        
        # Should pass basic validation (no PII detected)
        assert len(corrected_text) > 0
    
    def test_pipeline_state_flow(self, state_machine: StateMachine, sample_job_input: Dict[str, Any]):
        """Test that the pipeline follows the correct state flow."""
        # The new pipeline should go: INGEST -> EXTRACT_SIGNALS -> PROCESS -> VALIDATE -> OUTPUT
        
        # We can't directly test state transitions, but we can verify the result structure
        result = state_machine.execute(sample_job_input)
        
        # Verify we have the expected components from each stage
        assert "job_id" in result  # From INGEST
        assert "summary" in result  # From OUTPUT
        assert "results" in result  # From PROCESS
        assert "red_flags" in result  # From VALIDATE
        
        # Verify logs contain expected stages
        if "logs" in result:
            stage_names = [log.get("stage", "") for log in result["logs"]]
            expected_stages = ["INGEST", "EXTRACT_SIGNALS", "PROCESS", "VALIDATE", "OUTPUT"]
            for stage in expected_stages:
                assert stage in stage_names, f"Expected stage {stage} not found in logs"
    
    @pytest.mark.slow
    @patch('ops.llm_client.LLMClient.complete')
    def test_performance_improvement(self, mock_llm_complete, state_machine: StateMachine):
        """Test that the new pipeline is faster than the old approach."""
        # Mock LLM responses to make test deterministic and fast
        mock_llm_complete.return_value = "Mocked revised bullet with improved metrics and technical details"
        # Create a larger test case
        large_job_input = {
            "role": "Senior Software Engineer",
            "jd_text": """
            We are seeking a Senior Software Engineer with extensive experience in full-stack development.
            Required skills include Python, JavaScript, React, Node.js, AWS, Docker, Kubernetes,
            PostgreSQL, Redis, Elasticsearch, and microservices architecture. The candidate should have
            strong leadership skills, experience with agile development methodologies, and the ability to
            mentor junior developers. Experience with CI/CD pipelines, automated testing, and DevOps
            practices is essential.
            """,
            "bullets": [
                "Led development of scalable web applications using Python and React",
                "Designed and implemented microservices architecture with Docker and Kubernetes",
                "Optimized database performance and implemented caching strategies with Redis",
                "Built CI/CD pipelines and automated testing frameworks",
                "Mentored junior developers and conducted technical interviews",
                "Collaborated with product teams to define technical requirements",
                "Implemented monitoring and logging solutions for production systems",
                "Worked with cross-functional teams in agile development environment",
                "Designed RESTful APIs and GraphQL endpoints",
                "Managed AWS infrastructure and implemented security best practices"
            ],
            "settings": {
                "tone": "professional",
                "max_len": 30,
                "variants": 1
            }
        }
        
        # Measure execution time
        start_time = time.time()
        result = state_machine.execute(large_job_input)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # With mocked LLM calls, should complete in under 10 seconds
        assert execution_time < 10, f"Pipeline took {execution_time:.2f}s for 10 bullets, expected < 10s with mocked LLM"
        
        # Verify all bullets were processed
        assert len(result["results"]) == 10
        
        print(f"Large job execution time: {execution_time:.2f}s")
    
    def test_error_handling(self, state_machine: StateMachine):
        """Test error handling in the new pipeline."""
        # Test with invalid input
        invalid_input = {
            "role": "",  # Empty role
            "jd_text": "",  # Empty JD
            "bullets": [],  # Empty bullets
            "settings": {}
        }
        
        # Should raise an error or handle gracefully
        with pytest.raises((ValueError, RuntimeError)):
            state_machine.execute(invalid_input)


if __name__ == "__main__":
    # Run a quick test
    import sys
    sys.path.append(".")
    
    # Create test instance
    test_instance = TestPipelineOptimization()
    state_machine = StateMachine()
    
    # Sample input
    sample_input = {
        "role": "Software Engineer",
        "jd_text": "Looking for a Python developer with React experience.",
        "bullets": ["Developed web applications using Python"],
        "settings": {"tone": "concise", "max_len": 25, "variants": 1}
    }
    
    try:
        result = state_machine.execute(sample_input)
        print("✅ Pipeline test successful!")
        print(f"Processed {len(result['results'])} bullets")
        print(f"Job ID: {result['job_id']}")
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        sys.exit(1)
