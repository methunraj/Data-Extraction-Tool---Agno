# app/routers/agents.py
from fastapi import APIRouter, Depends
from typing import Dict, Any

from ..core.dependencies import APIKeyDep
from .. import services
from ..agents import get_agent_info

router = APIRouter(prefix="/api/agents", tags=["agents"])

@router.get("/pool/status")
async def get_pool_status(
    api_key: APIKeyDep
) -> Dict[str, Any]:
    """
    Get the current status of the Agno agent pool.
    
    Returns information about:
    - Number of agents in pool
    - Maximum pool size
    - List of cached agent types
    - Current model being used for Agno processing
    """
    return services.get_agent_pool_status()

@router.post("/pool/refresh")
async def refresh_pool(
    api_key: APIKeyDep
) -> Dict[str, str]:
    """
    Refresh the agent pool to use updated model configuration.
    
    This clears all cached agents and forces them to be recreated
    with the current model settings from models.json.
    
    Use this endpoint after updating model configuration to ensure
    agents use the new models without restarting the server.
    """
    services.refresh_agent_pool_for_model_change()
    return {"message": "Agent pool refreshed successfully"}

@router.delete("/pool")
async def clear_pool(
    api_key: APIKeyDep
) -> Dict[str, str]:
    """
    Clear the entire agent pool to free memory.
    
    This removes all cached agents. New agents will be created
    on the next request with current model configuration.
    """
    services.cleanup_agent_pool()
    return {"message": "Agent pool cleared successfully"}

@router.get("/info")
async def get_agents_info(
    api_key: APIKeyDep
) -> Dict[str, Any]:
    """
    Get information about available agent types and their capabilities.
    
    Returns details about each agent type including:
    - Description and purpose
    - Required tools and capabilities
    - Required and optional arguments
    """
    pool_status = services.get_agent_pool_status()
    return {
        "agent_types": get_agent_info(),
        "pool_info": pool_status
    }