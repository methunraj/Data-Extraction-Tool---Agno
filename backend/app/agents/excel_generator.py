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
            instructions=load_prompt("agents/excel_generator_instructions.txt").split('\n'),
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
