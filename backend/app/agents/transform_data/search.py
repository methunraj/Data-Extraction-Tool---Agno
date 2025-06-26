# app/agents/search_agent.py
from agno.models.google import Gemini
from ..base import BaseAgent


class SearchAgent(BaseAgent):
    """Search-only agent for currency conversion and fact-checking.
    
    This agent has native search and grounding enabled but no external tools.
    """
    
    def __init__(self, temp_dir: str = None, model_id=None):
        super().__init__("search", temp_dir, model_id=model_id)
    
    def get_instructions(self) -> list:
        """Get search agent specific instructions."""
        return [
            "You are a financial data assistant specializing in currency conversion.",
            "Your job is to find current exchange rates when asked.",
            "Provide the exchange rates in a clear, structured format.",
            "Always include the source and date of the rates.",
        ]
    
    def get_tools(self) -> list:
        """Search agent has no external tools, only built-in search."""
        return []
    
    def create_gemini_model(self, search: bool = True, grounding: bool = True) -> Gemini:
        """Create Gemini model with search and grounding enabled."""
        return super().create_gemini_model(search=search, grounding=grounding)