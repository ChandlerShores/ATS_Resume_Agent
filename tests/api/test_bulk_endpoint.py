#!/usr/bin/env python3
"""Test bulk processing endpoint functionality."""

import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from api.main import app
from schemas.models import BulkProcessRequest, CandidateInput, JobSettings

client = TestClient(app)


class TestBulkProcessing:
    """Test bulk processing endpoint functionality."""
    
    def test_bulk_process_request_validation(self):
        """Test that bulk process request validation works correctly."""
        # Valid request
        valid_request = {
            "job_description": "Software Engineer role with Python experience",
            "candidates": [
                {
                    "candidate_id": "candidate_001",
                    "bullets": ["Built web applications using Python", "Led team of 5 developers"]
                },
                {
                    "candidate_id": "candidate_002", 
                    "bullets": ["Managed database operations", "Implemented CI/CD pipelines"]
                }
            ],
            "settings": {
                "max_len": 30,
                "variants": 1,
                "tone": "concise"
            }
        }
        
        # Test Pydantic model validation
        bulk_request = BulkProcessRequest(**valid_request)
        assert bulk_request.job_description == valid_request["job_description"]
        assert len(bulk_request.candidates) == 2
        assert bulk_request.candidates[0].candidate_id == "candidate_001"
        assert len(bulk_request.candidates[0].bullets) == 2
        assert bulk_request.settings.max_len == 30
    
    def test_bulk_process_request_validation_errors(self):
        """Test that bulk process request validation catches errors."""
        # Missing job_description
        with pytest.raises(ValueError):
            BulkProcessRequest(
                candidates=[CandidateInput(candidate_id="test", bullets=["test"])]
            )
        
        # Empty candidates list
        with pytest.raises(ValueError):
            BulkProcessRequest(
                job_description="test",
                candidates=[]
            )
        
        # Too many candidates
        candidates = [
            CandidateInput(candidate_id=f"candidate_{i}", bullets=["test"])
            for i in range(51)  # Max is 50
        ]
        with pytest.raises(ValueError):
            BulkProcessRequest(
                job_description="test",
                candidates=candidates
            )
        
        # Empty bullets
        with pytest.raises(ValueError):
            CandidateInput(candidate_id="test", bullets=[])
    
    def test_bulk_process_endpoint_structure(self):
        """Test that bulk process endpoint exists and has correct structure."""
        # Check that the endpoint exists
        routes = [route.path for route in app.routes if hasattr(route, 'path')]
        assert "/api/bulk/process" in routes
        assert "/api/bulk/status/{job_id}" in routes
        assert "/api/bulk/results/{job_id}" in routes
    
    @patch('api.main.StateMachine')
    def test_bulk_process_endpoint_mock(self, mock_state_machine):
        """Test bulk process endpoint with mocked state machine."""
        # Mock the state machine execution
        mock_result = MagicMock()
        mock_result.bullet_results = [
            {
                "original": "Built web applications using Python",
                "revised": "Developed scalable web applications using Python and FastAPI",
                "scores": {"relevance": 0.85, "impact": 0.90, "clarity": 0.88}
            }
        ]
        mock_result.coverage = {
            "overall_score": 0.75,
            "top_terms": ["Python", "FastAPI", "web applications"]
        }
        
        mock_sm_instance = MagicMock()
        mock_sm_instance.execute.return_value = mock_result
        mock_state_machine.return_value = mock_sm_instance
        
        # Test request
        test_request = {
            "job_description": "Software Engineer role with Python experience",
            "candidates": [
                {
                    "candidate_id": "candidate_001",
                    "bullets": ["Built web applications using Python"]
                }
            ],
            "settings": {
                "max_len": 30,
                "variants": 1
            }
        }
        
        # Make request
        response = client.post("/api/bulk/process", json=test_request)
        
        # Verify response structure
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "processing"
        assert data["total_candidates"] == 1
        assert data["processed_candidates"] == 0
        assert data["candidates"] == []
    
    def test_bulk_status_endpoint_structure(self):
        """Test that bulk status endpoint has correct structure."""
        # Test with non-existent job ID
        response = client.get("/api/bulk/status/non-existent-job-id")
        assert response.status_code == 404
        assert "Job not found" in response.json()["detail"]
    
    def test_bulk_results_endpoint_structure(self):
        """Test that bulk results endpoint has correct structure."""
        # Test with non-existent job ID
        response = client.get("/api/bulk/results/non-existent-job-id")
        assert response.status_code == 404
        assert "Job not found" in response.json()["detail"]
    
    def test_candidate_input_validation(self):
        """Test CandidateInput model validation."""
        # Valid input
        candidate = CandidateInput(
            candidate_id="test_candidate",
            bullets=["Built web applications", "Led development team"]
        )
        assert candidate.candidate_id == "test_candidate"
        assert len(candidate.bullets) == 2
        
        # Test bullet length limit (max 1000 chars)
        long_bullet = "x" * 1001
        candidate = CandidateInput(
            candidate_id="test",
            bullets=[long_bullet]
        )
        # Should be truncated to 1000 chars
        assert len(candidate.bullets[0]) == 1000
        
        # Test empty bullets are filtered out
        candidate = CandidateInput(
            candidate_id="test",
            bullets=["Valid bullet", "", "   ", "Another valid bullet"]
        )
        assert len(candidate.bullets) == 2
        assert candidate.bullets == ["Valid bullet", "Another valid bullet"]


if __name__ == "__main__":
    # Run basic validation tests
    test = TestBulkProcessing()
    
    print("Testing bulk processing models...")
    test.test_bulk_process_request_validation()
    print("[OK] Bulk process request validation passed")
    
    test.test_candidate_input_validation()
    print("[OK] Candidate input validation passed")
    
    test.test_bulk_process_endpoint_structure()
    print("[OK] Bulk endpoint structure verified")
    
    print("\n[OK] All bulk processing tests passed!")
    print("\nTo run full test suite:")
    print("pytest tests/api/test_bulk_endpoint.py -v")
