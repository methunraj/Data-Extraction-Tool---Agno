# app/agents/strategist_agent.py
from .base import BaseAgent


class StrategistAgent(BaseAgent):
    """Strategist agent to break down tasks and create execution plans."""
    
    def __init__(self, temp_dir: str = None):
        super().__init__("strategist", temp_dir)
    
    def get_instructions(self) -> list:
        """Get strategist agent specific instructions."""
        return [
            "You are a master strategist. Your role is to analyze a complex data-to-Excel task and break it down into a series of smaller, sequential, and parallelizable steps.",
            "For each step, define the goal, the required inputs, the expected outputs, and the agent best suited for the job (e.g., Search Agent, Code Generation Agent).",
            "Output the plan in a structured format (e.g., JSON or YAML) that can be parsed by an orchestrator.",
            "Focus on creating a plan that is efficient, resilient to failures, and produces a high-quality final report."
        ]
    
    def get_tools(self) -> list:
        """Strategist agent has no external tools."""
        return []