# backend/app/agents/prompt_engineer/tools/example_creator.py
from typing import List, Dict, Any
from agno.tools import tool

class ExampleCreatorTool:
    """Specialized tool for generating few-shot examples."""
    
    @staticmethod
    @tool
    def generate_examples(schema: str, count: int = 2) -> List[Dict[str, Any]]:
        """Generate example inputs and outputs based on schema."""
        pass
