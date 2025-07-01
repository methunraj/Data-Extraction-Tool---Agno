"""
Simplified Prompt Engineer Workflow using Agno's native structured outputs.
One agent, structured response_model, built-in reasoning - pure simplicity.
"""
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

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
            instructions=load_prompt("workflows/prompt_engineer_instructions.txt").split('\n'),
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
        prompt = load_prompt("workflows/prompt_engineer_base_prompt.txt", requirements=requirements)
        
        # Direct agent call returns RunResponse
        response = self.engineer.run(prompt)
        
        # Debug logging
        print(f"[PromptEngineer] Response type: {type(response)}")
        if hasattr(response, 'content'):
            print(f"[PromptEngineer] Content type: {type(response.content)}")
            print(f"[PromptEngineer] Content: {response.content}")
        
        # Extract the structured content from RunResponse
        if hasattr(response, 'content') and isinstance(response.content, ExtractionSchema):
            return response.content
        elif hasattr(response, 'content') and isinstance(response.content, dict):
            # Try to create ExtractionSchema from dict
            try:
                return ExtractionSchema(**response.content)
            except Exception as e:
                print(f"[PromptEngineer] Failed to create ExtractionSchema from dict: {e}")
                raise ValueError(f"Failed to parse response as ExtractionSchema: {e}")
        else:
            print(f"[PromptEngineer] Invalid response format")
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
        
        # Debug logging
        print(f"[PromptEngineer] Response type: {type(response)}")
        if hasattr(response, 'content'):
            print(f"[PromptEngineer] Content type: {type(response.content)}")
        
        # Extract the structured content from RunResponse
        if hasattr(response, 'content') and isinstance(response.content, ExtractionSchema):
            return response.content
        elif hasattr(response, 'content') and isinstance(response.content, dict):
            # Try to create ExtractionSchema from dict
            try:
                return ExtractionSchema(**response.content)
            except (TypeError, ValueError, KeyError) as e:
                print(f"[PromptEngineer] Failed to create ExtractionSchema from dict: {e}")
                import traceback
                print(f"[PromptEngineer] Full traceback: {traceback.format_exc()}")
                raise ValueError(f"Failed to parse response as ExtractionSchema: {e}") from e
            except Exception as e:
                print(f"[PromptEngineer] Unexpected error creating ExtractionSchema: {e}")
                import traceback
                print(f"[PromptEngineer] Full traceback: {traceback.format_exc()}")
                raise RuntimeError(f"Unexpected error during schema creation: {e}") from e
        else:
            print(f"[PromptEngineer] Invalid response format")
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
        elif hasattr(response, 'content') and isinstance(response.content, dict):
            # Try to create ExtractionSchema from dict
            try:
                return ExtractionSchema(**response.content)
            except (TypeError, ValueError, KeyError) as e:
                print(f"[PromptEngineer] Failed to create ExtractionSchema from dict: {e}")
                import traceback
                print(f"[PromptEngineer] Full traceback: {traceback.format_exc()}")
                raise ValueError(f"Failed to parse response as ExtractionSchema: {e}") from e
            except Exception as e:
                print(f"[PromptEngineer] Unexpected error creating ExtractionSchema: {e}")
                import traceback
                print(f"[PromptEngineer] Full traceback: {traceback.format_exc()}")
                raise RuntimeError(f"Unexpected error during schema creation: {e}") from e
        else:
            print(f"[PromptEngineer] Invalid response format")
            raise ValueError("No valid structured response generated")