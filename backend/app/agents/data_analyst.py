"""
Data Analyst Agent using Agno patterns.
Analyzes JSON data structure and creates detailed Excel generation specifications.
"""

import json
from typing import Dict, Any
from pathlib import Path

from agno.agent import Agent
from agno.tools.python import PythonTools
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class SheetSpecification(BaseModel):
    """Specification for a single Excel sheet."""
    name: str = Field(..., description="Sheet name (max 31 chars)")
    purpose: str = Field(..., description="Purpose and content description")
    data_source: List[str] = Field(..., description="JSON paths to data sources")
    columns: List[str] = Field(..., description="Column names in order")
    calculated_fields: Optional[List[str]] = Field(default=None, description="Fields to calculate")
    sorting: Optional[str] = Field(default=None, description="Sort order specification")
    formatting: Dict[str, Any] = Field(default_factory=dict, description="Formatting rules")
    visualizations: Optional[List[str]] = Field(default=None, description="Charts/visualizations to add")


class ExcelSpecification(BaseModel):
    """Complete specification for Excel generation."""
    summary: str = Field(..., description="Summary of the data and Excel structure")
    total_records: Dict[str, int] = Field(..., description="Record counts by category")
    sheets: List[SheetSpecification] = Field(..., description="Specifications for each sheet")
    global_formatting: Dict[str, Any] = Field(..., description="Global formatting rules")
    data_insights: List[str] = Field(..., description="Key insights found in the data")
    special_handling: List[str] = Field(..., description="Special data handling requirements")


class DataAnalystAgent(Agent):
    """
    Agent specialized in analyzing JSON data and creating Excel specifications.
    """

    def __init__(self, model, working_dir: Optional[str] = None):
        """Initialize data analyst agent."""
        
        work_dir = working_dir or "/tmp/agno_work"
        Path(work_dir).mkdir(parents=True, exist_ok=True)

        super().__init__(
            name="DataAnalyst",
            model=model,
            tools=[
                PythonTools(
                    base_dir=Path(work_dir),
                    pip_install=True,
                    run_code=True,
                    read_files=True,
                )
            ],
            description="You are an expert data analyst specializing in financial data analysis and Excel report design. You analyze complex JSON data structures and create detailed specifications for professional Excel reports.",
            goal="Analyze the provided JSON data thoroughly and create a comprehensive specification for how to structure it into a professional Excel workbook.",
            instructions=[
                "Read and analyze the JSON file completely using read_file",
                "Understand the complete data structure, including all nested objects and arrays",
                "Count the number of records in each data category",
                "Identify all unique values in categorical fields",
                "Detect data patterns (time series, hierarchical relationships, etc.)",
                "Analyze the financial metrics structure and categorization",
                "Create a detailed Excel structure plan that includes:",
                "  - Optimal sheet organization based on data categories",
                "  - Which metrics should be grouped together",
                "  - Opportunities for summary dashboards and KPIs",
                "  - Calculated fields that would add value (YoY growth, ratios, percentages)",
                "  - Data validation requirements",
                "  - Sorting and filtering recommendations",
                "Consider the end user (executives, analysts) when designing the structure",
                "Recommend professional formatting for each sheet type",
                "Identify any data quality issues or special handling needs",
                "Output a comprehensive ExcelSpecification as a structured response",
            ],
            expected_output="A detailed ExcelSpecification object containing sheet structures, formatting rules, and data insights that will guide the Excel generation process.",
            response_model=ExcelSpecification,  # This ensures structured output
            markdown=False,
            stream=False,
            show_tool_calls=True,
        )

    def analyze_and_plan(self, json_file_path: str) -> ExcelSpecification:
        """
        Analyze JSON data and create Excel specification.
        
        Args:
            json_file_path: Path to the JSON file to analyze
            
        Returns:
            ExcelSpecification object with detailed plan
        """
        prompt = f"""Analyze the financial data in {json_file_path} and create a comprehensive Excel specification.

Your analysis should:
1. Read the entire JSON file and understand its structure
2. Count records in each category
3. Identify patterns and relationships
4. Design an optimal Excel structure
5. Recommend formatting and visualizations
6. Suggest calculated fields and summaries

Focus on creating a specification that will result in a professional, executive-ready Excel report."""

        return self.run(prompt)