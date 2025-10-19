#!/usr/bin/env python3
"""Simple API test"""

import requests
import json

def test_api():
    print("Testing API after fix...")
    
    try:
        response = requests.post(
            "http://localhost:8000/api/test/process-sync",
            json={
                "role": "Software Engineer",
                "jd_text": "Looking for a skilled developer with Python experience",
                "bullets": ["Built web applications using Python"],
                "settings": {"max_len": 30, "variants": 1}
            },
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("SUCCESS! API is working!")
            print(f"Job ID: {result.get('job_id', 'N/A')}")
            print(f"Number of results: {len(result.get('results', []))}")
            
            if result.get('results'):
                first_result = result['results'][0]
                print(f"Original bullet: {first_result.get('original', 'N/A')}")
                print(f"Revised bullets: {first_result.get('revised', [])}")
                print(f"Scores: {first_result.get('scores', {})}")
                
                # Show red flags if any
                red_flags = result.get('red_flags', [])
                if red_flags:
                    print(f"Red flags detected: {red_flags}")
                else:
                    print("No red flags detected")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_api()
