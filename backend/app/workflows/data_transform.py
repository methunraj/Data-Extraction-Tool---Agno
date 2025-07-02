"""
Pure Python Data Transform Workflow using Agno patterns.
Follows best practices from Agno documentation.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional
from textwrap import dedent

from agno.agent import Agent, RunResponse
from agno.tools.file import FileTools
from agno.tools.python import PythonTools
from agno.workflow import Workflow, RunEvent
from agno.utils.log import logger
from pydantic import BaseModel, Field

# Import our shared infrastructure
from ..agents.models import get_extraction_model, get_reasoning_model
from ..agents.tools import get_python_tools, get_reasoning_tools
from ..prompts import load_prompt

# Import specialized agents
from ..agents.data_analyst import DataAnalystAgent, ExcelSpecification
from ..agents.excel_generator import ExcelGeneratorAgent


# Response Models for Structured Outputs
class ExtractionPlan(BaseModel):
    """Strategic plan for data extraction"""
    approach: str = Field(..., description="Overall extraction approach")
    steps: List[str] = Field(..., description="Step-by-step extraction plan")
    expected_output: str = Field(..., description="Expected output structure")
    challenges: List[str] = Field(default_factory=list, description="Potential challenges")


class ExtractedData(BaseModel):
    """Structured extracted data"""
    data: Dict[str, Any] = Field(..., description="Extracted data in structured format")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extraction metadata")
    quality_score: float = Field(..., description="Data quality score (0-1)")
    issues: List[str] = Field(default_factory=list, description="Any issues found")


class ValidationResult(BaseModel):
    """Excel validation results"""
    file_path: str = Field(..., description="Path to generated Excel file")
    validation_passed: bool = Field(..., description="Whether validation passed")
    sheets_created: List[str] = Field(..., description="List of sheets created")
    formatting_applied: bool = Field(..., description="Whether formatting was applied")
    issues: List[str] = Field(default_factory=list, description="Any issues found")


class DataTransformWorkflow(Workflow):
    """
    Extract data from documents and generate professional Excel reports.
    Uses Agno best practices with proper agent initialization and caching.
    """

    name: str = "DataTransform"
    description: str = dedent("""
    An intelligent data transformation workflow that:
    1. Analyzes extraction requirements
    2. Extracts data from various document formats
    3. Plans optimal Excel structure using AI
    4. Generates professional Excel reports with formatting
    5. Validates output quality
    """)

    def __init__(
        self, working_dir: Optional[str] = None, model_id: Optional[str] = None, **kwargs
    ):
        """Initialize workflow with working directory for file operations."""
        super().__init__(**kwargs)

        # Set up working directory
        self.working_dir = working_dir or os.environ.get(
            "AGENT_TEMP_DIR", "/tmp/agno_work"
        )
        Path(self.working_dir).mkdir(parents=True, exist_ok=True)
        
        # Store model_id for agent initialization
        self.model_id = model_id

        # Initialize agents with proper configuration
        self._initialize_agents()

    def _initialize_agents(self):
        """Initialize all agents with proper configuration"""
        
        # Load instructions properly (not split by lines)
        strategist_instructions = [
            "# Strategic Analysis Phase",
            "1. Analyze the extraction request comprehensively",
            "2. Evaluate extraction challenges and complexity",
            "# Execution Planning Phase", 
            "3. Design optimal extraction strategy",
            "4. Create detailed execution roadmap",
            "# Excel Structure Planning Phase",
            "5. Design target Excel architecture",
            "6. Define data transformation rules",
            "# Quality Assurance Planning",
            "7. Establish quality benchmarks",
            "8. Plan verification procedures"
        ]
        
        extractor_instructions = [
            "# Document Analysis Phase",
            "1. Identify and analyze document format",
            "2. Select optimal extraction tools",
            "# Data Extraction Phase",
            "3. Execute format-specific extraction",
            "4. Handle extraction complexities",
            "# Data Processing Phase",
            "5. Clean and normalize extracted data",
            "6. Structure data for Excel output",
            "# Quality Control Phase",
            "7. Validate extracted data",
            "8. Handle missing or problematic data",
            "# Output Preparation Phase",
            "9. Format final JSON output",
            "10. Generate extraction report"
        ]
        
        validator_instructions = [
            "Validate the generated Excel file meets all requirements",
            "Check data completeness and accuracy against source",
            "Verify file formatting and professional appearance",
            "Test file opens correctly and data is accessible",
            "Provide constructive feedback and quality assessment",
            "Identify any issues that need correction"
        ]

        # Agent 1: Strategic Planning with structured output
        self.strategist = Agent(
            name="StrategicPlanner",
            model=get_reasoning_model(model_id=self.model_id),
            description=dedent("""
            You are a strategic planning expert who analyzes data extraction requests
            and creates detailed execution plans. You excel at understanding requirements
            and designing optimal approaches for data transformation.
            """),
            instructions=strategist_instructions,
            response_model=ExtractionPlan,
            structured_outputs=True,
            reasoning=True,
            show_tool_calls=True,
        )

        # Agent 2: Data Extraction with structured output
        self.extractor = Agent(
            name="DataExtractor",
            model=get_extraction_model(model_id=self.model_id),
            tools=[
                get_python_tools(self.working_dir),
                FileTools(base_dir=Path(self.working_dir))
            ],
            description=dedent("""
            You are a data extraction specialist who can process various document formats
            and extract structured data. You ensure complete and accurate data extraction
            while maintaining data quality.
            """),
            instructions=extractor_instructions,
            response_model=ExtractedData,
            structured_outputs=True,
            add_history_to_messages=True,
        )

        # Agent 3: Data Analyst for Excel Structure Planning
        self.data_analyst = DataAnalystAgent(
            model=get_extraction_model(model_id=self.model_id),
            working_dir=self.working_dir
        )

        # Agent 4: Excel Generation with Professional Formatting
        self.excel_generator = ExcelGeneratorAgent(
            model=get_extraction_model(model_id=self.model_id),
            working_dir=self.working_dir
        )

        # Agent 5: Quality Validation with structured output
        self.validator = Agent(
            name="QualityValidator",
            model=get_extraction_model(model_id=self.model_id),
            tools=[
                get_python_tools(self.working_dir),
                FileTools(base_dir=Path(self.working_dir))
            ],
            description=dedent("""
            You are a quality assurance specialist who validates Excel reports
            for completeness, accuracy, and professional presentation.
            """),
            instructions=validator_instructions,
            response_model=ValidationResult,
            structured_outputs=True,
        )

    def run(
        self, request: str, files: Optional[List[Dict[str, Any]]] = None
    ) -> Iterator[RunResponse]:
        """
        Main workflow execution using pure Python control flow.
        Implements proper caching, error handling, and structured outputs.
        """
        
        # Check cache first using proper session_state
        cached_result = self.get_cached_excel(request, files)
        if cached_result:
            yield RunResponse(
                run_id=self.run_id,
                content=f"Using cached Excel report: {cached_result}",
                event=RunEvent.workflow_completed
            )
            return
        
        try:
            # Step 1: Strategic Planning
            yield RunResponse(
                run_id=self.run_id,
                content="🎯 Phase 1: Strategic Planning - Analyzing requirements...",
            )
            
            extraction_plan = self.create_extraction_plan(request, files)
            if not extraction_plan:
                yield RunResponse(
                    run_id=self.run_id,
                    content="❌ Failed to create extraction plan",
                    event=RunEvent.workflow_completed
                )
                return
            
            yield RunResponse(
                run_id=self.run_id,
                content=f"✅ Plan created: {extraction_plan.approach}",
            )
            
            # Step 2: Data Extraction
            yield RunResponse(
                run_id=self.run_id,
                content="📊 Phase 2: Data Extraction - Processing documents...",
            )
            
            extracted_data = self.extract_data(extraction_plan, request, files)
            if not extracted_data:
                yield RunResponse(
                    run_id=self.run_id,
                    content="❌ Failed to extract data",
                    event=RunEvent.workflow_completed
                )
                return
            
            yield RunResponse(
                run_id=self.run_id,
                content=f"✅ Data extracted with quality score: {extracted_data.quality_score}",
            )
            
            # Save extracted data for next steps
            json_file_path = self.save_extracted_data(extracted_data)
            
            # Step 3: Excel Structure Planning
            yield RunResponse(
                run_id=self.run_id,
                content="📋 Phase 3: Excel Planning - Designing structure...",
            )
            
            excel_spec = self.plan_excel_structure(json_file_path)
            if excel_spec:
                yield RunResponse(
                    run_id=self.run_id,
                    content=f"✅ Excel structure planned: {excel_spec.summary}",
                )
            
            # Step 4: Excel Generation
            yield RunResponse(
                run_id=self.run_id,
                content="🎨 Phase 4: Excel Generation - Creating formatted report...",
            )
            
            # Generate Excel and stream responses
            excel_path = None
            if excel_spec:
                generation_prompt = f"""
                Generate Excel file from the JSON data at: {json_file_path}
                
                Use this Excel specification for structure and formatting:
                {excel_spec.model_dump_json(indent=2)}
                
                IMPORTANT: Apply ALL formatting as specified in your instructions.
                """
            else:
                generation_prompt = f"""
                Generate Excel file from the JSON data at: {json_file_path}
                
                Original request: {request}
                
                IMPORTANT: Apply professional formatting with colors, borders, and proper column widths.
                """
            
            # Stream generation results
            for response in self.excel_generator.run(generation_prompt, stream=True):
                yield response
            
            # Find the generated file
            excel_files = list(Path(self.working_dir).glob("*.xlsx"))
            if excel_files:
                excel_path = str(excel_files[0])
            
            # Step 5: Quality Validation
            yield RunResponse(
                run_id=self.run_id,
                content="✅ Phase 5: Quality Validation - Verifying report...",
            )
            
            validation = self.validate_excel(excel_path, request)
            
            if validation and validation.validation_passed:
                # Cache successful result
                self.cache_excel_result(request, files, validation.file_path)
                
                yield RunResponse(
                    run_id=self.run_id,
                    content=f"🎉 Success! Excel report generated: {validation.file_path}",
                    event=RunEvent.workflow_completed
                )
            else:
                issues = validation.issues if validation else ["Unknown validation error"]
                yield RunResponse(
                    run_id=self.run_id,
                    content=f"⚠️ Report generated with issues: {', '.join(issues)}",
                    event=RunEvent.workflow_completed
                )
                
        except Exception as e:
            logger.error(f"Workflow failed: {str(e)}")
            yield RunResponse(
                run_id=self.run_id,
                content=f"❌ Workflow failed: {str(e)}",
                event=RunEvent.workflow_completed
            )

    # Helper methods for better organization (Agno best practice)
    def get_cached_excel(self, request: str, files: Optional[List[Dict[str, Any]]]) -> Optional[str]:
        """Check if we have a cached Excel report"""
        cache_key = self._generate_cache_key(request, files)
        return self.session_state.get("excel_reports", {}).get(cache_key)
    
    def cache_excel_result(self, request: str, files: Optional[List[Dict[str, Any]]], file_path: str):
        """Cache the Excel report for future use"""
        cache_key = self._generate_cache_key(request, files)
        if "excel_reports" not in self.session_state:
            self.session_state["excel_reports"] = {}
        self.session_state["excel_reports"][cache_key] = file_path
        logger.info(f"Cached Excel report: {file_path}")
    
    def _generate_cache_key(self, request: str, files: Optional[List[Dict[str, Any]]]) -> str:
        """Generate a cache key from request and files"""
        files_str = json.dumps(files) if files else ""
        return f"{hash(request + files_str)}"
    
    def create_extraction_plan(self, request: str, files: Optional[List[Dict[str, Any]]]) -> Optional[ExtractionPlan]:
        """Create strategic extraction plan"""
        file_info = []
        if files:
            for file_data in files:
                file_info.append({
                    "name": file_data.get("name", "unknown"),
                    "type": file_data.get("type", "unknown"),
                    "size": file_data.get("size", 0),
                })
        
        prompt = f"""
        Create an extraction plan for this request:
        Request: {request}
        Files: {json.dumps(file_info, indent=2)}
        
        Analyze the requirements and create a comprehensive plan.
        """
        
        response = self.strategist.run(prompt)
        if response and isinstance(response.content, ExtractionPlan):
            return response.content
        else:
            logger.warning("Failed to get valid extraction plan")
            return None
    
    def extract_data(self, plan: ExtractionPlan, request: str, files: Optional[List[Dict[str, Any]]]) -> Optional[ExtractedData]:
        """Extract data based on the plan"""
        prompt = f"""
        Extract data based on this plan:
        Plan: {plan.model_dump_json(indent=2)}
        Request: {request}
        Working Directory: {self.working_dir}
        
        Read and process all files, then return structured data.
        """
        
        response = self.extractor.run(prompt)
        if response and isinstance(response.content, ExtractedData):
            return response.content
        else:
            logger.warning("Failed to get valid extracted data")
            return None
    
    def save_extracted_data(self, extracted_data: ExtractedData) -> str:
        """Save extracted data to JSON file"""
        json_file_path = os.path.join(self.working_dir, "extracted_data.json")
        with open(json_file_path, 'w') as f:
            json.dump(extracted_data.data, f, indent=2)
        logger.info(f"Saved extracted data to: {json_file_path}")
        return json_file_path
    
    def plan_excel_structure(self, json_file_path: str) -> Optional[ExcelSpecification]:
        """Use DataAnalyst to plan Excel structure"""
        try:
            excel_spec = self.data_analyst.analyze_and_plan(json_file_path)
            return excel_spec
        except Exception as e:
            logger.warning(f"Excel planning failed: {e}")
            return None
    
    def validate_excel(self, excel_path: Optional[str], request: str) -> Optional[ValidationResult]:
        """Validate the generated Excel file"""
        if not excel_path:
            return None
        
        prompt = f"""
        Validate the Excel report at: {excel_path}
        Original request: {request}
        
        Check for completeness, formatting, and quality.
        """
        
        response = self.validator.run(prompt)
        if response and isinstance(response.content, ValidationResult):
            return response.content
        else:
            logger.warning("Failed to get valid validation result")
            return None