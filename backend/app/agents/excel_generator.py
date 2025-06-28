"""
Excel Generator Agent using Agno patterns.
Converts JSON data to professional Excel files.
"""

import json
import os
from pathlib import Path
from typing import Optional

from agno.agent import Agent
from agno.tools.file import FileTools
from agno.tools.python import PythonTools


class ExcelGeneratorAgent(Agent):
    """
    Agent specialized in generating Excel files from JSON data.
    """

    def __init__(self, model, working_dir: Optional[str] = None):
        """Initialize Excel generator agent."""

        # Set up working directory
        work_dir = working_dir or os.environ.get("AGENT_TEMP_DIR", "/tmp/agno_work")
        Path(work_dir).mkdir(parents=True, exist_ok=True)

        # Initialize with Python and File tools for Excel generation
        super().__init__(
            name="ExcelGenerator",
            model=model,
            tools=[
                PythonTools(
                    base_dir=Path(work_dir),
                    pip_install=True,  # Allow installing pandas/openpyxl
                    run_code=True,  # Allow running code directly
                    save_and_run=True,  # Save code to file and run it
                    run_files=True,  # Allow running saved files
                    read_files=True,  # Allow reading files
                ),
                FileTools(base_dir=Path(work_dir)),
            ],
            description="You are an expert data engineer specialized in converting JSON data to professional Excel files with robust data format detection and cleaning capabilities.",
            goal="Convert the provided JSON financial data into a well-formatted Excel file with multiple sheets, each containing specific data categories.",
            instructions=[
                "You are an expert at multi-step tasks involving file processing and Python execution.",
                "ALWAYS start by reading and analyzing the input JSON file structure",
                "Detect if the JSON is wrapped in markdown format (```json\\n...\\n```)",
                "If markdown-wrapped: strip the wrapper and parse the clean JSON",
                "If pure JSON: parse directly",
                "Handle any JSON parsing errors gracefully with detailed error messages",
                "Complete ALL steps in sequence without stopping:",
                "1. Install required packages: pandas and openpyxl using pip_install_package",
                "2. Read the complete JSON file from the provided file path using read_file",
                "3. Analyze and clean the JSON structure - remove markdown wrappers if present",
                "4. Write a complete Python script using save_to_file_and_run that:",
                "   - Reads the JSON file as text first",
                "   - Detects format and cleans data (removes ```json\\n and \\n``` if present)",
                "   - Parses the cleaned JSON properly",
                "   - Creates an Excel workbook with multiple sheets",
                "   - Handles nested structures properly (flatten context arrays, etc.)",
                "   - Saves to the specified output path",
                "5. Execute the script and verify the Excel file was created successfully",
                "6. Verify the Excel file contains data and report file size",
                "Continue with ALL steps automatically without stopping after each tool execution",
            ],
            expected_output="A professionally formatted Excel file containing all extracted financial data, organized into multiple sheets with proper headers and formatting, saved at the specified output path, with confirmation that the file contains the expected data.",
            additional_context="The JSON contains financial data with nested structures. Each financial metric is an array of observations with fields like term_used, value, location, full_amount, etc. Company identification contains basic company info. IMPORTANT: The JSON data may be wrapped in markdown format like '```json\\n{...}\\n```' and needs to be cleaned before parsing. Handle both markdown-wrapped and pure JSON formats robustly.",
            stream=False,  # Don't stream for this focused task
            show_tool_calls=True,  # Show tool calls for debugging
            add_history_to_messages=True,  # Add chat history to messages
            num_history_responses=10,  # Keep last 10 responses in context
            exponential_backoff=True,  # Enable retry with exponential backoff
            retries=20,  # Allow up to 20 retries for better completion
            markdown=False,  # No need for markdown in this task
        )
