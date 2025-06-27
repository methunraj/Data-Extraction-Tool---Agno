"""
Pure Python Data Transform Workflow using Agno patterns.
No framework or step-based approach - just pure Python control flow.
"""
import os
import json
from typing import Iterator, List, Dict, Any, Optional
from pathlib import Path

from agno.workflow import Workflow
from agno.agent import Agent, RunResponse
from agno.tools.python import PythonTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.file import FileTools

# Import our shared infrastructure
from ..agents.models import get_extraction_model, get_reasoning_model, get_search_model
from ..agents.memory import get_memory, get_storage, get_session_memory
from ..agents.tools import get_python_tools, get_reasoning_tools


class DataTransformWorkflow(Workflow):
    """
    Extract data from documents and generate Excel reports.
    Pure Python workflow logic with Agno's native capabilities.
    """
    
    name: str = "DataTransform"
    
    def __init__(self, working_dir: Optional[str] = None):
        """Initialize workflow with working directory for file operations."""
        super().__init__()
        
        # Set up working directory
        self.working_dir = working_dir or os.environ.get("AGENT_TEMP_DIR", "/tmp/agno_work")
        Path(self.working_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize shared memory and storage
        self.workflow_memory = get_memory()
        self.workflow_storage = get_storage()
        
        # Agent 1: Strategic Planning with Reasoning
        self.strategist = Agent(
            name="Strategist",
            model=get_reasoning_model(),
            tools=[get_reasoning_tools(add_instructions=True)],
            instructions=[
                "Analyze the data extraction request step by step",
                "Create a clear, actionable execution plan",
                "Identify document types and optimal extraction approach",
                "Consider data quality and formatting requirements"
            ],
            reasoning=True,  # Enable step-by-step reasoning
            show_tool_calls=True,
            stream=True,
            memory=self.workflow_memory,
            storage=self.workflow_storage
        )
        
        # Agent 2: Document Analysis and Data Extraction  
        self.extractor = Agent(
            name="DataExtractor",
            model=get_extraction_model(),
            tools=[
                get_python_tools(self.working_dir),  # For file reading and processing
                FileTools(base_dir=self.working_dir)  # For file operations
            ],
            instructions=[
                "Extract structured data from uploaded documents",
                "Handle multiple file formats: PDF, CSV, Excel, JSON, text",
                "Use appropriate Python libraries (pandas, openpyxl, PyPDF2) for each format",
                "Return clean, structured data in JSON format",
                "Preserve data integrity and handle missing values properly"
            ],
            stream=True,
            memory=self.workflow_memory,
            storage=self.workflow_storage,
            add_history_to_messages=True
        )
        
        # Agent 3: Excel Generation and Formatting
        self.generator = Agent(
            name="ExcelGenerator", 
            model=get_extraction_model(),
            tools=[get_python_tools(self.working_dir)],
            instructions=[
                "Generate professional Excel reports using pandas and openpyxl",
                "Create multiple sheets with logical data organization",
                "Apply professional formatting: headers, colors, borders, fonts",
                "Include data validation and conditional formatting where appropriate",
                "Add summary statistics and charts if beneficial",
                "Save files with descriptive names in the working directory",
                "Ensure Excel files open correctly in standard applications"
            ],
            memory=self.workflow_memory,
            storage=self.workflow_storage,
            stream=True,
            add_history_to_messages=True
        )
        
        # Agent 4: Quality Validation and Verification
        self.validator = Agent(
            name="QualityValidator",
            model=get_extraction_model(),
            tools=[
                get_python_tools(self.working_dir),
                FileTools(base_dir=self.working_dir)
            ],
            instructions=[
                "Validate the generated Excel file meets all requirements",
                "Check data completeness and accuracy against source",
                "Verify file formatting and professional appearance", 
                "Test file opens correctly and data is accessible",
                "Provide constructive feedback and quality assessment",
                "Identify any issues that need correction"
            ],
            stream=True,
            memory=self.workflow_memory,
            storage=self.workflow_storage
        )
    
    def run(self, request: str, files: Optional[List[Dict[str, Any]]] = None) -> Iterator[RunResponse]:
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
                    content=f"Using cached results for: {request[:100]}..."
                )
                cached_result = self.session_state[cache_key]
                yield RunResponse(run_id=self.run_id, content=cached_result)
                return
            
            # Step 1: Strategic Planning Phase
            yield RunResponse(
                run_id=self.run_id, 
                content="🎯 Phase 1: Strategic Planning - Analyzing request and documents..."
            )
            
            file_info = []
            if files:
                for file_data in files:
                    file_info.append({
                        "name": file_data.get("name", "unknown"),
                        "type": file_data.get("type", "unknown"),
                        "size": file_data.get("size", 0)
                    })
            
            planning_prompt = f"""
            Analyze this data extraction request and create an execution plan:
            
            Request: {request}
            Files to process: {json.dumps(file_info, indent=2)}
            
            Consider:
            1. Document types and complexity
            2. Expected data structure and format
            3. Quality requirements and validation needs
            4. Optimal extraction approach for each file type
            """
            
            # Stream planning results
            for response in self.strategist.run(planning_prompt, stream=True):
                yield response
            
            plan = self.strategist.run_response.content if self.strategist.run_response else "Plan generation failed"
            
            # Step 2: Data Extraction Phase
            yield RunResponse(
                run_id=self.run_id,
                content="📊 Phase 2: Data Extraction - Processing documents..."
            )
            
            extraction_prompt = f"""
            Execute data extraction based on the strategic plan:
            
            Plan: {plan}
            Request: {request}
            Files: {json.dumps(file_info, indent=2)}
            
            IMPORTANT: Use Python code to:
            1. Read and process each file in the working directory: {self.working_dir}
            2. Extract data according to the requirements
            3. Structure the data cleanly for Excel generation
            4. Handle any data quality issues or missing values
            5. Return the processed data in a structured format
            
            Save intermediate results to verify extraction quality.
            """
            
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
                content="📋 Phase 3: Excel Generation - Creating professional report..."
            )
            
            generation_prompt = f"""
            Generate a professional Excel report from the extracted data:
            
            Original Request: {request}
            Extracted Data: {extracted_data if extracted_data else "No data extracted"}
            Working Directory: {self.working_dir}
            
            Create Excel file with:
            1. Professional formatting and styling
            2. Multiple sheets if data is complex
            3. Headers, proper column widths, and formatting
            4. Data validation where appropriate
            5. Summary sheet with key metrics if beneficial
            
            Save as: data_extraction_report.xlsx
            
            Use pandas and openpyxl for optimal results.
            """
            
            # Stream generation results
            for response in self.generator.run(generation_prompt, stream=True):
                yield response
            
            # Step 4: Quality Validation Phase
            yield RunResponse(
                run_id=self.run_id,
                content="✅ Phase 4: Quality Validation - Verifying report quality..."
            )
            
            validation_prompt = f"""
            Validate the generated Excel report meets all requirements:
            
            Original Request: {request}
            Expected Output: Professional Excel report with extracted data
            File Location: {self.working_dir}/data_extraction_report.xlsx
            
            Check:
            1. File exists and opens correctly
            2. Data completeness and accuracy
            3. Professional formatting and presentation
            4. Meets original request requirements
            5. No errors or corruption
            
            Provide detailed quality assessment and any recommendations.
            """
            
            # Stream validation results
            for response in self.validator.run(validation_prompt, stream=True):
                yield response
            
            # Cache final result
            final_result = self.validator.run_response.content if self.validator.run_response else "Validation completed"
            self.session_state[cache_key] = final_result
            
            # Find and return the generated file path
            excel_files = list(Path(self.working_dir).glob("*.xlsx"))
            if excel_files:
                final_file = str(excel_files[0])  # Get the first Excel file found
                yield RunResponse(
                    run_id=self.run_id,
                    content=f"🎉 Workflow Complete! Generated file: {final_file}"
                )
            else:
                yield RunResponse(
                    run_id=self.run_id,
                    content="⚠️ Workflow completed but no Excel file was found. Check logs for issues."
                )
                
        except Exception as e:
            # Pure Python exception handling
            error_msg = f"Workflow failed with error: {str(e)}"
            yield RunResponse(run_id=self.run_id, content=f"❌ {error_msg}")
            
            # Log error for debugging
            if hasattr(self, 'workflow_storage'):
                # Could log to storage if needed
                pass