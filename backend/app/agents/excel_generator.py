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
from app.prompts import load_prompt


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
            description=load_prompt("agents/excel_generator_description.txt"),
            goal=load_prompt("agents/excel_generator_goal.txt"),
            instructions=[
                "# Setup Phase",
                "1. Install required packages: pandas, openpyxl, json",
                "# Read and Process Data", 
                "2. Read the JSON file using read_file tool",
                "3. Parse the JSON data (handle markdown wrappers if present)",
                "4. If ExcelSpecification is provided, use it to guide the structure",
                "# Create Excel File with Professional Formatting",
                "5. Create a Python script using save_to_file_and_run with the EXACT formatting pattern from your instructions",
                "6. ALWAYS use the exact formatting code provided",
                "7. ALWAYS apply ALL formatting (headers, borders, colors, number formats)",
                "8. ALWAYS auto-adjust column widths",
                "9. ALWAYS freeze the header row",
                "10. ALWAYS add autofilters",
                "11. Handle errors gracefully but ensure formatting is applied"
            ],
            expected_output=load_prompt("agents/excel_generator_expected_output.txt"),
            additional_context=load_prompt("agents/excel_generator_additional_context.txt"),
            stream=False,  # Don't stream for this focused task
            show_tool_calls=True,  # Show tool calls for debugging
            add_history_to_messages=True,  # Add chat history to messages
            num_history_responses=10,  # Keep last 10 responses in context
            exponential_backoff=True,  # Enable retry with exponential backoff
            retries=20,  # Allow up to 20 retries for better completion
            markdown=False,  # No need for markdown in this task
        )
