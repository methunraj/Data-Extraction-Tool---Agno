# app/agents/base.py
import os
import uuid
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any

from agno.agent import Agent
from agno.models.google import Gemini
from agno.storage.sqlite import SqliteStorage

from ..core.config import settings
from ..utils.model_utils import get_model_service

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base class for all Agno agents with common functionality."""
    
    def __init__(self, agent_type: str, temp_dir: Optional[str] = None, model_id: Optional[str] = None):
        self.agent_type = agent_type
        self.temp_dir = temp_dir
        self.model_id = model_id
        self.model_service = get_model_service()
        self._agent: Optional[Agent] = None
        
    def get_agno_model(self) -> str:
        """Get the configured model for Agno processing."""
        # Use specified model if provided
        if self.model_id:
            logger.info(f"Using specified model_id: {self.model_id}")
            return self.model_id
            
        # Try to get a model that supports 'agno' purpose
        agno_models = self.model_service.get_models_for_purpose("agno")
        if agno_models:
            # Prefer 2.0-flash models for speed, fall back to 2.5-flash for compatibility
            for model in agno_models:
                if "2.0-flash" in model["id"]:
                    logger.info(f"Using default 2.0-flash model: {model['id']}")
                    return model["id"]
            for model in agno_models:
                if "2.5-flash" in model["id"]:
                    logger.info(f"Using default 2.5-flash model: {model['id']}")
                    return model["id"]
            # Return first available agno model
            logger.info(f"Using first available agno model: {agno_models[0]['id']}")
            return agno_models[0]["id"]
        
        # Fallback to default if no agno models found
        logger.info(f"Using fallback default model: {settings.DEFAULT_AI_MODEL}")
        return settings.DEFAULT_AI_MODEL

    def create_storage(self, table_name: str) -> SqliteStorage:
        """Create unique storage for the agent."""
        storage_dir = Path("storage")
        storage_dir.mkdir(exist_ok=True)
        unique_db_id = uuid.uuid4().hex[:8]
        
        return SqliteStorage(
            table_name=table_name,
            db_file=str(storage_dir / f"{self.agent_type}_agents_{unique_db_id}.db"),
            auto_upgrade_schema=True
        )

    def create_gemini_model(self, search: bool = False, grounding: bool = False) -> Gemini:
        """Create Gemini model with specified capabilities."""
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not set in the environment.")
            
        return Gemini(
            id=self.get_agno_model(),
            api_key=settings.GOOGLE_API_KEY,
            search=search,
            grounding=grounding,
        )

    @abstractmethod
    def get_instructions(self) -> list:
        """Get instructions specific to this agent type."""
        pass

    @abstractmethod
    def get_tools(self) -> list:
        """Get tools specific to this agent type."""
        pass

    def create_agent(self) -> Agent:
        """Create the agent with directory enforcement"""
        if self._agent is not None:
            return self._agent
        
        # Ensure temp_dir is absolute and exists
        if self.temp_dir:
            self.temp_dir = os.path.abspath(self.temp_dir)
            os.makedirs(self.temp_dir, exist_ok=True)
        
        # Create unique storage for Python agent
        storage_dir = Path("storage")
        storage_dir.mkdir(exist_ok=True)
        unique_db_id = os.urandom(4).hex()
        db_path = storage_dir / f"python_agents_{unique_db_id}.db"
        
        # Ensure storage directory has write permissions
        storage_dir.chmod(0o755)
        
        agent_storage = SqliteStorage(
            table_name="python_agent_sessions",
            db_file=str(db_path),
            auto_upgrade_schema=True
        )
        
        # Ensure database file has write permissions
        if db_path.exists():
            db_path.chmod(0o644)
        
        # Create Python execution agent with enhanced configuration
        self._agent = Agent(
            model=self.create_gemini_model(),
            tools=self.get_tools(),
            storage=agent_storage,
            add_history_to_messages=True,
            num_history_runs=3,
            reasoning=False,
            show_tool_calls=True,
            markdown=True,
            add_datetime_to_instructions=True,
            tool_call_limit=20,
            instructions=self.get_instructions(),
            exponential_backoff=True,
            retries=5,
            debug_mode=settings.AGNO_DEBUG,
            monitoring=settings.AGNO_MONITOR,
        )
        
        return self._agent
            
        self._agent = Agent(
            model=self.create_gemini_model(),
            tools=self.get_tools(),
            storage=self.create_storage(f"{self.agent_type}_agent_sessions"),
            instructions=self.get_instructions(),
            markdown=True,
            show_tool_calls=True,
            debug_mode=settings.AGNO_DEBUG,
        )
        
        logger.info(f"Created {self.agent_type} agent with model: {self.get_agno_model()}")
        return self._agent

    @property
    def agent(self) -> Agent:
        """Get the agent instance, creating it if necessary."""
        if self._agent is None:
            self._agent = self.create_agent()
        return self._agent