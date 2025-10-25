"""Tests for customer API key authentication."""

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


class TestCustomerAuthentication:
    """Test customer API key authentication."""

    def test_health_check_no_api_key_required(self):
        """Test that health check doesn't require API key."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "customers" in data

    def test_api_key_required_for_bulk_processing(self):
        """Test that API key is required for bulk processing."""
        response = client.post(
            "/api/bulk/process",
            json={
                "job_description": "Test job",
                "candidates": [{"candidate_id": "test", "bullets": ["Test bullet"]}],
            },
        )
        assert response.status_code == 401
        assert "API key required" in response.json()["detail"]

    def test_api_key_required_for_resume_processing(self):
        """Test that API key is required for resume processing."""
        response = client.post(
            "/api/resume/process",
            data={"resume_text": "Test bullet", "role": "Engineer", "jd_text": "Test job"},
        )
        assert response.status_code == 401
        assert "API key required" in response.json()["detail"]

    def test_invalid_api_key_rejected(self):
        """Test that invalid API key is rejected."""
        response = client.post(
            "/api/bulk/process",
            headers={"X-API-Key": "invalid_key"},
            json={
                "job_description": "Test job",
                "candidates": [{"candidate_id": "test", "bullets": ["Test bullet"]}],
            },
        )
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]

    def test_valid_api_key_accepted(self, monkeypatch):
        """Test that valid API key is accepted."""
        # Mock environment variable
        monkeypatch.setenv("CUSTOMER_API_KEYS", "test_customer:sk_test_123")

        # Create a new customer manager instance for testing
        from ops.customer_manager import CustomerManager

        test_manager = CustomerManager()

        # Test the validation directly
        customer_id = test_manager.validate_api_key("sk_test_123")
        assert customer_id == "test_customer"

    def test_usage_tracking_increments(self, monkeypatch):
        """Test that usage tracking increments correctly."""
        # Mock environment variable
        monkeypatch.setenv("CUSTOMER_API_KEYS", "test_customer:sk_test_123")

        # Create a new customer manager instance for testing
        from ops.customer_manager import CustomerManager

        test_manager = CustomerManager()

        # Track usage
        test_manager.track_usage("test_customer", 2)

        # Check usage stats
        stats = test_manager.get_usage_stats("test_customer")
        assert stats["customer_id"] == "test_customer"
        assert stats["today"]["bullets"] == 2
        assert stats["today"]["requests"] == 1


class TestCustomerManager:
    """Test CustomerManager class directly."""

    def test_load_customers_from_env(self, monkeypatch):
        """Test loading customers from environment variable."""
        monkeypatch.setenv("CUSTOMER_API_KEYS", "customer1:key1,customer2:key2")

        from ops.customer_manager import CustomerManager

        manager = CustomerManager()

        assert len(manager.customers) == 2
        assert "key1" in manager.customers
        assert "key2" in manager.customers
        assert manager.customers["key1"].customer_id == "customer1"
        assert manager.customers["key2"].customer_id == "customer2"

    def test_validate_api_key(self, monkeypatch):
        """Test API key validation."""
        monkeypatch.setenv("CUSTOMER_API_KEYS", "test_customer:sk_test_123")

        from ops.customer_manager import CustomerManager

        manager = CustomerManager()

        # Valid key
        customer_id = manager.validate_api_key("sk_test_123")
        assert customer_id == "test_customer"

        # Invalid key
        with pytest.raises(ValueError, match="Invalid API key"):
            manager.validate_api_key("invalid_key")

        # Empty key
        with pytest.raises(ValueError, match="API key is required"):
            manager.validate_api_key("")

    def test_track_usage(self, monkeypatch):
        """Test usage tracking."""
        monkeypatch.setenv("CUSTOMER_API_KEYS", "test_customer:sk_test_123")

        from ops.customer_manager import CustomerManager

        manager = CustomerManager()

        # Track usage
        manager.track_usage("test_customer", 5)

        # Check usage stats
        stats = manager.get_usage_stats("test_customer")
        assert stats["customer_id"] == "test_customer"
        assert stats["today"]["bullets"] == 5
        assert stats["today"]["requests"] == 1

    def test_get_all_customers_stats(self, monkeypatch):
        """Test getting stats for all customers."""
        monkeypatch.setenv("CUSTOMER_API_KEYS", "customer1:key1,customer2:key2")

        from ops.customer_manager import CustomerManager

        manager = CustomerManager()

        # Track usage for one customer
        manager.track_usage("customer1", 3)

        # Get all stats
        all_stats = manager.get_all_customers_stats()
        assert all_stats["total_customers"] == 2
        assert all_stats["total_requests_today"] == 1
        assert all_stats["total_bullets_today"] == 3
