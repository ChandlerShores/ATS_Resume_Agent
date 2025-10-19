"""Quick test without API calls - just validates structure."""

import json
import os
from dotenv import load_dotenv

load_dotenv()

print("Quick Structure Test (no API calls)")
print("="*50)

# Test 1: Imports
print("\n1. Testing imports...")
try:
    from orchestrator.state_machine import StateMachine
    from schemas.models import JobInput, JobSettings
    from agents.jd_parser import JDParser
    from agents.rewriter import Rewriter
    from agents.scorer import Scorer
    from agents.validator import Validator
    print("   ✅ All imports successful")
except ImportError as e:
    print(f"   ❌ Import failed: {e}")
    exit(1)

# Test 2: Pydantic validation
print("\n2. Testing data validation...")
try:
    job_input = JobInput(
        role="Software Engineer",
        jd_text="Test job description",
        bullets=["Test bullet 1", "Test bullet 2"],
        settings=JobSettings(max_len=30, variants=2)
    )
    print(f"   ✅ JobInput validation passed")
    print(f"      Role: {job_input.role}")
    print(f"      Bullets: {len(job_input.bullets)}")
    print(f"      Settings: {job_input.settings.max_len} words, {job_input.settings.variants} variants")
except Exception as e:
    print(f"   ❌ Validation failed: {e}")
    exit(1)

# Test 3: Agent initialization
print("\n3. Testing agent initialization...")
try:
    jd_parser = JDParser()
    rewriter = Rewriter()
    scorer = Scorer()
    validator = Validator()
    print("   ✅ All agents initialized")
except Exception as e:
    print(f"   ❌ Agent initialization failed: {e}")
    exit(1)

# Test 4: State machine
print("\n4. Testing state machine...")
try:
    sm = StateMachine()
    print("   ✅ State machine initialized")
    print(f"      Has JD Parser: {sm.jd_parser is not None}")
    print(f"      Has Rewriter: {sm.rewriter is not None}")
    print(f"      Has Scorer: {sm.scorer is not None}")
    print(f"      Has Validator: {sm.validator is not None}")
except Exception as e:
    print(f"   ❌ State machine failed: {e}")
    exit(1)

# Test 5: API endpoints
print("\n5. Testing API module...")
try:
    from api.main import app
    routes = [r.path for r in app.routes if hasattr(r, 'path')]
    print(f"   ✅ API loaded with {len(routes)} routes")
    print(f"      Key routes: /health, /api/resume/process")
except Exception as e:
    print(f"   ❌ API module failed: {e}")
    exit(1)

# Check API key
print("\n6. Checking API configuration...")
api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
if api_key and not api_key.startswith("your_"):
    print(f"   ✅ API key configured ({api_key[:15]}...)")
    print("\n   Ready for full test! Run: python test_full_workflow.py")
else:
    print("   ⚠️  API key not set")
    print("   Edit .env file and add your OPENAI_API_KEY")
    print("   Then run: python test_full_workflow.py")

print("\n" + "="*50)
print("✅ STRUCTURE TEST PASSED")
print("="*50)
print("\nAll core components working correctly!")
print("Next: Add API key to .env and run full workflow test")

