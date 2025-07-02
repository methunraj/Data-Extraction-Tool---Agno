"""
Simplified Prompt Engineer Workflow using Agno's native structured outputs.
One agent, structured response_model, built-in reasoning - pure simplicity.
"""
from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field, model_validator
import json

from agno.agent import Agent

# Import our shared infrastructure
from ..agents.models import get_reasoning_model, get_structured_model
from ..agents.tools import get_reasoning_tools
from ..agents.memory import get_memory, get_storage
from ..prompts import load_prompt


class Example(BaseModel):
    """Example input-output pair for few-shot learning."""
    input: str = Field(..., description="Example input document text")
    output: str = Field(..., description="Expected JSON output for this input")

class ExtractionSchema(BaseModel):
    """Structured extraction configuration - validated by Agno automatically."""
    
    # Support both field names for compatibility
    schema: Optional[str] = Field(
        None, 
        description="Complete JSON schema as a string with all required fields, types, and descriptions"
    )
    json_schema: Optional[str] = Field(
        None, 
        description="Complete JSON schema as a string (alternative field name)"
    )
    system_prompt: str = Field(
        ..., 
        description="Optimized system prompt that guides the extraction process"
    )
    user_prompt_template: str = Field(
        ..., 
        description="User prompt template with clear placeholders like {{document_text}}"
    )
    examples: List[Example] = Field(
        default_factory=list, 
        description="2-3 high-quality few-shot examples showing input-output pairs"
    )
    reasoning: Optional[str] = Field(
        None, 
        description="Detailed explanation of design choices and approach"
    )
    
    # Optional fields that may be returned by the model
    extraction_instructions: Optional[List[str]] = Field(
        None,
        description="Step-by-step instructions for the extraction process"
    )
    validation_rules: Optional[List[str]] = Field(
        None,
        description="Rules to validate the extracted data quality"
    )
    
    @model_validator(mode='before')
    def handle_schema_fields(cls, values):
        """Handle both schema and json_schema fields."""
        # If we have json_schema but not schema, copy it over
        if 'json_schema' in values and values.get('json_schema') and not values.get('schema'):
            values['schema'] = values['json_schema']
        # If neither is provided, we'll let Pydantic handle the error
        return values
    
    @model_validator(mode='after')
    def validate_schema_exists(self):
        """Ensure we have at least one schema field."""
        if not self.schema and not self.json_schema:
            raise ValueError("Either 'schema' or 'json_schema' must be provided")
        return self
    
    class Config:
        extra = 'allow'  # Allow extra fields from the model


class PromptEngineerWorkflow:
    """
    Generate optimized extraction configurations using Agno's structured outputs.
    Simplicity: One agent instead of multiple, structured output via response_model.
    """
    
    def __init__(self, model_id: Optional[str] = None):
        """Initialize with shared memory and storage."""
        
        # Shared infrastructure
        self.workflow_memory = get_memory()
        self.workflow_storage = get_storage()
        
        # Single powerful agent with reasoning and structured output
        # Note: Gemini doesn't support tools with structured outputs, so we remove them
        self.engineer = Agent(
            name="PromptEngineer",
            model=get_structured_model(model_id=model_id),  # Use provided model or default
            instructions=[
                "Generate comprehensive extraction configurations",
                "Create detailed JSON schemas for data extraction",
                "Write clear system and user prompts",
                "Provide realistic examples",
                "Include validation rules and instructions"
            ],
            response_model=ExtractionSchema,  # Structured output - no parsing needed!
            structured_outputs=True,
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
        prompt = load_prompt("workflows/prompt_engineer_base_prompt.txt", requirements=requirements)
        
        # Direct agent call returns RunResponse
        response = self.engineer.run(prompt)
        
        # Debug logging
        print(f"[PromptEngineer] Response type: {type(response)}")
        if hasattr(response, 'content'):
            print(f"[PromptEngineer] Content type: {type(response.content)}")
            if isinstance(response.content, str):
                print(f"[PromptEngineer] Content preview: {response.content[:200]}...")
            elif isinstance(response.content, dict):
                print(f"[PromptEngineer] Content keys: {list(response.content.keys())}")
        
        # Extract the structured content from RunResponse
        if hasattr(response, 'content'):
            # Case 1: Already an ExtractionSchema object
            if isinstance(response.content, ExtractionSchema):
                return response.content
            
            # Case 2: Dict that needs to be converted
            elif isinstance(response.content, dict):
                try:
                    return ExtractionSchema(**response.content)
                except Exception as e:
                    print(f"[PromptEngineer] Failed to create ExtractionSchema from dict: {e}")
                    print(f"[PromptEngineer] Dict keys: {list(response.content.keys())}")
                    raise ValueError(f"Failed to parse response as ExtractionSchema: {e}")
            
            # Case 3: JSON string that needs parsing
            elif isinstance(response.content, str):
                try:
                    # Try to parse as JSON
                    parsed = json.loads(response.content)
                    return ExtractionSchema(**parsed)
                except json.JSONDecodeError as e:
                    print(f"[PromptEngineer] Failed to parse as JSON: {e}")
                    # Maybe it's a plain text response, try to extract JSON from it
                    import re
                    json_match = re.search(r'\{[\s\S]*\}', response.content)
                    if json_match:
                        try:
                            parsed = json.loads(json_match.group())
                            return ExtractionSchema(**parsed)
                        except Exception as e:
                            print(f"[PromptEngineer] Failed to extract JSON from string: {e}")
                    raise ValueError("Response is not valid JSON")
                except Exception as e:
                    print(f"[PromptEngineer] Failed to parse string response: {e}")
                    raise ValueError(f"Failed to parse response as ExtractionSchema: {e}")
        
        print(f"[PromptEngineer] No valid content in response")
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
        
        enhanced_prompt = load_prompt(
            "workflows/prompt_engineer_with_examples_prompt.txt",
            requirements=requirements,
            documents_section=documents_section
        )
        
        # Direct agent call returns RunResponse
        response = self.engineer.run(enhanced_prompt)
        
        # Use the same parsing logic as run()
        return self._parse_response(response)
    
    def _parse_response(self, response) -> ExtractionSchema:
        """Helper method to parse response into ExtractionSchema."""
        if hasattr(response, 'content'):
            if isinstance(response.content, ExtractionSchema):
                return response.content
            elif isinstance(response.content, dict):
                return ExtractionSchema(**response.content)
            elif isinstance(response.content, str):
                try:
                    parsed = json.loads(response.content)
                    return ExtractionSchema(**parsed)
                except Exception as e:
                    # Try to extract JSON from text
                    import re
                    json_match = re.search(r'\{[\s\S]*\}', response.content)
                    if json_match:
                        parsed = json.loads(json_match.group())
                        return ExtractionSchema(**parsed)
                    raise ValueError(f"Failed to parse response: {e}")
        
        raise ValueError("No valid structured response generated")