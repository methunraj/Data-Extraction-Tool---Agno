#!/usr/bin/env python3
"""Test that model selection is properly passed from frontend to backend"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_generate_unified_config():
    """Test model passing in generate-unified-config endpoint"""
    print("=== Testing generate-unified-config ===")
    
    test_models = ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"]
    
    for model in test_models:
        print(f"\nTesting with model: {model}")
        
        request_data = {
            "user_intent": "Extract company names from documents",
            "model_name": model,
            "temperature": 0.7,
            "include_examples": True,
            "example_count": 2
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/generate-unified-config",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print("✅ Success - Check server logs for model usage")
            else:
                print(f"❌ Error: {response.text[:200]}")
                
        except Exception as e:
            print(f"❌ Connection error: {e}")

def test_extract_data():
    """Test model passing in extract-data endpoint"""
    print("\n\n=== Testing extract-data ===")
    
    test_models = ["gemini-2.5-flash", "gemini-2.0-flash"]
    
    for model in test_models:
        print(f"\nTesting with model: {model}")
        
        request_data = {
            "document_text": "Apple Inc. revenue was $394 billion in 2022.",
            "model_name": model,
            "schema_definition": json.dumps({
                "type": "object",
                "properties": {
                    "company": {"type": "string"},
                    "revenue": {"type": "number"}
                }
            }),
            "system_prompt": "Extract data from text",
            "user_prompt_template": "{document_text}"
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/extract-data",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Success - Model used: {result.get('model_used')}")
            else:
                print(f"❌ Error: {response.text[:200]}")
                
        except Exception as e:
            print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    print("Testing model parameter passing...")
    print("Make sure the server is running and check server logs for model usage\n")
    
    test_generate_unified_config()
    test_extract_data()
    
    print("\n\n✅ Tests complete - Check server console for model logging")