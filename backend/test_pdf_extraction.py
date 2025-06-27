#!/usr/bin/env python3
"""Test PDF extraction with Agno multimodal capabilities"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Test direct Agno PDF handling
def test_agno_pdf():
    """Test Agno's native PDF handling"""
    from agno.agent import Agent
    from agno.models.google import Gemini
    from agno.media import File
    
    print("Testing Agno PDF extraction...")
    
    # Create a simple test agent
    agent = Agent(
        name="PDFExtractor",
        model=Gemini(
            id="gemini-2.0-flash",
            api_key=os.environ.get("GOOGLE_API_KEY")
        ),
        instructions=["Extract text and data from PDF documents"],
        markdown=True
    )
    
    # Test with a sample PDF URL
    test_pdf_url = "https://agno-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"
    
    print(f"\nTesting with PDF URL: {test_pdf_url}")
    
    response = agent.run(
        "Extract the title and first recipe name from this PDF",
        files=[File(url=test_pdf_url)]
    )
    
    print(f"\nResponse: {response.content}")
    
    return True

# Test the extraction endpoint
def test_extraction_endpoint():
    """Test the /api/extract-data endpoint with PDF"""
    import requests
    import json
    import base64
    
    print("\n\nTesting extraction endpoint with PDF...")
    
    # Create a simple test PDF content (base64 encoded)
    # This is just a placeholder - in real usage, you'd encode an actual PDF
    test_pdf_base64 = "JVBERi0xLjQKJeLjz9MKCjEgMCBvYmoKPDwKL1R5cGUgL0NhdGFsb2cKL1BhZ2VzIDIgMCBSCj4+CmVuZG9iagoKMiAwIG9iago8PAovVHlwZSAvUGFnZXMKL0tpZHMgWzMgMCBSXQovQ291bnQgMQo+PgplbmRvYmoKCjMgMCBvYmoKPDwKL1R5cGUgL1BhZ2UKL1BhcmVudCAyIDAgUgovUmVzb3VyY2VzIDw8Ci9Gb250IDw8Ci9GMSA8PAovVHlwZSAvRm9udAovU3VidHlwZSAvVHlwZTEKL0Jhc2VGb250IC9IZWx2ZXRpY2EKPj4KPj4KPj4KL01lZGlhQm94IFswIDAgNjEyIDc5Ml0KL0NvbnRlbnRzIDQgMCBSCj4+CmVuZG9iagoKNCAwIG9iago8PAovTGVuZ3RoIDQ0Cj4+CnN0cmVhbQpCVApxCjcwIDUwIFRECi9GMSAxMiBUZgooVGVzdCBQREYpIFRqCkVUClEKZW5kc3RyZWFtCmVuZG9iagoKeHJlZgowIDUKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDE1IDAwMDAwIG4gCjAwMDAwMDAwNjggMDAwMDAgbiAKMDAwMDAwMDEyNSAwMDAwMCBuIAowMDAwMDAwMzUzIDAwMDAwIG4gCnRyYWlsZXIKPDwKL1NpemUgNQovUm9vdCAxIDAgUgo+PgpzdGFydHhyZWYKNDQ5CiUlRU9G"
    
    request_data = {
        "document_file": {
            "mime_type": "application/pdf",
            "data": test_pdf_base64
        },
        "schema_definition": json.dumps({
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "content": {"type": "string"}
            }
        }),
        "system_prompt": "Extract data from the PDF",
        "user_prompt_template": "{document_text}",
        "model_name": "gemini-2.0-flash"
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/api/extract-data",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Success! Extracted: {result.get('extracted_json')}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Testing PDF extraction capabilities...\n")
    
    # Test 1: Direct Agno PDF handling
    try:
        test_agno_pdf()
    except Exception as e:
        print(f"Agno PDF test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Extraction endpoint
    print("\n" + "="*50)
    test_extraction_endpoint()
    
    print("\n✅ Tests complete!")