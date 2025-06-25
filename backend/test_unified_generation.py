#!/usr/bin/env python3
"""
Test script to verify the unified generation endpoint is working correctly.
"""

import requests
import json

# Backend API URL
BASE_URL = "http://localhost:8000"

# Test data
test_request = {
    "user_intent": "Extract invoice information including invoice number, date, customer name, total amount, and line items",
    "model_name": "gemini-2.0-flash-exp",
    "temperature": 0.7,
    "include_examples": True,
    "example_count": 2,
    "include_reasoning": True
}

# Headers (if you have an API key set it here)
headers = {
    "Content-Type": "application/json",
    # "X-API-Key": "your-api-key-here"  # Uncomment and set if needed
}

print("Testing unified generation endpoint...")
print(f"Request: {json.dumps(test_request, indent=2)}")

try:
    response = requests.post(
        f"{BASE_URL}/api/generate-unified-config",
        json=test_request,
        headers=headers
    )
    
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("\nSuccess! Generated configuration:")
        print(f"- Schema: {len(result.get('schema', ''))} characters")
        print(f"- System Prompt: {len(result.get('system_prompt', ''))} characters")
        print(f"- User Prompt Template: {len(result.get('user_prompt_template', ''))} characters")
        print(f"- Examples: {len(result.get('examples', []))} examples")
        print(f"- Cost: ${result.get('cost', 0):.4f}")
        print(f"- Tokens Used: {result.get('tokens_used', 0)}")
        
        if result.get('reasoning'):
            print(f"\nReasoning: {result['reasoning'][:200]}...")
            
        print("\n--- Generated Schema Preview ---")
        schema_preview = result.get('schema', '')[:500]
        print(schema_preview + "..." if len(result.get('schema', '')) > 500 else schema_preview)
        
    else:
        print(f"\nError: {response.text}")
        
except Exception as e:
    print(f"\nConnection Error: {e}")
    print("Make sure the backend server is running on http://localhost:8000")