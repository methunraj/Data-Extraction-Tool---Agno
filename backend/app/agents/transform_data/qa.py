# app/agents/qa_agent.py
from agno.tools.python import PythonTools
from ..base import BaseAgent


class QualityAssuranceAgent(BaseAgent):
    """Quality assurance agent to verify output and code quality."""
    
    def __init__(self, temp_dir: str = None, model_id=None):
        super().__init__("qa", temp_dir, model_id=model_id)
    
    def get_instructions(self) -> list:
        """Get QA agent specific instructions."""
        return [
            "You are a meticulous Quality Assurance analyst. Your job is to inspect the generated Excel file and the Python code that created it.",
            "Verify that all requirements from the initial plan have been met.",
            "Check for data accuracy, completeness, and proper formatting in the Excel report.",
            "Review the Python code for clarity, efficiency, and robustness.",
            "If you find any issues, provide specific, actionable feedback to the Code Generation Agent for revision.",
            "If the report is perfect, provide a confirmation of approval."
        ]
    
    def get_tools(self) -> list:
        """QA agent has Python tools to inspect code and data."""
        return [
            PythonTools(run_files=True)  # To inspect code and data
        ]