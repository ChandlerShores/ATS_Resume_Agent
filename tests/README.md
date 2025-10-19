# Test Suite Documentation

## Overview

This directory contains all test files for the ATS Resume Agent. Tests are organized by type and purpose for easy navigation and execution.

## Directory Structure

```
tests/
├── unit/               # Unit tests for individual components
├── integration/        # End-to-end workflow tests
├── api/               # API endpoint tests
├── security/          # Security and penetration tests
└── fixtures/          # Test data and expected outputs
```

## Test Categories

### Unit Tests (`unit/`)
**Purpose**: Test individual components in isolation

**Planned Tests**:
- `test_jd_parser.py` - Job description parsing logic
- `test_rewriter.py` - Bullet rewriting logic
- `test_scorer.py` - Scoring algorithms
- `test_validator.py` - Validation rules

**Status**: To be implemented

---

### Integration Tests (`integration/`)
**Purpose**: Test complete workflows across multiple components

#### `test_full_workflow.py`
**Purpose**: End-to-end test of the complete state machine

**Usage**:
```bash
python tests/integration/test_full_workflow.py
```

**What it tests**:
- Complete 6-stage state machine execution
- LLM API integration
- Input/output validation
- Scoring and validation logic

**Requirements**:
- Valid `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in `.env`
- Internet connection for LLM API calls

**Expected runtime**: 30-60 seconds

#### `test_quick.py`
**Purpose**: Quick smoke test for basic functionality

**Usage**:
```bash
python tests/integration/test_quick.py
```

**What it tests**:
- Module imports
- State machine initialization
- Basic schema validation

**Expected runtime**: < 5 seconds

---

### API Tests (`api/`)
**Purpose**: Test FastAPI endpoints and HTTP functionality

#### `test_api_basic.py`
**Purpose**: Quick API health check and basic functionality

**Usage**:
```bash
# Start server first
python scripts/start_server.py

# In another terminal
python tests/api/test_api_basic.py
```

**What it tests**:
- `/health` endpoint
- `/api/test/process-sync` endpoint
- Basic request/response validation

#### `test_api_manual.py`
**Purpose**: Manual API testing with detailed output

**Usage**:
```bash
python tests/api/test_api_manual.py
```

**What it tests**:
- Request structure validation
- Response schema validation
- Error handling

#### `test_api.ps1` (PowerShell)
**Purpose**: Windows-specific API testing script

**Usage**:
```powershell
.\tests\api\test_api.ps1
```

---

### Security Tests (`security/`)
**Purpose**: Validate security controls and detect vulnerabilities

#### `test_penetration.py`
**Purpose**: Basic penetration testing

**Usage**:
```bash
python tests/security/test_penetration.py --api-url http://localhost:8000
```

**What it tests**:
- CORS configuration
- Rate limiting enforcement
- Input sanitization
- Request size limits
- Security headers
- Cost controls

#### `test_security_attacks.py`
**Purpose**: Advanced attack simulation

**Usage**:
```bash
python tests/security/test_security_attacks.py --api-url http://localhost:8000
```

**What it tests**:
- 40+ prompt injection techniques
- Rate limiting bypass attempts
- Input validation bypass methods
- Edge cases and boundaries

#### `test_input_validation.py`
**Purpose**: Input sanitization testing

**Usage**:
```bash
python tests/security/test_input_validation.py
```

**What it tests**:
- Malicious pattern detection
- HTML/script stripping
- Length limit enforcement
- Schema validation

#### `run_all_security_tests.py`
**Purpose**: Execute complete security test suite

**Usage**:
```bash
python tests/security/run_all_security_tests.py
```

**What it does**:
- Runs all security tests
- Generates comprehensive report
- Saves results to `tests/fixtures/security_results.json`

---

### Test Fixtures (`fixtures/`)
**Purpose**: Sample data for testing

#### `sample_input.json`
Example API request payload for testing

```json
{
  "role": "Senior Software Engineer",
  "jd_text": "...",
  "bullets": ["...", "..."],
  "settings": {"max_len": 30, "variants": 2}
}
```

#### `sample_output.json`
Example API response for validation

---

## Running Tests

### Run All Integration Tests
```bash
# Set API key
export OPENAI_API_KEY=sk-...

# Run full workflow
python tests/integration/test_full_workflow.py

# Run quick test
python tests/integration/test_quick.py
```

### Run API Tests
```bash
# Terminal 1: Start server
python scripts/start_server.py

# Terminal 2: Run tests
python tests/api/test_api_basic.py
```

### Run Security Tests
```bash
# With local server
python tests/security/run_all_security_tests.py --api-url http://localhost:8000

# Against production
python tests/security/run_all_security_tests.py --api-url https://your-app.onrender.com
```

---

## Test Requirements

### Environment Variables
```bash
# Required for integration tests
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=sk-ant-...

# Optional configuration
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
```

### Dependencies
All test dependencies are included in base installation:
```bash
pip install -e .
```

For development testing tools:
```bash
pip install -e .[dev]
```

---

## Writing New Tests

### Unit Test Template
```python
"""Unit tests for <component>."""

def test_component_functionality():
    """Test basic functionality."""
    from agents.component import Component
    
    component = Component()
    result = component.process(input_data)
    
    assert result is not None
    assert isinstance(result, ExpectedType)
```

### Integration Test Template
```python
"""Integration test for <workflow>."""

from orchestrator.state_machine import StateMachine
from schemas.models import JobInput

def test_workflow():
    """Test complete workflow."""
    sm = StateMachine()
    
    input_data = JobInput(
        role="Test Role",
        jd_text="Test JD",
        bullets=["Test bullet"]
    )
    
    result = sm.execute(input_data.model_dump())
    
    assert result["job_id"]
    assert len(result["results"]) > 0
```

---

## CI/CD Integration

### GitHub Actions
```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -e .[dev]
      - run: python tests/integration/test_quick.py
      - run: python tests/api/test_api_manual.py
```

---

## Troubleshooting

### Test Failures

**Issue**: `test_full_workflow.py` times out
**Solution**: Check API key, internet connection, or try faster model (`gpt-4o-mini`)

**Issue**: API tests fail with 404
**Solution**: Ensure server is running on correct port (8000)

**Issue**: Security tests show failures
**Solution**: Expected - tests check if security controls catch attacks

### Common Errors

```
ModuleNotFoundError: No module named 'agents'
```
**Solution**: Install package: `pip install -e .`

```
openai.AuthenticationError: Invalid API key
```
**Solution**: Check `.env` file has valid `OPENAI_API_KEY`

```
ConnectionRefusedError: [Errno 111] Connection refused
```
**Solution**: Start API server first: `python scripts/start_server.py`

---

## Test Coverage

To generate coverage reports (requires `.[dev]` install):
```bash
pytest tests/ --cov=agents --cov=orchestrator --cov=ops --cov=schemas --cov-report=html
```

View report:
```bash
open htmlcov/index.html
```

---

## Contributing

When adding new features:
1. Add unit tests in `tests/unit/`
2. Add integration tests in `tests/integration/` if needed
3. Update this README with new test documentation
4. Ensure all tests pass before committing

---

## Quick Reference

| Test Type | Command | Runtime |
|-----------|---------|---------|
| Quick Smoke Test | `python tests/integration/test_quick.py` | < 5s |
| Full Workflow | `python tests/integration/test_full_workflow.py` | 30-60s |
| API Health | `python tests/api/test_api_basic.py` | < 5s |
| Security Suite | `python tests/security/run_all_security_tests.py` | 2-5min |
| All Tests | Run each category separately | Varies |

---

## Future Improvements

- [ ] Add pytest configuration for test discovery
- [ ] Implement unit tests for all components
- [ ] Add performance benchmarking tests
- [ ] Create mock LLM client for faster testing
- [ ] Add database/persistence tests (when implemented)
- [ ] Implement load testing suite
- [ ] Add visual regression tests for frontend integration

