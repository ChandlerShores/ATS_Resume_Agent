#!/usr/bin/env python3
"""
Critical import test to catch deployment issues.

This test verifies that all critical modules can be imported without errors.
Failures here would prevent the application from starting on Render.com.
"""


def test_critical_imports():
    """Test that all critical modules can be imported."""

    # Test core modules
    try:
        from agents.fused_processor import FusedProcessor

        assert FusedProcessor is not None
    except Exception as e:
        raise AssertionError(f"Failed to import FusedProcessor: {e}")

    try:
        from agents.jd_parser import JDParser

        assert JDParser is not None
    except Exception as e:
        raise AssertionError(f"Failed to import JDParser: {e}")

    try:
        from agents.validator import Validator

        assert Validator is not None
    except Exception as e:
        raise AssertionError(f"Failed to import Validator: {e}")

    try:
        from orchestrator.state_machine import StateMachine

        assert StateMachine is not None
    except Exception as e:
        raise AssertionError(f"Failed to import StateMachine: {e}")

    # Test API
    try:
        from api.main import app

        assert app is not None
    except Exception as e:
        raise AssertionError(f"Failed to import FastAPI app: {e}")

    # Test operations modules
    try:
        from ops.customer_manager import customer_manager

        assert customer_manager is not None
    except Exception as e:
        raise AssertionError(f"Failed to import customer_manager: {e}")

    try:
        from ops.cost_controller import cost_controller

        assert cost_controller is not None
    except Exception as e:
        raise AssertionError(f"Failed to import cost_controller: {e}")

    try:
        from ops.logging import logger

        assert logger is not None
    except Exception as e:
        raise AssertionError(f"Failed to import logger: {e}")

    try:
        from ops.input_sanitizer import InputSanitizer

        assert InputSanitizer is not None
    except Exception as e:
        raise AssertionError(f"Failed to import InputSanitizer: {e}")

    try:
        from ops.security_monitor import security_monitor

        assert security_monitor is not None
    except Exception as e:
        raise AssertionError(f"Failed to import security_monitor: {e}")

    try:
        from ops.simple_rate_limiter import check_rate_limit

        assert check_rate_limit is not None
    except Exception as e:
        raise AssertionError(f"Failed to import check_rate_limit: {e}")

    # Test schemas
    try:
        from schemas.models import (
            BulletResult,
            JobInput,
            JobOutput,
        )

        assert JobInput is not None
        assert JobOutput is not None
        assert BulletResult is not None
    except Exception as e:
        raise AssertionError(f"Failed to import schema models: {e}")

    print("✅ All critical imports successful!")


def test_can_instantiate_state_machine():
    """Test that we can instantiate the StateMachine."""
    try:
        from orchestrator.state_machine import StateMachine

        sm = StateMachine()
        assert sm is not None
        assert hasattr(sm, "jd_parser")
        assert hasattr(sm, "fused_processor")
        assert hasattr(sm, "validator")
        assert hasattr(sm, "redis_cache")
        assert hasattr(sm, "scorer")
        print("✅ StateMachine instantiation successful!")
    except Exception as e:
        raise AssertionError(f"Failed to instantiate StateMachine: {e}")


def test_can_create_api_app():
    """Test that we can create the FastAPI app instance."""
    try:
        from api.main import app

        assert app is not None
        assert hasattr(app, "router")
        print("✅ FastAPI app creation successful!")
    except Exception as e:
        raise AssertionError(f"Failed to create FastAPI app: {e}")


if __name__ == "__main__":
    test_critical_imports()
    test_can_instantiate_state_machine()
    test_can_create_api_app()
    print("\n🎉 All import tests passed!")
