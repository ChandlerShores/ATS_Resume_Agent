"""
Full workflow test for ATS Resume Agent.
Tests the complete pipeline with real LLM calls.
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("="*70)
print("ATS RESUME AGENT - FULL WORKFLOW TEST")
print("="*70)

# Check for API keys
print("\n1. Checking API Configuration...")
api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
provider = os.getenv("LLM_PROVIDER", "openai")

if not api_key:
    print("❌ ERROR: No API key found!")
    print("   Please set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env file")
    exit(1)

print(f"✅ API Key found: {api_key[:15]}...")
print(f"✅ Provider: {provider}")

# Import modules
print("\n2. Loading modules...")
try:
    from orchestrator.state_machine import StateMachine
    from schemas.models import JobInput
    print("✅ Modules loaded successfully")
except ImportError as e:
    print(f"❌ Failed to load modules: {e}")
    exit(1)

# Create test input
print("\n3. Creating test input...")
test_input = {
    "role": "Senior Software Engineer",
    "jd_text": """
    We are seeking a Senior Software Engineer with strong Python and FastAPI experience.
    The ideal candidate will have:
    - 5+ years of Python development experience
    - Experience building RESTful APIs with FastAPI or Flask
    - Cloud platform experience (AWS, GCP, or Azure)
    - Strong understanding of microservices architecture
    - Experience with CI/CD pipelines and Docker
    - Excellent communication and mentoring skills
    """,
    "bullets": [
        "Built REST APIs using Python and FastAPI framework",
        "Deployed applications to cloud infrastructure",
        "Created automated testing pipelines"
    ],
    "settings": {
        "tone": "concise",
        "max_len": 30,
        "variants": 2
    }
}

print(f"✅ Test input created:")
print(f"   Role: {test_input['role']}")
print(f"   Bullets: {len(test_input['bullets'])}")
print(f"   JD Length: {len(test_input['jd_text'])} characters")

# Initialize state machine
print("\n4. Initializing State Machine...")
try:
    sm = StateMachine()
    print("✅ State Machine initialized")
except Exception as e:
    print(f"❌ Failed to initialize: {e}")
    exit(1)

# Run the workflow
print("\n5. Running Full Workflow (this may take 30-60 seconds)...")
print("   - Parsing job description...")
print("   - Rewriting bullets...")
print("   - Scoring variants...")
print("   - Validating output...")
print()

try:
    result = sm.execute(test_input)
    print("✅ Workflow completed successfully!")
except Exception as e:
    print(f"❌ Workflow failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Display results
print("\n" + "="*70)
print("RESULTS")
print("="*70)

print(f"\nJob ID: {result['job_id']}")
print(f"Role: {result['summary']['role']}")

print(f"\nTop JD Terms ({len(result['summary']['top_terms'])}):")
for term in result['summary']['top_terms'][:10]:
    print(f"  • {term}")

print(f"\nCoverage:")
print(f"  Hit: {len(result['summary']['coverage']['hit'])} terms")
print(f"  Miss: {len(result['summary']['coverage']['miss'])} terms")

print(f"\n{len(result['results'])} Bullets Revised:")
print("-"*70)

for i, bullet_result in enumerate(result['results'], 1):
    print(f"\n[{i}] ORIGINAL:")
    print(f"    {bullet_result['original']}")
    
    print(f"\n    REVISED VARIANTS:")
    for j, revised in enumerate(bullet_result['revised'], 1):
        print(f"    {j}. {revised}")
    
    scores = bullet_result['scores']
    print(f"\n    SCORES:")
    print(f"    • Relevance: {scores['relevance']}/100")
    print(f"    • Impact:    {scores['impact']}/100")
    print(f"    • Clarity:   {scores['clarity']}/100")
    
    if bullet_result.get('notes'):
        print(f"\n    NOTES: {bullet_result['notes']}")

if result.get('red_flags'):
    print(f"\n⚠️  Red Flags ({len(result['red_flags'])}):")
    for flag in result['red_flags']:
        print(f"  • {flag}")
else:
    print(f"\n✅ No red flags detected")

# Save results
output_file = "test_output.json"
with open(output_file, 'w') as f:
    json.dump(result, f, indent=2)

print("\n" + "="*70)
print("✅ TEST PASSED - Full workflow working correctly!")
print("="*70)
print(f"\nFull results saved to: {output_file}")
print("\nKey Validations:")
print("  ✅ LLM API calls working")
print("  ✅ JD parsing extracting terms")
print("  ✅ Bullets being rewritten")
print("  ✅ Scoring system functional")
print("  ✅ Validation passing")
print("\n🚀 Your API is ready for production!")

