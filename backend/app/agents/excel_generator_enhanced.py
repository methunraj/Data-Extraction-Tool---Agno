"""
Enhanced Excel Generator with Data Analyst Agent.
Two-agent system for intelligent Excel generation based on data analysis.
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List

from agno.agent import Agent
from agno.tools.file import FileTools
from agno.tools.python import PythonTools
from pydantic import BaseModel, Field

from ..agents.models import get_transform_model


class SheetSpecification(BaseModel):
    """Specification for a single Excel sheet."""
    name: str = Field(..., description="Sheet name (max 31 chars)")
    purpose: str = Field(..., description="What data this sheet contains")
    data_source: str = Field(..., description="JSON path to data source (e.g., 'company_identification', 'financial_metrics')")
    columns: List[str] = Field(..., description="Column names to include in order")
    data_transformations: List[str] = Field(default_factory=list, description="Simple transformations like 'flatten context_qualifiers array'")
    sorting: Optional[str] = Field(default=None, description="Sort order (e.g., 'reporting_year DESC')")
    special_formatting: Optional[Dict[str, str]] = Field(default=None, description="Special column formatting (e.g., {'extracted_value': 'currency'})")


class ExcelSpecification(BaseModel):
    """Complete specification for Excel generation."""
    data_structure_summary: str = Field(..., description="Brief summary of the JSON structure")
    total_records: Dict[str, int] = Field(..., description="Record counts by section")
    sheets: List[SheetSpecification] = Field(..., description="Specifications for each sheet")
    formatting_rules: Dict[str, str] = Field(..., description="Global formatting rules")
    data_handling_notes: List[str] = Field(..., description="Notes on how to handle specific data types")


class DataAnalystAgent(Agent):
    """Agent that analyzes JSON data structure and creates Excel organization plan."""
    
    def __init__(self, model, working_dir: str):
        super().__init__(
            name="DataAnalyst",
            model=model,
            tools=[
                PythonTools(
                    base_dir=Path(working_dir),
                    run_code=True,
                    read_files=True,
                )
            ],
            description="You are a data structure analyst who examines JSON data and creates clear organization plans for Excel conversion.",
            goal="Analyze JSON structure and create a detailed plan for organizing data into Excel sheets - no calculations needed.",
            instructions=[
                "Read the JSON file and understand its complete structure",
                "Count how many records are in each section",
                "Identify all data types and nested structures",
                "Plan the Excel sheet organization:",
                "  - Decide how many sheets are needed",
                "  - Choose clear, descriptive sheet names",
                "  - Determine which JSON data goes to which sheet",
                "  - List all columns needed for each sheet",
                "  - Identify arrays that need flattening (like context_qualifiers)",
                "  - Note any special formatting needs (currency, dates)",
                "DO NOT suggest any calculations or analysis",
                "Focus only on data organization and presentation",
                "Create a clear specification that tells the next agent:",
                "  - Exactly which sheets to create",
                "  - What data to put on each sheet",
                "  - Which columns to include",
                "  - How to handle nested data",
                "Return a structured ExcelSpecification",
            ],
            response_model=ExcelSpecification,
            stream=False,
        )


class ExcelGeneratorEnhanced:
    """
    Enhanced Excel generator using two-agent approach:
    1. Data Analyst - Analyzes data and creates specifications
    2. Excel Generator - Implements the specifications
    """
    
    def __init__(self, model_id: Optional[str] = None, working_dir: Optional[str] = None):
        self.working_dir = working_dir or os.environ.get("AGENT_TEMP_DIR", "/tmp/agno_work")
        Path(self.working_dir).mkdir(parents=True, exist_ok=True)
        
        self.model = get_transform_model(model_id=model_id)
        
        # Initialize agents
        self.analyst = DataAnalystAgent(model=self.model, working_dir=self.working_dir)
        self.generator = self._create_generator_agent()
    
    def _create_generator_agent(self) -> Agent:
        """Create the Excel generator agent."""
        return Agent(
            name="ExcelImplementer",
            model=self.model,
            tools=[
                PythonTools(
                    base_dir=Path(self.working_dir),
                    pip_install=True,
                    run_code=True,
                    save_and_run=True,
                    read_files=True,
                ),
                FileTools(base_dir=Path(self.working_dir)),
            ],
            description="You are an expert Python developer who implements Excel generation plans exactly as specified.",
            goal="Follow the Excel specification from the Data Analyst to create a clean, well-formatted Excel file.",
            instructions=[
                "Install required packages: pandas, openpyxl",
                "Read the JSON data file",
                "Follow the provided specification EXACTLY",
                "For each sheet in the specification:",
                "  - Create the sheet with the exact name specified",
                "  - Extract data from the specified JSON path",
                "  - Include only the columns listed",
                "  - Apply any data transformations mentioned (like flattening arrays)",
                "  - Sort data if sorting is specified",
                "Apply clean, professional formatting:",
                "  - Headers: Bold, white text on blue background (#4472C4)",
                "  - Data rows: Alternating white and light gray (#F2F2F2)",
                "  - Borders: Around all cells",
                "  - Column widths: Auto-fit",
                "  - Number formatting: Apply special formatting from spec",
                "  - Freeze top row (headers)",
                "NO CALCULATIONS - just present the data as specified",
                "Save the Excel file and verify it was created",
            ],
            stream=False,
            show_tool_calls=True,
        )
    
    def generate(self, json_file_path: str, output_path: str) -> Dict[str, Any]:
        """Generate Excel using two-agent approach."""
        
        # Step 1: Analyze the data
        print("[ExcelGeneratorEnhanced] Step 1: Analyzing data structure...")
        
        analysis_prompt = f"""Analyze the JSON data structure in {json_file_path} and create a plan for Excel organization.

Your task:
1. Read and understand the complete JSON structure
2. Count how many records are in each section
3. Identify all the different data types and fields
4. Plan the sheet organization:
   - How many sheets are needed?
   - What should each sheet be named?
   - Which data goes on which sheet?
   - What columns should each sheet have?
5. Note any special data handling:
   - Arrays that need to be flattened (like context_qualifiers)
   - Fields that contain currency values
   - Date fields that need formatting

NO CALCULATIONS OR ANALYSIS - just organize the data logically into sheets."""

        try:
            spec = self.analyst.run(analysis_prompt)
            print(f"[ExcelGeneratorEnhanced] Analysis complete. Planning {len(spec.sheets)} sheets")
            
            # Convert to dict for the generator
            spec_dict = spec.model_dump() if hasattr(spec, 'model_dump') else spec
            
        except Exception as e:
            print(f"[ExcelGeneratorEnhanced] Analysis failed: {e}, using fallback")
            spec_dict = self._get_fallback_spec()
        
        # Step 2: Generate the Excel file
        print("[ExcelGeneratorEnhanced] Step 2: Generating Excel file...")
        
        generation_prompt = f"""Create a professional Excel file based on this specification:

SPECIFICATION:
{json.dumps(spec_dict, indent=2)}

INPUT: {json_file_path}
OUTPUT: {output_path}

Implementation requirements:
1. Install pandas and openpyxl
2. Read the JSON data (handle markdown wrappers if present)
3. Create each sheet EXACTLY as specified in the plan
4. Apply the formatting rules:
   - Blue headers (#4472C4) with white text
   - Alternating row colors (white and #F2F2F2)
   - Borders around all cells
   - Auto-fit columns
   - Currency formatting where specified
5. Handle data transformations mentioned in the spec (like flattening arrays)
6. NO CALCULATIONS - just present the data cleanly

The final Excel should be clean and professional with good formatting."""

        result = self.generator.run(generation_prompt)
        
        # Verify the file was created
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"[ExcelGeneratorEnhanced] Success! Excel file created: {file_size} bytes")
            return {
                "success": True,
                "specification": spec_dict,
                "output_path": output_path,
                "file_size": file_size
            }
        else:
            print("[ExcelGeneratorEnhanced] Excel file not found after generation")
            return {
                "success": False,
                "error": "Excel file was not created",
                "specification": spec_dict
            }
    
    def _get_fallback_spec(self) -> Dict[str, Any]:
        """Get a fallback specification if analysis fails."""
        return {
            "data_structure_summary": "JSON data with standard structure",
            "total_records": {"unknown": 0},
            "sheets": [
                {
                    "name": "Company Info",
                    "purpose": "Company identification data",
                    "data_source": "company_identification",
                    "columns": ["Field", "Value"],
                    "data_transformations": ["Convert to field-value pairs"],
                    "sorting": None,
                    "special_formatting": None
                },
                {
                    "name": "Financial Metrics",
                    "purpose": "All financial metrics data",
                    "data_source": "financial_metrics",
                    "columns": ["metric_category", "metric_name", "reporting_year", "extracted_value", "currency", "context_qualifiers"],
                    "data_transformations": ["Flatten context_qualifiers array to comma-separated string"],
                    "sorting": "reporting_year DESC",
                    "special_formatting": {"extracted_value": "currency"}
                },
                {
                    "name": "Extraction Notes",
                    "purpose": "Metadata and extraction notes",
                    "data_source": "extraction_notes",
                    "columns": ["Field", "Value"],
                    "data_transformations": ["Convert to field-value pairs", "Flatten any arrays"],
                    "sorting": None,
                    "special_formatting": None
                }
            ],
            "formatting_rules": {
                "header_color": "#4472C4",
                "header_text": "white",
                "alternate_row": "#F2F2F2",
                "borders": "all cells",
                "freeze_row": "1"
            },
            "data_handling_notes": ["Arrays should be flattened to comma-separated strings", "Currency values need $#,##0.00 format"]
        }