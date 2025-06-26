# backend/app/agents/prompt_engineer/prompt_engineer.py
from typing import Dict, Any, List
import json
from ..base import BaseAgent
from agno.tools import tool

class PromptEngineerAgent(BaseAgent):
    """Agent for generating extraction configurations including schema, prompts, and examples."""
    
    def __init__(self, model_id=None):
        super().__init__("prompt_engineer", model_id=model_id)
        
    def get_instructions(self) -> list:
        return [
            "You are an expert prompt engineer specializing in data extraction configurations.",
            "You generate JSON schemas, system prompts, user templates, and examples.",
            "Always ensure schemas are valid JSON with proper types and constraints.",
            "Create prompts that are clear, specific, and optimized for extraction.",
            "Generate realistic examples that demonstrate the expected output.",
            "Explain your design choices when requested.",
            "Consider the document type and user intent in your designs."
        ]
    
    def get_tools(self) -> list:
        return [
            validate_json_schema,
            optimize_prompt,
            generate_examples,
            test_extraction_config
        ]

# Define tools as module-level functions
@tool
def validate_json_schema(schema: str) -> Dict[str, Any]:
    """Validate a JSON schema for correctness."""
    try:
        schema_obj = json.loads(schema)
        # Add validation logic
        return {"valid": True, "schema": schema_obj}
    except Exception as e:
        return {"valid": False, "error": str(e)}

@tool
def optimize_prompt(prompt: str, purpose: str) -> str:
    """Optimize a prompt for better extraction results."""
    # Implement prompt optimization logic
    return prompt

@tool
def generate_examples(schema: str, count: int = 2) -> List[Dict[str, Any]]:
    """Generate example inputs and outputs based on schema."""
    # Implement example generation
    return []

@tool
def test_extraction_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Test if an extraction configuration is complete and valid."""
    # Implement config testing
    return {"valid": True}
