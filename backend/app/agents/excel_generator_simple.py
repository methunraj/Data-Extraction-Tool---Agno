"""
Simple Excel Generator Agent using Agno patterns.
Converts JSON data to clean, well-formatted Excel files without analysis.
"""

import json
import os
from pathlib import Path
from typing import Optional

from agno.agent import Agent
from agno.tools.file import FileTools
from agno.tools.python import PythonTools


class SimpleExcelGeneratorAgent(Agent):
    """
    Agent specialized in generating clean, well-formatted Excel files from JSON data.
    No calculations or analysis - just clean data presentation.
    """

    def __init__(self, model, working_dir: Optional[str] = None):
        """Initialize simple Excel generator agent."""

        # Set up working directory
        work_dir = working_dir or os.environ.get("AGENT_TEMP_DIR", "/tmp/agno_work")
        Path(work_dir).mkdir(parents=True, exist_ok=True)

        # Initialize with Python and File tools for Excel generation
        super().__init__(
            name="SimpleExcelGenerator",
            model=model,
            tools=[
                PythonTools(
                    base_dir=Path(work_dir),
                    pip_install=True,
                    run_code=True,
                    save_and_run=True,
                    run_files=True,
                    read_files=True,
                ),
                FileTools(base_dir=Path(work_dir)),
            ],
            description="You are an expert at converting JSON data to clean, well-formatted Excel files with proper sheet organization and professional formatting.",
            goal="Convert JSON data into a clean Excel file with properly organized sheets and professional formatting - no analysis or calculations needed.",
            instructions=[
                "Read the JSON file and understand its structure",
                "Handle markdown-wrapped JSON if present (```json\\n...\\n```)",
                "Install required packages: pandas and openpyxl",
                "Create a Python script that generates a clean Excel file:",
                "",
                "SHEET ORGANIZATION:",
                "- Company Overview: For company_identification data",
                "- One sheet per metric category in financial_metrics",
                "- Extraction Notes: For metadata and notes",
                "",
                "FORMATTING REQUIREMENTS:",
                "- Headers: Bold, white text on blue background (#4472C4)",
                "- Data rows: Alternating white and light gray (#F2F2F2)",
                "- Borders: Thin borders around all cells",
                "- Column widths: Auto-fit based on content",
                "- Number format: Currency values as $#,##0.00",
                "- Freeze panes: Keep headers visible when scrolling",
                "",
                "DATA HANDLING:",
                "- Flatten arrays to comma-separated strings",
                "- Keep all data as-is (no calculations)",
                "- Sort by year/date if such columns exist",
                "- Handle missing values gracefully",
                "",
                "Execute the script and verify the Excel file was created",
                "Report the file size and number of sheets created",
            ],
            expected_output="A clean, professionally formatted Excel file with data organized into logical sheets, proper formatting, and no calculations or analysis.",
            additional_context="""The JSON typically contains:
- company_identification: Company details (name, industry, location, etc.)
- financial_metrics: Array of financial data points with fields like metric_name, value, year, currency, etc.
- extraction_notes: Metadata about the extraction process

Each major section should be on its own sheet. Focus on clean presentation, not analysis.""",
            stream=False,
            show_tool_calls=True,
            add_history_to_messages=True,
            num_history_responses=10,
            markdown=False,
        )