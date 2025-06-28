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
            instructions=[
                "You are an expert at converting JSON data to professional Excel files",
                "IMPORTANT: First install required packages using pip_install_package function: pandas and openpyxl",
                "Read the JSON file to understand the data structure",
                "Write a Python script that:",
                "  1. Reads the JSON data from the input file",
                "  2. Converts it to a pandas DataFrame",
                "  3. Handles nested structures appropriately (flatten or create multiple sheets)",
                "  4. Creates an Excel file with proper formatting",
                "  5. Saves the Excel file to the specified output path",
                "Use save_to_file_and_run to save and execute your Python script",
                "Apply professional formatting: headers, column widths, number formats",
                "Ensure the Excel file is created successfully before finishing",
            ],
            stream=False,  # Don't stream for this focused task
            show_tool_calls=True,  # Show tool calls for debugging
        )
