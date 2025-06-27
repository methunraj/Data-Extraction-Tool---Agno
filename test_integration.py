#!/usr/bin/env python3
"""
Integration test for the complete frontend-to-backend workflow
Tests PDF upload, prompt processing, and data transformation
"""

import asyncio
import aiohttp
import json
import tempfile
import os
from pathlib import Path

# Test configuration
FRONTEND_URL = "http://localhost:3000"
BACKEND_URL = "http://localhost:8000"

class IntegrationTester:
    def __init__(self):
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_backend_health(self):
        """Test backend health endpoint"""
        print("🔍 Testing backend health...")
        try:
            async with self.session.get(f"{BACKEND_URL}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Backend healthy: {data}")
                    return True
                else:
                    print(f"❌ Backend unhealthy: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Backend unreachable: {e}")
            return False

    async def test_frontend_health(self):
        """Test frontend health endpoint"""
        print("🔍 Testing frontend health...")
        try:
            async with self.session.get(f"{FRONTEND_URL}/api/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Frontend healthy: {data}")
                    return True
                else:
                    print(f"❌ Frontend unhealthy: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Frontend unreachable: {e}")
            return False

    async def test_config_generation(self):
        """Test configuration generation via PromptEngineerWorkflow"""
        print("🔍 Testing configuration generation...")
        try:
            payload = {
                "requirements": "Extract invoice data with vendor name, invoice number, total amount, date, and line items",
                "sampleDocuments": None,
                "apiKey": os.getenv("GOOGLE_API_KEY")
            }
            
            async with self.session.post(
                f"{FRONTEND_URL}/api/generate-config",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Config generated successfully")
                    print(f"   Schema keys: {list(data.get('config', {}).keys())}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Config generation failed: {response.status} - {error_text}")
                    return False
        except Exception as e:
            print(f"❌ Config generation error: {e}")
            return False

    async def test_file_upload_and_processing(self):
        """Test file upload and processing via DataTransformWorkflow"""
        print("🔍 Testing file upload and processing...")
        try:
            # Create a test PDF file
            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
                temp_file.write(b"""
INVOICE

Vendor: ACME Corporation
Invoice Number: INV-12345
Date: 2024-01-15
Total Amount: $1,250.00

Line Items:
- Widget A: $500.00
- Widget B: $750.00
                """)
                temp_path = temp_file.name

            # Prepare form data
            form_data = aiohttp.FormData()
            form_data.add_field('files', 
                              open(temp_path, 'rb'), 
                              filename='test_invoice.txt',
                              content_type='text/plain')
            form_data.add_field('request', 'Extract all invoice data from this document')
            
            if os.getenv("GOOGLE_API_KEY"):
                form_data.add_field('apiKey', os.getenv("GOOGLE_API_KEY"))

            async with self.session.post(
                f"{FRONTEND_URL}/api/upload-extract",
                data=form_data
            ) as response:
                if response.status == 200:
                    if response.headers.get('content-type', '').startswith('text/event-stream'):
                        print("✅ Streaming response received")
                        # Read streaming data
                        content = await response.text()
                        print(f"   Stream content length: {len(content)} chars")
                        return True
                    else:
                        data = await response.json()
                        print(f"✅ File processed successfully")
                        print(f"   Response keys: {list(data.keys())}")
                        return True
                else:
                    error_text = await response.text()
                    print(f"❌ File processing failed: {response.status} - {error_text}")
                    return False
        except Exception as e:
            print(f"❌ File processing error: {e}")
            return False
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass

    async def test_agno_processing(self):
        """Test Agno processing endpoint"""
        print("🔍 Testing Agno processing...")
        try:
            payload = {
                "extractedData": {
                    "vendor_name": "ACME Corp",
                    "invoice_number": "INV-12345",
                    "total_amount": 1250.00,
                    "date": "2024-01-15"
                },
                "fileName": "test_document.json",
                "llmProvider": "google",
                "model": "gemini-1.5-flash",
                "apiKey": os.getenv("GOOGLE_API_KEY"),
                "temperature": 0.1
            }
            
            async with self.session.post(
                f"{FRONTEND_URL}/api/agno-process",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Agno processing successful")
                    print(f"   Response keys: {list(data.keys())}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Agno processing failed: {response.status} - {error_text}")
                    return False
        except Exception as e:
            print(f"❌ Agno processing error: {e}")
            return False

    async def run_all_tests(self):
        """Run all integration tests"""
        print("🚀 Starting Integration Tests\n")
        
        results = {
            "backend_health": await self.test_backend_health(),
            "frontend_health": await self.test_frontend_health(),
            "config_generation": await self.test_config_generation(),
            "file_processing": await self.test_file_upload_and_processing(),
            "agno_processing": await self.test_agno_processing()
        }
        
        print(f"\n📊 Test Results:")
        print(f"================")
        passed = sum(results.values())
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All integration tests passed!")
            return True
        else:
            print("⚠️ Some tests failed. Check the logs above.")
            return False

async def main():
    """Main test runner"""
    print("IntelliExtract Frontend-Backend Integration Test")
    print("=" * 50)
    
    # Check environment
    if not os.getenv("GOOGLE_API_KEY"):
        print("⚠️ Warning: GOOGLE_API_KEY not set. Some tests may fail.")
        print("   Set it with: export GOOGLE_API_KEY=your_key_here")
    
    async with IntegrationTester() as tester:
        success = await tester.run_all_tests()
        return success

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n❌ Test runner failed: {e}")
        exit(1)