# app/schemas/generation.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

class GenerationType(str, Enum):
    """Types of generation requests."""
    UNIFIED_CONFIG = "unified_config"
    SCHEMA_ONLY = "schema_only"
    PROMPT_ONLY = "prompt_only"

class GenerateConfigRequest(BaseModel):
    """Request model for generating extraction configuration."""
    user_intent: str = Field(description="User's description of what they want to extract")
    document_type: Optional[str] = Field(None, description="Type of document (invoice, contract, etc)")
    sample_data: Optional[str] = Field(None, description="Sample of the document content")
    
    # Model configuration
    model_name: str = Field(description="Model ID to use for generation")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperature for generation")
    
    # Generation options
    include_examples: bool = Field(default=True, description="Whether to generate few-shot examples")
    example_count: int = Field(default=2, ge=0, le=5, description="Number of examples to generate")
    include_reasoning: bool = Field(default=True, description="Whether to include reasoning explanation")

class GeneratedExample(BaseModel):
    """Generated example for few-shot learning."""
    input: str = Field(description="Example input")
    output: Dict[str, Any] = Field(description="Example output")

class GenerateConfigResponse(BaseModel):
    """Response model for extraction configuration generation."""
    schema: str = Field(description="Generated JSON schema")
    system_prompt: str = Field(description="Generated system prompt")
    user_prompt_template: str = Field(description="Template for user prompts")
    examples: List[GeneratedExample] = Field(default=[], description="Generated examples")
    reasoning: Optional[str] = Field(None, description="Explanation of the generation")
    cost: float = Field(description="Generation cost in USD")
    tokens_used: int = Field(description="Total tokens used")

class GenerateSchemaRequest(BaseModel):
    """Request model for schema-only generation."""
    user_intent: str = Field(description="Description of data to extract")
    field_descriptions: Optional[Dict[str, str]] = Field(None, description="Specific field requirements")
    constraints: Optional[List[str]] = Field(None, description="Additional constraints")
    
    # Model configuration
    model_name: str = Field(description="Model ID to use")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)

class GenerateSchemaResponse(BaseModel):
    """Response model for schema generation."""
    schema: str = Field(description="Generated JSON schema")
    field_explanations: Optional[Dict[str, str]] = Field(None, description="Explanations for each field")
    cost: float = Field(description="Generation cost in USD")
    tokens_used: int = Field(description="Total tokens used")

class GeneratePromptRequest(BaseModel):
    """Request model for prompt-only generation."""
    extraction_goal: str = Field(description="What the extraction should achieve")
    schema: str = Field(description="JSON schema for the extraction")
    document_context: Optional[str] = Field(None, description="Context about the documents")
    
    # Model configuration
    model_name: str = Field(description="Model ID to use")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    
    # Options
    generate_system_prompt: bool = Field(default=True, description="Generate system prompt")
    generate_user_template: bool = Field(default=True, description="Generate user prompt template")

class GeneratePromptResponse(BaseModel):
    """Response model for prompt generation."""
    system_prompt: Optional[str] = Field(None, description="Generated system prompt")
    user_prompt_template: Optional[str] = Field(None, description="Generated user prompt template")
    usage_tips: Optional[List[str]] = Field(None, description="Tips for using the prompts")
    cost: float = Field(description="Generation cost in USD")
    tokens_used: int = Field(description="Total tokens used")

class RefineConfigRequest(BaseModel):
    """Request model for refining existing configuration."""
    current_schema: str = Field(description="Current JSON schema")
    current_system_prompt: str = Field(description="Current system prompt")
    refinement_instructions: str = Field(description="How to refine the configuration")
    failed_examples: Optional[List[Dict[str, Any]]] = Field(None, description="Examples that failed")
    
    # Model configuration
    model_name: str = Field(description="Model ID to use")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)

class RefineConfigResponse(BaseModel):
    """Response model for configuration refinement."""
    refined_schema: str = Field(description="Refined JSON schema")
    refined_system_prompt: str = Field(description="Refined system prompt")
    changes_made: List[str] = Field(description="List of changes made")
    reasoning: str = Field(description="Explanation of refinements")
    cost: float = Field(description="Refinement cost in USD")
    tokens_used: int = Field(description="Total tokens used")