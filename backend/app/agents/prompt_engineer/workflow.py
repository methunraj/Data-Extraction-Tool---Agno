# backend/app/agents/prompt_engineer/workflow.py
from agno.workflow import Workflow
from .prompt_engineer import PromptEngineerAgent

class PromptEngineerWorkflow(Workflow):
    """A workflow for generating extraction configurations."""

    def __init__(self):
        super().__init__()
        self.prompt_engineer = PromptEngineerAgent()

    def run(self, user_intent: str):
        # This is where the orchestration logic will go.
        # For now, it's a placeholder.
        pass
