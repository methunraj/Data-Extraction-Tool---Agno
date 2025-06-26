# app/agents/factory.py
import logging
from typing import Dict, Optional, Any

from agno.agent import Agent
from .transform_data.search import SearchAgent
from .transform_data.strategist import StrategistAgent
from .transform_data.codegen import CodeGenAgent
from .transform_data.qa import QualityAssuranceAgent
from .prompt_engineer.prompt_engineer import PromptEngineerAgent
from .json_corrector import JSONCorrectorAgent

logger = logging.getLogger(__name__)

def create_agent(agent_type: str, **kwargs) -> Agent:
    """Factory function to create agents based on type.
    
    Args:
        agent_type: Type of agent ('search', 'strategist', 'qa', 'codegen', 'prompt_engineer')
        **kwargs: Additional arguments for agent creation
            - model_id: Model ID to use for the agent
            - temp_dir: Temporary directory (for codegen)
            - exchange_rates: Exchange rates (for codegen)
    
    Returns:
        Agent instance
    """
    model_id = kwargs.get("model_id")
    
    if agent_type == "search":
        agent_instance = SearchAgent(model_id=model_id)
        return agent_instance.agent
    elif agent_type == "strategist":
        agent_instance = StrategistAgent(model_id=model_id)
        return agent_instance.agent
    elif agent_type == "qa":
        agent_instance = QualityAssuranceAgent(model_id=model_id)
        return agent_instance.agent
    elif agent_type == "codegen":
        temp_dir = kwargs.get("temp_dir")
        if not temp_dir:
            raise ValueError("temp_dir is required for codegen agent")
        exchange_rates = kwargs.get("exchange_rates")
        agent_instance = CodeGenAgent(temp_dir, exchange_rates, model_id=model_id)
        return agent_instance.agent
    elif agent_type == "prompt_engineer":
        agent_instance = PromptEngineerAgent(model_id=model_id)
        return agent_instance.agent
    elif agent_type == "json_corrector":
        agent_instance = JSONCorrectorAgent(model_id=model_id)
        return agent_instance.agent
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")

def get_agent_info() -> Dict[str, Dict[str, Any]]:
    """Get information about available agent types."""
    return {
        "search": {
            "description": "Currency conversion and fact-checking agent with search capabilities",
            "tools": ["Search", "Grounding"],
            "required_args": []
        },
        "strategist": {
            "description": "Task planning and breakdown agent",
            "tools": [],
            "required_args": []
        },
        "qa": {
            "description": "Quality assurance agent for code and output verification",
            "tools": ["PythonTools"],
            "required_args": []
        },
        "codegen": {
            "description": "Python code generation and execution agent for Excel creation",
            "tools": ["PythonTools"],
            "required_args": ["temp_dir"],
            "optional_args": ["exchange_rates"]
        }
    }

def cleanup_agent_pool():
    """Cleanup function for agent pool resources.
    
    This function is called during application shutdown to clean up
    any resources used by the agent pool. Currently a no-op as agents
    are created on-demand and don't maintain persistent connections.
    """
    logger.info("Agent pool cleanup completed")
    pass