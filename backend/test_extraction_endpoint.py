#!/usr/bin/env python3
"""Test the extraction endpoint"""

import requests
import json

# Test data
test_request = {
    "document_text": "Apple Inc. reported revenue of $394.3 billion in fiscal year 2022.",
    "schema_definition": json.dumps({
        "type": "object",
        "properties": {
            "company": {"type": "string"},
            "revenue": {"type": "number"},
            "year": {"type": "integer"}
        }
    }),
    "system_prompt": "Extract company information from the text",
    "user_prompt_template": "Extract data from: {document_text}",
    "model_name": "gemini-2.0-flash",
    "examples": []
}

print("Testing extraction endpoint...")
print(f"Request: {json.dumps(test_request, indent=2)}")

try:
    response = requests.post(
        "http://localhost:8000/api/extract-data",
        json=test_request,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nResponse: {json.dumps(result, indent=2)}")
    else:
        print(f"\nError: {response.text}")
        
except Exception as e:
    print(f"\nConnection Error: {e}")
    print("Make sure the server is running on port 8000")