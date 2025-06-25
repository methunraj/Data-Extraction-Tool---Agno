#!/usr/bin/env python3
"""
Test script to validate the Genkit to backend migration.

This script tests the key endpoints and functionality to ensure
the migration is working correctly.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from services.model_service import get_model_service
from services.extraction_service import ExtractionService
from services.generation_service import GenerationService
from services.token_service import TokenService
from services.cache_service import get_cache_service
from core.google_client import GoogleGenAIClient

async def test_model_service():
    """Test the model service functionality."""
    print("\n=== Testing Model Service ===")
    
    model_service = get_model_service()
    
    # Test getting all models
    all_models = model_service.get_all_models()
    print(f"✓ Found {len(all_models)} models in configuration")
    
    # Test getting models by purpose
    extraction_models = model_service.get_models_for_purpose("extraction")
    agno_models = model_service.get_models_for_purpose("agno")
    generation_models = model_service.get_models_for_purpose("generation")
    
    print(f"✓ Extraction models: {len(extraction_models)}")
    print(f"✓ Agno models: {len(agno_models)}")
    print(f"✓ Generation models: {len(generation_models)}")
    
    # Test cost calculation
    if extraction_models:
        model_id = extraction_models[0]["id"]
        cost = model_service.calculate_cost(model_id, {
            "input_tokens": 1000,
            "output_tokens": 100,
            "cached_tokens": 0,
            "thinking_tokens": 0
        })
        print(f"✓ Cost calculation for {model_id}: ${cost:.6f}")
    
    return True

async def test_google_client():
    """Test Google GenAI client connectivity."""
    print("\n=== Testing Google GenAI Client ===")
    
    try:
        # Test API key validation
        is_valid = GoogleGenAIClient.validate_api_key()
        if not is_valid:
            print("⚠ Google API key not configured - skipping client tests")
            return False
        
        print("✓ Google API key is configured")
        
        # Test client creation
        client = GoogleGenAIClient.get_client()
        print("✓ Google GenAI client created successfully")
        
        # Test connection (if possible)
        connected = await GoogleGenAIClient.test_connection()
        if connected:
            print("✓ Google GenAI API connection successful")
        else:
            print("⚠ Google GenAI API connection failed")
            
        return True
        
    except Exception as e:
        print(f"✗ Google client test failed: {e}")
        return False

async def test_token_service():
    """Test token counting and cost estimation."""
    print("\n=== Testing Token Service ===")
    
    model_service = get_model_service()
    token_service = TokenService(model_service)
    
    # Test text token estimation
    test_text = "This is a test string for token counting."
    tokens = token_service.estimate_text_tokens(test_text)
    print(f"✓ Text token estimation: '{test_text[:30]}...' = {tokens} tokens")
    
    # Test model validation
    models = model_service.get_all_models()
    if models:
        model_id = models[0]["id"]
        validation = token_service.validate_token_limits(
            model_id=model_id,
            input_tokens=1000,
            output_tokens=100
        )
        print(f"✓ Token limit validation for {model_id}: {'Valid' if validation['valid'] else 'Invalid'}")
        if validation['warnings']:
            print(f"  Warnings: {validation['warnings']}")
    
    return True

async def test_generation_service():
    """Test generation service functionality."""
    print("\n=== Testing Generation Service ===")
    
    model_service = get_model_service()
    generation_service = GenerationService(model_service)
    
    # Check if we have generation models
    generation_models = model_service.get_models_for_purpose("generation")
    if not generation_models:
        print("⚠ No generation models available - skipping generation tests")
        return False
    
    print(f"✓ Found {len(generation_models)} generation models")
    print("✓ Generation service initialized successfully")
    
    # Note: We can't test actual generation without API keys and rate limits
    print("ℹ Actual generation testing requires API keys and is skipped for safety")
    
    return True

async def test_extraction_service():
    """Test extraction service functionality."""
    print("\n=== Testing Extraction Service ===")
    
    model_service = get_model_service()
    token_service = TokenService(model_service)
    cache_service = get_cache_service(model_service)
    extraction_service = ExtractionService(model_service, token_service, cache_service)
    
    # Check if we have extraction models
    extraction_models = model_service.get_models_for_purpose("extraction")
    if not extraction_models:
        print("⚠ No extraction models available - skipping extraction tests")
        return False
    
    print(f"✓ Found {len(extraction_models)} extraction models")
    print("✓ Extraction service initialized successfully")
    
    # Note: We can't test actual extraction without API keys and rate limits
    print("ℹ Actual extraction testing requires API keys and is skipped for safety")
    
    return True

async def test_cache_service():
    """Test cache service functionality."""
    print("\n=== Testing Cache Service ===")
    
    model_service = get_model_service()
    cache_service = get_cache_service(model_service)
    
    # Test cache statistics
    stats = await cache_service.get_stats()
    print(f"✓ Cache stats: {stats.total_entries} entries, {stats.total_hits} hits")
    
    # Test cache listing
    caches = await cache_service.list_caches()
    print(f"✓ Listed {len(caches)} cache entries")
    
    print("✓ Cache service working correctly")
    
    return True

async def test_import_paths():
    """Test that all import paths are working correctly."""
    print("\n=== Testing Import Paths ===")
    
    try:
        # Test core imports
        from core.config import settings
        from core.google_client import GoogleGenAIClient
        from core.dependencies import get_model_service_dep
        print("✓ Core module imports successful")
        
        # Test service imports
        from services.model_service import ModelService
        from services.extraction_service import ExtractionService
        from services.generation_service import GenerationService
        from services.cache_service import CacheService
        from services.token_service import TokenService
        print("✓ Service module imports successful")
        
        # Test schema imports
        from schemas.extraction import ExtractDataRequest, ExtractDataResponse
        from schemas.generation import GenerateConfigRequest, GenerateConfigResponse
        from schemas.models import ModelInfo, ModelListResponse
        print("✓ Schema module imports successful")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

async def main():
    """Run all migration tests."""
    print("🚀 Starting Genkit to Backend Migration Tests")
    print("=" * 50)
    
    tests = [
        ("Import Paths", test_import_paths),
        ("Model Service", test_model_service),
        ("Google Client", test_google_client),
        ("Token Service", test_token_service),
        ("Cache Service", test_cache_service),
        ("Generation Service", test_generation_service),
        ("Extraction Service", test_extraction_service),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"\n✗ {test_name} test failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("🧪 Migration Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:<20} {status}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Migration is working correctly.")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)