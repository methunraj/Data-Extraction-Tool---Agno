"""
Simplified Prompt Engineer Workflow using Agno's native structured outputs.
One agent, structured response_model, built-in reasoning - pure simplicity.
"""
from typing import Dict, List, Any
from pydantic import BaseModel, Field

from agno.agent import Agent

# Import our shared infrastructure
from ..agents.models import get_reasoning_model, get_structured_model
from ..agents.tools import get_reasoning_tools
from ..agents.memory import get_memory, get_storage


class Example(BaseModel):
    """Example input-output pair for few-shot learning."""
    input: str = Field(..., description="Example input document text")
    output: str = Field(..., description="Expected JSON output for this input")

class ExtractionSchema(BaseModel):
    """Structured extraction configuration - validated by Agno automatically."""
    
    json_schema: str = Field(
        ..., 
        description="Complete JSON schema as a string with all required fields, types, and descriptions"
    )
    system_prompt: str = Field(
        ..., 
        description="Optimized system prompt that guides the extraction process"
    )
    user_prompt_template: str = Field(
        ..., 
        description="User prompt template with clear placeholders like {document_text}"
    )
    examples: List[Example] = Field(
        default_factory=list, 
        description="2-3 high-quality few-shot examples showing input-output pairs"
    )
    extraction_instructions: List[str] = Field(
        default_factory=list,
        description="Step-by-step instructions for the extraction process"
    )
    validation_rules: List[str] = Field(
        default_factory=list,
        description="Rules to validate the extracted data quality"
    )


class PromptEngineerWorkflow:
    """
    Generate optimized extraction configurations using Agno's structured outputs.
    Simplicity: One agent instead of multiple, structured output via response_model.
    """
    
    def __init__(self):
        """Initialize with shared memory and storage."""
        
        # Shared infrastructure
        self.workflow_memory = get_memory()
        self.workflow_storage = get_storage()
        
        # Single powerful agent with reasoning and structured output
        # Note: Gemini doesn't support tools with structured outputs, so we remove them
        self.engineer = Agent(
            name="PromptEngineer",
            model=get_structured_model(),  # Optimized for structured outputs
            instructions=[
                "You are an expert prompt engineer specializing in data extraction configurations",
                "Generate complete, production-ready extraction configurations",
                "Create JSON schemas that capture all required fields with proper types",
                "Write clear, specific prompts that guide accurate data extraction",
                "Include relevant few-shot examples that demonstrate the desired output",
                "Focus on clarity, completeness, and extraction accuracy",
                "Consider edge cases and data validation requirements",
                "Think step-by-step through the requirements before generating the configuration"
            ],
            response_model=ExtractionSchema,  # Structured output - no parsing needed!
            use_json_mode=True,  # Use JSON mode for complex nested structures
            markdown=False,  # Disable markdown for cleaner JSON output
            memory=self.workflow_memory,
            storage=self.workflow_storage,
            show_tool_calls=False
        )
    
    def run(self, requirements: str) -> ExtractionSchema:
        """
        Generate extraction configuration from requirements.
        Direct agent call without workflow iteration.
        """
        
        # Comprehensive prompt for extraction configuration generation
        prompt = f"""
        Create a comprehensive data extraction configuration for the following requirements:
        
        {requirements}
        
        Generate a complete configuration that includes:
        
        1. **JSON Schema**: 
           - Define all required fields with appropriate data types
           - Include descriptions for each field
           - Specify validation constraints where applicable
           - Use nested objects for complex data structures
           - Consider optional vs required fields based on document variability
        
        2. **System Prompt**: 
           - Create a clear, authoritative system prompt
           - Define the extraction agent's role and expertise
           - Specify output format requirements
           - Include quality and accuracy guidelines
        
        3. **User Prompt Template**: 
           - Design a template with clear placeholders (e.g., {{document_text}})
           - Include specific extraction instructions
           - Guide the model to find and structure the required data
           - Handle cases where data might be missing or unclear
        
        4. **Few-Shot Examples**: 
           - Provide 2-3 realistic examples showing input documents and expected output
           - Cover different document formats or edge cases
           - Demonstrate proper handling of missing or partial data
           - Show the exact JSON structure expected
        
        5. **Extraction Instructions**:
           - Break down the extraction process into clear steps
           - Specify how to handle ambiguous or missing data
           - Define data cleaning and normalization rules
        
        6. **Validation Rules**:
           - Define quality checks for extracted data
           - Specify required field validation
           - Include data format validation rules
        
        Focus on creating a production-ready configuration that will reliably extract high-quality, structured data from the specified document types.
        """
        
        # Direct agent call returns RunResponse
        response = self.engineer.run(prompt)
        
        # Extract the structured content from RunResponse
        if hasattr(response, 'content') and isinstance(response.content, ExtractionSchema):
            return response.content
        else:
            raise ValueError("No valid structured response generated")
    
    def run_with_examples(self, requirements: str, sample_documents: List[str]) -> ExtractionSchema:
        """
        Generate extraction configuration with sample documents for better few-shot examples.
        """
        
        # Enhanced prompt with sample documents
        documents_section = "\n\n".join([
            f"**Sample Document {i+1}:**\n{doc}" 
            for i, doc in enumerate(sample_documents[:3])  # Limit to 3 samples
        ])
        
        enhanced_prompt = f"""
        Create a comprehensive data extraction configuration for:
        
        **Requirements:** {requirements}
        
        **Sample Documents to Analyze:**
        {documents_section}
        
        Use these sample documents to:
        1. Design a JSON schema that captures all relevant data present
        2. Create realistic few-shot examples based on actual document content
        3. Identify common patterns and edge cases in the documents
        4. Optimize prompts for the specific document format and content style
        
        Generate a complete extraction configuration optimized for these document types.
        """
        
        # Direct agent call returns RunResponse
        response = self.engineer.run(enhanced_prompt)
        
        # Extract the structured content from RunResponse
        if hasattr(response, 'content') and isinstance(response.content, ExtractionSchema):
            return response.content
        else:
            raise ValueError("No valid structured response generated")
    
    def refine_configuration(self, current_config: ExtractionSchema, feedback: str) -> ExtractionSchema:
        """
        Refine existing configuration based on feedback.
        Pure Python - simple method calls.
        """
        
        refinement_prompt = f"""
        Improve this existing extraction configuration based on the provided feedback:
        
        **Current Configuration:**
        - JSON Schema: {current_config.json_schema}
        - System Prompt: {current_config.system_prompt}
        - User Prompt Template: {current_config.user_prompt_template}
        - Examples: {len(current_config.examples)} examples provided
        
        **Feedback to Address:**
        {feedback}
        
        Generate an improved configuration that addresses all the feedback while maintaining the quality of the existing configuration.
        Focus on:
        1. Fixing any identified issues in the schema or prompts
        2. Adding missing fields or improving field definitions
        3. Enhancing the clarity and specificity of prompts
        4. Improving or adding better few-shot examples
        5. Strengthening validation rules
        
        Return the complete refined configuration.
        """
        
        # Direct agent call returns RunResponse
        response = self.engineer.run(refinement_prompt)
        
        # Extract the structured content from RunResponse
        if hasattr(response, 'content') and isinstance(response.content, ExtractionSchema):
            return response.content
        else:
            raise ValueError("No valid structured response generated")