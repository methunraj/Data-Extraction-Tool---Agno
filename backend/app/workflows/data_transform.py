"""
Pure Python Data Transform Workflow using Agno patterns.
No framework or step-based approach - just pure Python control flow.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from agno.agent import Agent, RunResponse
from agno.tools.file import FileTools
from agno.tools.python import PythonTools
from agno.tools.reasoning import ReasoningTools
from agno.workflow import Workflow

from ..agents.memory import get_memory, get_session_memory, get_storage

# Import our shared infrastructure
from ..agents.models import get_extraction_model, get_reasoning_model, get_search_model
from ..agents.tools import get_python_tools, get_reasoning_tools
from ..prompts import load_prompt


class DataTransformWorkflow(Workflow):
    """
    Extract data from documents and generate Excel reports.
    Pure Python workflow logic with Agno's native capabilities.
    """

    name: str = "DataTransform"

    def __init__(
        self, working_dir: Optional[str] = None, model_id: Optional[str] = None
    ):
        """Initialize workflow with working directory for file operations."""
        super().__init__()

        # Set up working directory
        self.working_dir = working_dir or os.environ.get(
            "AGENT_TEMP_DIR", "/tmp/agno_work"
        )
        Path(self.working_dir).mkdir(parents=True, exist_ok=True)

        # Initialize shared memory and storage
        self.workflow_memory = get_memory()
        self.workflow_storage = get_storage()

        # Agent 1: Strategic Planning with Reasoning
        self.strategist = Agent(
            name="Strategist",
            model=get_reasoning_model(model_id=model_id),
            tools=[get_reasoning_tools(add_instructions=True)],
            instructions=load_prompt("workflows/data_transform_strategist_instructions.txt").split('\n'),
            reasoning=True,  # Enable step-by-step reasoning
            show_tool_calls=True,
            stream=True,
            memory=self.workflow_memory,
            storage=self.workflow_storage,
        )

        # Agent 2: Document Analysis and Data Extraction
        self.extractor = Agent(
            name="DataExtractor",
            model=get_extraction_model(model_id=model_id),
            tools=[
                get_python_tools(self.working_dir),  # For file reading and processing
                FileTools(base_dir=Path(self.working_dir)),  # For file operations
            ],
            instructions=load_prompt("workflows/data_transform_extractor_instructions.txt").split('\n'),
            stream=True,
            memory=self.workflow_memory,
            storage=self.workflow_storage,
            add_history_to_messages=True,
        )

        # Agent 3: Excel Generation and Formatting
        self.generator = Agent(
            name="ExcelGenerator",
            model=get_extraction_model(model_id=model_id),
            tools=[get_python_tools(self.working_dir)],
            instructions=load_prompt("workflows/data_transform_generator_instructions.txt").split('\n'),
            memory=self.workflow_memory,
            storage=self.workflow_storage,
            stream=True,
            add_history_to_messages=True,
        )

        # Agent 4: Quality Validation and Verification
        self.validator = Agent(
            name="QualityValidator",
            model=get_extraction_model(),
            tools=[
                get_python_tools(self.working_dir),
                FileTools(base_dir=Path(self.working_dir)),
            ],
            instructions=load_prompt("workflows/data_transform_validator_instructions.txt").split('\n'),
            stream=True,
            memory=self.workflow_memory,
            storage=self.workflow_storage,
        )

    def run(
        self, request: str, files: Optional[List[Dict[str, Any]]] = None
    ) -> Iterator[RunResponse]:
        """
        Pure Python workflow logic - full control over execution flow.
        Uses standard Python: loops, conditionals, exception handling.
        """

        # Initialize session-specific memory for this workflow run
        session_id = f"workflow_{self.run_id}"
        session_memory = get_session_memory(session_id)

        try:
            # Use session_state to cache intermediate results
            cache_key = f"extraction_{hash(request + str(files))}"
            if cache_key in self.session_state:
                yield RunResponse(
                    run_id=self.run_id,
                    content=f"Using cached results for: {request[:100]}...",
                )
                cached_result = self.session_state[cache_key]
                yield RunResponse(run_id=self.run_id, content=cached_result)
                return

            # Step 1: Strategic Planning Phase
            yield RunResponse(
                run_id=self.run_id,
                content="🎯 Phase 1: Strategic Planning - Analyzing request and documents...",
            )

            file_info = []
            if files:
                for file_data in files:
                    file_info.append(
                        {
                            "name": file_data.get("name", "unknown"),
                            "type": file_data.get("type", "unknown"),
                            "size": file_data.get("size", 0),
                        }
                    )

            planning_prompt = load_prompt(
                "workflows/data_transform_planning_prompt.txt",
                request=request,
                file_info=json.dumps(file_info, indent=2)
            )

            # Stream planning results
            for response in self.strategist.run(planning_prompt, stream=True):
                yield response

            plan = (
                self.strategist.run_response.content
                if self.strategist.run_response
                else "Plan generation failed"
            )

            # Step 2: Data Extraction Phase
            yield RunResponse(
                run_id=self.run_id,
                content="📊 Phase 2: Data Extraction - Processing documents...",
            )

            extraction_prompt = load_prompt(
                "workflows/data_transform_extraction_prompt.txt",
                plan=plan,
                request=request,
                file_info=json.dumps(file_info, indent=2),
                working_dir=self.working_dir
            )

            # Stream extraction results
            extracted_data = None
            for response in self.extractor.run(extraction_prompt, stream=True):
                yield response

            if self.extractor.run_response:
                extracted_data = self.extractor.run_response.content
                # Cache extraction results in session_state
                self.session_state[f"extracted_{cache_key}"] = extracted_data

            # Step 3: Excel Generation Phase
            yield RunResponse(
                run_id=self.run_id,
                content="📋 Phase 3: Excel Generation - Creating professional report...",
            )

            generation_prompt = load_prompt(
                "workflows/data_transform_generation_prompt.txt",
                request=request,
                extracted_data=extracted_data if extracted_data else "No data extracted",
                working_dir=self.working_dir
            )

            # Stream generation results
            for response in self.generator.run(generation_prompt, stream=True):
                yield response

            # Step 4: Quality Validation Phase
            yield RunResponse(
                run_id=self.run_id,
                content="✅ Phase 4: Quality Validation - Verifying report quality...",
            )

            validation_prompt = load_prompt(
                "workflows/data_transform_validation_prompt.txt",
                request=request,
                working_dir=self.working_dir
            )

            # Stream validation results
            for response in self.validator.run(validation_prompt, stream=True):
                yield response

            # Cache final result
            final_result = (
                self.validator.run_response.content
                if self.validator.run_response
                else "Validation completed"
            )
            self.session_state[cache_key] = final_result

            # Find and return the generated file path
            excel_files = list(Path(self.working_dir).glob("*.xlsx"))
            if excel_files:
                final_file = str(excel_files[0])  # Get the first Excel file found
                yield RunResponse(
                    run_id=self.run_id,
                    content=f"🎉 Workflow Complete! Generated file: {final_file}",
                )
            else:
                yield RunResponse(
                    run_id=self.run_id,
                    content="⚠️ Workflow completed but no Excel file was found. Check logs for issues.",
                )

        except Exception as e:
            # Pure Python exception handling
            error_msg = f"Workflow failed with error: {str(e)}"
            yield RunResponse(run_id=self.run_id, content=f"❌ {error_msg}")

            # Log error for debugging
            if hasattr(self, "workflow_storage"):
                # Could log to storage if needed
                pass
