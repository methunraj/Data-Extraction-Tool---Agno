#!/usr/bin/env python3
"""
Test the enhanced two-agent Excel generation approach.
"""

import json
import os
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.excel_generator_enhanced import ExcelGeneratorEnhanced
from app.agents.models import get_transform_model


def test_enhanced_generator():
    """Test the enhanced Excel generator with sample data."""
    
    # Create test data
    test_data = {
        "company_identification": {
            "official_company_name": "Test Corp",
            "industry": "Technology",
            "fiscal_year_end": "December 31",
            "headquarters": "San Francisco, CA"
        },
        "financial_metrics": [
            {
                "metric_category": "Revenue/Sales",
                "metric_name": "Total Revenue",
                "reporting_year": 2024,
                "extracted_value": 1000000,
                "currency": "USD"
            },
            {
                "metric_category": "Revenue/Sales", 
                "metric_name": "Total Revenue",
                "reporting_year": 2023,
                "extracted_value": 800000,
                "currency": "USD"
            },
            {
                "metric_category": "Profitability Metrics",
                "metric_name": "Net Income",
                "reporting_year": 2024,
                "extracted_value": 150000,
                "currency": "USD"
            },
            {
                "metric_category": "Profitability Metrics",
                "metric_name": "Net Income", 
                "reporting_year": 2023,
                "extracted_value": 100000,
                "currency": "USD"
            }
        ],
        "extraction_notes": {
            "total_pages": 50,
            "extraction_date": "2024-01-15",
            "confidence_score": 0.95
        }
    }
    
    # Create temp directory
    temp_dir = "/tmp/test_enhanced_excel"
    Path(temp_dir).mkdir(exist_ok=True)
    
    # Save test data
    json_path = os.path.join(temp_dir, "test_data.json")
    with open(json_path, "w") as f:
        json.dump(test_data, f, indent=2)
    
    # Output path
    output_path = os.path.join(temp_dir, "test_output.xlsx")
    
    print("Testing Enhanced Excel Generator...")
    print(f"Input: {json_path}")
    print(f"Output: {output_path}")
    
    # Initialize generator
    generator = ExcelGeneratorEnhanced(working_dir=temp_dir)
    
    # Generate Excel
    result = generator.generate(json_path, output_path)
    
    print("\nResult:")
    print(f"Success: {result.get('success')}")
    if result.get('success'):
        print(f"File size: {result.get('file_size')} bytes")
        print(f"Specification sheets: {len(result['specification']['sheets'])}")
        for sheet in result['specification']['sheets']:
            print(f"  - {sheet['name']}: {sheet['purpose']}")
    else:
        print(f"Error: {result.get('error')}")
    
    return result


if __name__ == "__main__":
    # Make sure we have API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("Error: GOOGLE_API_KEY not set")
        sys.exit(1)
    
    result = test_enhanced_generator()
    print("\nTest completed!")