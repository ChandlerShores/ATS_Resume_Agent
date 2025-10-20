#!/usr/bin/env python3
"""Performance benchmark for the optimized pipeline."""

import json
import time
from pathlib import Path

# Add project root to path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from orchestrator.state_machine import StateMachine


def run_benchmark():
    """Run performance benchmark for the optimized pipeline."""
    
    # Test cases of different sizes
    test_cases = [
        {
            "name": "Small Job (3 bullets)",
            "bullets": [
                "Developed web applications using Python",
                "Worked on database optimization",
                "Collaborated with cross-functional teams"
            ]
        },
        {
            "name": "Medium Job (5 bullets)",
            "bullets": [
                "Developed web applications using Python and JavaScript",
                "Worked on database optimization and query performance",
                "Collaborated with cross-functional teams on product development",
                "Implemented automated testing and deployment processes",
                "Mentored junior developers and conducted code reviews"
            ]
        },
        {
            "name": "Large Job (10 bullets)",
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
            ]
        }
    ]
    
    # Common job description
    jd_text = """
    We are looking for a Software Engineer with experience in Python, React, and AWS.
    The ideal candidate will have strong problem-solving skills, experience with agile development,
    and knowledge of CI/CD pipelines. Experience with Docker, Kubernetes, and microservices
    architecture is preferred. The role involves full-stack development, database optimization,
    and working with cross-functional teams.
    """
    
    # Initialize state machine
    state_machine = StateMachine()
    
    print("🚀 ATS Resume Agent Pipeline Benchmark")
    print("=" * 50)
    
    results = []
    
    for test_case in test_cases:
        print(f"\n📊 Testing: {test_case['name']}")
        
        # Prepare input
        job_input = {
            "role": "Software Engineer",
            "jd_text": jd_text,
            "bullets": test_case["bullets"],
            "settings": {
                "tone": "concise",
                "max_len": 25,
                "variants": 1
            }
        }
        
        # Run benchmark
        start_time = time.time()
        try:
            result = state_machine.execute(job_input)
            end_time = time.time()
            
            execution_time = end_time - start_time
            bullets_processed = len(result["results"])
            
            # Calculate metrics
            bullets_per_second = bullets_processed / execution_time if execution_time > 0 else 0
            
            benchmark_result = {
                "test_case": test_case["name"],
                "bullets_count": bullets_processed,
                "execution_time": execution_time,
                "bullets_per_second": bullets_per_second,
                "success": True,
                "job_id": result["job_id"]
            }
            
            print(f"  ✅ Success: {bullets_processed} bullets in {execution_time:.2f}s")
            print(f"  📈 Rate: {bullets_per_second:.2f} bullets/second")
            
        except Exception as e:
            benchmark_result = {
                "test_case": test_case["name"],
                "bullets_count": len(test_case["bullets"]),
                "execution_time": 0,
                "bullets_per_second": 0,
                "success": False,
                "error": str(e)
            }
            
            print(f"  ❌ Failed: {str(e)}")
        
        results.append(benchmark_result)
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 BENCHMARK SUMMARY")
    print("=" * 50)
    
    successful_tests = [r for r in results if r["success"]]
    if successful_tests:
        avg_time = sum(r["execution_time"] for r in successful_tests) / len(successful_tests)
        avg_rate = sum(r["bullets_per_second"] for r in successful_tests) / len(successful_tests)
        
        print(f"✅ Successful tests: {len(successful_tests)}/{len(results)}")
        print(f"⏱️  Average execution time: {avg_time:.2f}s")
        print(f"📈 Average processing rate: {avg_rate:.2f} bullets/second")
        
        # Performance targets
        print(f"\n🎯 Performance Targets:")
        print(f"   - Target: < 20s for 10 bullets")
        print(f"   - Target: > 0.5 bullets/second")
        
        # Check if targets are met
        large_test = next((r for r in successful_tests if "10 bullets" in r["test_case"]), None)
        if large_test:
            if large_test["execution_time"] < 20:
                print(f"   ✅ Large job target met: {large_test['execution_time']:.2f}s < 20s")
            else:
                print(f"   ❌ Large job target missed: {large_test['execution_time']:.2f}s >= 20s")
        
        if avg_rate > 0.5:
            print(f"   ✅ Processing rate target met: {avg_rate:.2f} > 0.5 bullets/second")
        else:
            print(f"   ❌ Processing rate target missed: {avg_rate:.2f} <= 0.5 bullets/second")
    
    else:
        print("❌ No successful tests completed")
    
    # Save results
    output_file = Path("benchmark_results.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")
    
    return results


if __name__ == "__main__":
    try:
        results = run_benchmark()
        
        # Exit with error code if any tests failed
        failed_tests = [r for r in results if not r["success"]]
        if failed_tests:
            print(f"\n⚠️  {len(failed_tests)} test(s) failed")
            sys.exit(1)
        else:
            print("\n🎉 All benchmarks passed!")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n💥 Benchmark failed with error: {e}")
        sys.exit(1)
