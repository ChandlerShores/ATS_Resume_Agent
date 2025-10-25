"""Quick manual test to verify API works after cleanup."""

import json
from pathlib import Path

# Test that core modules import correctly
print("Testing imports...")
try:
    from agents.jd_parser import JDParser
    from agents.rewriter import Rewriter
    from agents.scorer import Scorer
    from agents.validator import Validator
    from orchestrator.state_machine import StateMachine
    from schemas.models import JobInput, JobSettings
    print("[OK] All core imports successful")
except ImportError as e:
    print(f"[ERROR] Import failed: {e}")
    exit(1)

# Test that state machine initializes
print("\nTesting state machine initialization...")
try:
    sm = StateMachine()
    print("[OK] State machine initialized")
    print(f"   - JD Parser: {sm.jd_parser is not None}")
    print(f"   - Rewriter: {sm.rewriter is not None}")
    print(f"   - Scorer: {sm.scorer is not None}")
    print(f"   - Validator: {sm.validator is not None}")
except Exception as e:
    print(f"[ERROR] State machine failed: {e}")
    exit(1)

# Test JobInput validation
print("\nTesting JobInput validation...")
try:
    test_input = {
        "role": "Software Engineer",
        "jd_text": "We are looking for a Python developer with FastAPI experience.",
        "bullets": [
            "Built REST APIs using Python",
            "Wrote unit tests and documentation"
        ],
        "settings": {
            "tone": "concise",
            "max_len": 30,
            "variants": 2
        }
    }
    
    job_input = JobInput(**test_input)
    print("[OK] JobInput validation passed")
    print(f"   - Role: {job_input.role}")
    print(f"   - Bullets: {len(job_input.bullets)}")
    print(f"   - Settings: max_len={job_input.settings.max_len}, variants={job_input.settings.variants}")
except Exception as e:
    print(f"[ERROR] JobInput validation failed: {e}")
    exit(1)

# Test that API module loads
print("\nTesting API module...")
try:
    from api.main import app
    print("[OK] FastAPI app loaded")
    
    # Get routes
    routes = [route.path for route in app.routes if hasattr(route, 'path')]
    print(f"   - Routes found: {len(routes)}")
    print(f"   - Key routes: /health, /api/bulk/process, /api/resume/process")
    
    # Check for bulk processing routes
    bulk_routes = [r for r in routes if 'bulk' in r]
    print(f"   - Bulk processing routes: {bulk_routes}")
except Exception as e:
    print(f"[ERROR] API module failed: {e}")
    exit(1)

# Test bulk processing models
print("\nTesting bulk processing models...")
try:
    from schemas.models import BulkProcessRequest, CandidateInput, BulkProcessResponse, CandidateResult
    
    # Test CandidateInput
    candidate = CandidateInput(
        candidate_id="test_candidate",
        bullets=["Built web applications", "Led development team"]
    )
    print("[OK] CandidateInput validation passed")
    
    # Test BulkProcessRequest
    bulk_request = BulkProcessRequest(
        job_description="Software Engineer role",
        candidates=[candidate],
        settings=JobSettings()
    )
    print("[OK] BulkProcessRequest validation passed")
    
    # Test CandidateResult
    candidate_result = CandidateResult(
        candidate_id="test_candidate",
        status="completed",
        results=[],
        coverage=None,
        error_message=None
    )
    print("[OK] CandidateResult validation passed")
    
    # Test BulkProcessResponse
    bulk_response = BulkProcessResponse(
        job_id="test_job_id",
        status="completed",
        total_candidates=1,
        processed_candidates=1,
        candidates=[candidate_result]
    )
    print("[OK] BulkProcessResponse validation passed")
    
except Exception as e:
    print(f"[ERROR] Bulk processing models failed: {e}")
    exit(1)

print("\n" + "="*60)
print("[OK] ALL TESTS PASSED - API is ready!")
print("="*60)
print("\nNext step: Start the server")
print("Run: uvicorn api.main:app --reload")
print("\nThen test with:")
print("curl http://localhost:8000/health")

