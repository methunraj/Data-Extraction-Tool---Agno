# app/agents/factory.py
import logging
from typing import Dict, Optional, Any

from agno.agent import Agent
from .search_agent import SearchAgent
from .strategist_agent import StrategistAgent
from .codegen_agent import CodeGenAgent
from .qa_agent import QualityAssuranceAgent

logger = logging.getLogger(__name__)

def create_agent(agent_type: str, **kwargs) -> Agent:
    """Factory function to create agents based on type.
    
    Args:
        agent_type: Type of agent ('search', 'strategist', 'qa', 'codegen')
        **kwargs: Additional arguments for agent creation
    
    Returns:
        Agent instance
    """
    if agent_type == "search":
        agent_instance = SearchAgent()
        return agent_instance.agent
    elif agent_type == "strategist":
        agent_instance = StrategistAgent()
        return agent_instance.agent
    elif agent_type == "qa":
        agent_instance = QualityAssuranceAgent()
        return agent_instance.agent
    elif agent_type == "codegen":
        temp_dir = kwargs.get("temp_dir")
        if not temp_dir:
            raise ValueError("temp_dir is required for codegen agent")
        exchange_rates = kwargs.get("exchange_rates")
        agent_instance = CodeGenAgent(temp_dir, exchange_rates)
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