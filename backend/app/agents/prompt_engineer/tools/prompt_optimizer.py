# backend/app/agents/prompt_engineer/tools/prompt_optimizer.py
from agno.tools import tool

class PromptOptimizerTool:
    """Specialized tool for prompt optimization tasks."""
    
    @staticmethod
    @tool
    def optimize_system_prompt(prompt: str) -> str:
        """Optimize a system prompt for clarity and effectiveness."""
        pass
    
    @staticmethod
    @tool
    def optimize_user_prompt(prompt: str) -> str:
        """Optimize a user prompt for better user experience."""
        pass
