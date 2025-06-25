#!/usr/bin/env python3
"""
Simple test to validate basic migration components.
"""

import json
import sys
from pathlib import Path

def test_models_config():
    """Test that models.json is valid and contains expected models."""
    print("=== Testing models.json configuration ===")
    
    models_path = Path("app/config/models.json")
    if not models_path.exists():
        print("✗ models.json not found")
        return False
    
    try:
        with open(models_path) as f:
            config = json.load(f)
        
        print("✓ models.json loads successfully")
        
        # Check structure
        required_keys = ["version", "providers", "models"]
        for key in required_keys:
            if key not in config:
                print(f"✗ Missing required key: {key}")
                return False
        
        print("✓ models.json has required structure")
        
        # Check models
        models = config["models"]
        if not models:
            print("✗ No models defined")
            return False
        
        print(f"✓ Found {len(models)} models")
        
        # Check for key model types
        extraction_models = [m for m in models.values() if "extraction" in m.get("supportedIn", [])]
        agno_models = [m for m in models.values() if "agno" in m.get("supportedIn", [])]
        generation_models = [m for m in models.values() if "generation" in m.get("supportedIn", [])]
        
        print(f"✓ Extraction models: {len(extraction_models)}")
        print(f"✓ Agno models: {len(agno_models)}")
        print(f"✓ Generation models: {len(generation_models)}")
        
        # Check pricing
        for model_id, model in models.items():
            if "pricing" not in model:
                print(f"✗ Model {model_id} missing pricing")
                return False
        
        print("✓ All models have pricing information")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"✗ Error reading models.json: {e}")
        return False

def test_file_structure():
    """Test that all required files are present."""
    print("\n=== Testing file structure ===")
    
    required_files = [
        "app/config/models.json",
        "app/core/google_client.py",
        "app/core/config.py",
        "app/core/dependencies.py",
        "app/core/exceptions.py",
        "app/services/model_service.py",
        "app/services/extraction_service.py", 
        "app/services/generation_service.py",
        "app/services/cache_service.py",
        "app/services/token_service.py",
        "app/routers/extraction.py",
        "app/routers/generation.py",
        "app/routers/models.py",
        "app/routers/cache.py",
        "app/routers/agents.py",
        "app/schemas/extraction.py",
        "app/schemas/generation.py",
        "app/schemas/models.py",
        "app/schemas/common.py",
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("✗ Missing files:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        return False
    
    print(f"✓ All {len(required_files)} required files are present")
    return True

def test_requirements():
    """Test that requirements.txt has necessary dependencies."""
    print("\n=== Testing requirements.txt ===")
    
    req_path = Path("requirements.txt")
    if not req_path.exists():
        print("✗ requirements.txt not found")
        return False
    
    with open(req_path) as f:
        requirements = f.read()
    
    required_packages = [
        "google-genai",
        "watchdog",
        "tiktoken"
    ]
    
    missing_packages = []
    for package in required_packages:
        if package not in requirements:
            missing_packages.append(package)
    
    if missing_packages:
        print("✗ Missing required packages:")
        for package in missing_packages:
            print(f"  - {package}")
        return False
    
    print(f"✓ All required packages are in requirements.txt")
    return True

def test_syntax():
    """Test that Python files have valid syntax."""
    print("\n=== Testing Python syntax ===")
    
    python_files = [
        "app/core/google_client.py",
        "app/core/config.py", 
        "app/core/dependencies.py",
        "app/core/exceptions.py",
        "app/services/model_service.py",
        "app/services/extraction_service.py",
        "app/services/generation_service.py",
        "app/services/cache_service.py",
        "app/services/token_service.py",
        "app/routers/extraction.py",
        "app/routers/generation.py",
        "app/routers/models.py",
        "app/routers/cache.py",
        "app/routers/agents.py",
    ]
    
    syntax_errors = []
    
    for file_path in python_files:
        try:
            with open(file_path) as f:
                source = f.read()
            compile(source, file_path, 'exec')
        except SyntaxError as e:
            syntax_errors.append(f"{file_path}: {e}")
        except Exception as e:
            syntax_errors.append(f"{file_path}: {e}")
    
    if syntax_errors:
        print("✗ Syntax errors found:")
        for error in syntax_errors:
            print(f"  - {error}")
        return False
    
    print(f"✓ All {len(python_files)} Python files have valid syntax")
    return True

def main():
    """Run all basic tests."""
    print("🚀 Basic Migration Validation Tests")
    print("=" * 50)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Models Configuration", test_models_config),
        ("Requirements", test_requirements),
        ("Python Syntax", test_syntax),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"\n✗ {test_name} test failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All basic tests passed! Migration structure is correct.")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Set GOOGLE_API_KEY environment variable")
        print("3. Start the server: python -m uvicorn app.main:app --reload")
        print("4. Test the API endpoints at http://localhost:8000/docs")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed. Fix the issues above before proceeding.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)