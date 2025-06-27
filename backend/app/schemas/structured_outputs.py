# backend/app/schemas/structured_outputs.py
from typing import List, Dict, Any
from pydantic import BaseModel, Field

class ExamplePair(BaseModel):
    """A single input-output example pair for data extraction."""
    input: str = Field(..., description="Realistic document text sample", min_length=10)
    output: str = Field(..., description="Valid JSON output matching the schema", min_length=5)

class ExtractionConfiguration(BaseModel):
    """Complete data extraction configuration with all required components."""
    schema: str = Field(
        ..., 
        description="Valid JSON schema as an escaped string for data extraction",
        min_length=20
    )
    system_prompt: str = Field(
        ..., 
        description="Comprehensive system prompt for the AI extraction specialist",
        min_length=100
    )
    user_prompt_template: str = Field(
        ..., 
        description="User prompt template with {{document_text}} and {{schema}} placeholders",
        min_length=50
    )
    examples: List[ExamplePair] = Field(
        ..., 
        description="Array of realistic input-output examples", 
        min_items=1,
        max_items=5
    )
    reasoning: str = Field(
        ..., 
        description="Detailed explanation of design choices and approach",
        min_length=100
    )