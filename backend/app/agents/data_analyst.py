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
from app.prompts import load_prompt


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
            description=load_prompt("agents/data_analyst_description.txt"),
            goal=load_prompt("agents/data_analyst_goal.txt"),
            instructions=[
                "# Quick Analysis Phase",
                "1. Read the JSON file using read_file tool",
                "2. Understand the data structure - what types of data are present",
                "3. Count how many records exist for each type of data",
                "# Excel Structure Decision Phase",
                "4. Decide how to organize the Excel file",
                "5. For each sheet, determine columns and formatting",
                "6. Plan the formatting for professional appearance",
                "7. Identify any summary rows or totals needed",
                "# Output Generation",
                "8. Create the ExcelSpecification with all details"
            ],
            expected_output=load_prompt("agents/data_analyst_expected_output.txt"),
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
        prompt = load_prompt("agents/data_analyst_analysis_prompt.txt", json_file_path=json_file_path)

        return self.run(prompt)