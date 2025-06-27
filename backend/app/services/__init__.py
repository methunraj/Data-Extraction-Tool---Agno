# app/services/__init__.py
from .generation_service import GenerationService
from .model_service import ModelService
from .token_service import TokenService

# Import agent factory and pool cleanup
# from ..agents.factory import cleanup_agent_pool  # Legacy import - removed
cleanup_agent_pool = lambda: None  # Placeholder function

# Import legacy services from legacy_services.py for backward compatibility
from ..legacy_services import (
    FinancialReportWorkflow,
    direct_json_to_excel_async,
    direct_json_to_excel,
    get_agent_pool_status,
    AGENT_POOL
)

__all__ = [
    "GenerationService", "ModelService", "TokenService", "cleanup_agent_pool",
    "FinancialReportWorkflow", "direct_json_to_excel_async", "direct_json_to_excel",
    "get_agent_pool_status", "AGENT_POOL"
]