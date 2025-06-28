"""
Agno-native tools configuration for IntelliExtract.
Pure Agno tools - no custom wrappers or subprocess handling.
"""

import os
from pathlib import Path
from typing import List, Union

from agno.tools.file import FileTools
from agno.tools.python import PythonTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.thinking import ThinkingTools


def get_python_tools(working_dir: str) -> PythonTools:
    """
    Python execution tools with proper isolation via Agno's base_dir.
    Agno handles ALL path management, security, and execution!

    Args:
        working_dir: Directory for Python execution and file operations

    Returns:
        PythonTools configured for safe execution
    """
    # Ensure working directory exists
    Path(working_dir).mkdir(parents=True, exist_ok=True)

    return PythonTools(
        run_code=True,  # Enable code execution
        pip_install=True,  # Allow pip installs in sandbox
        save_and_run=True,  # Enable save_to_file_and_run functionality
        read_files=True,  # Allow reading files
        base_dir=Path(working_dir),  # Agno handles all path management!
    )


def get_file_tools(working_dir: str) -> FileTools:
    """
    File operation tools with Agno's built-in path validation.

    Args:
        working_dir: Directory for file operations

    Returns:
        FileTools configured for safe file operations
    """
    # Ensure working directory exists
    Path(working_dir).mkdir(parents=True, exist_ok=True)

    return FileTools(
        base_dir=Path(working_dir)  # Agno handles path validation automatically
    )


def get_reasoning_tools(add_instructions: bool = True) -> ReasoningTools:
    """
    Enable step-by-step reasoning capabilities.

    Args:
        add_instructions: Whether to add reasoning instructions automatically

    Returns:
        ReasoningTools for chain-of-thought reasoning
    """
    return ReasoningTools(add_instructions=add_instructions)


def get_thinking_tools(add_instructions: bool = True) -> ThinkingTools:
    """
    Enable structured thinking and reflection capabilities.
    Provides agents with a scratchpad for reasoning through problems.

    Args:
        add_instructions: Whether to add thinking instructions automatically

    Returns:
        ThinkingTools for structured reflection
    """
    return ThinkingTools(add_instructions=add_instructions)


def get_extraction_tools(working_dir: str) -> List[Union[PythonTools, FileTools]]:
    """
    Standard tool set for data extraction agents.

    Args:
        working_dir: Directory for tool operations

    Returns:
        List of tools for extraction workflows
    """
    return [get_python_tools(working_dir), get_file_tools(working_dir)]


def get_reasoning_extraction_tools(
    working_dir: str,
) -> List[Union[PythonTools, FileTools, ReasoningTools]]:
    """
    Enhanced tool set with reasoning for complex extraction tasks.

    Args:
        working_dir: Directory for tool operations

    Returns:
        List of tools including reasoning capabilities
    """
    return [
        get_python_tools(working_dir),
        get_file_tools(working_dir),
        get_reasoning_tools(add_instructions=True),
    ]


def get_thinking_extraction_tools(
    working_dir: str,
) -> List[Union[PythonTools, FileTools, ThinkingTools]]:
    """
    Enhanced tool set with thinking for reflective extraction tasks.

    Args:
        working_dir: Directory for tool operations

    Returns:
        List of tools including thinking capabilities
    """
    return [
        get_python_tools(working_dir),
        get_file_tools(working_dir),
        get_thinking_tools(add_instructions=True),
    ]
