# app/routers/monitoring.py
from fastapi import APIRouter, Depends
from typing import Dict, Any, List
from ..agents.utils.execution_monitor import execution_monitor
from ..core.dependencies import APIKeyDep

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

@router.get("/metrics", response_model=Dict[str, Any])
async def get_execution_metrics(api_key: APIKeyDep) -> Dict[str, Any]:
    """Get execution metrics and success rates"""
    return execution_monitor.get_success_metrics()

@router.get("/failures", response_model=Dict[str, Any])
async def get_failure_patterns(api_key: APIKeyDep) -> Dict[str, Any]:
    """Get failure patterns and analysis"""
    return execution_monitor.get_failure_patterns()

@router.get("/executions", response_model=List[Dict[str, Any]])
async def get_execution_history(api_key: APIKeyDep, limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent execution history"""
    data = execution_monitor.export_data()
    return data[-limit:] if len(data) > limit else data

@router.post("/cleanup")
async def cleanup_old_records(api_key: APIKeyDep, max_age_hours: int = 24) -> Dict[str, str]:
    """Clean up old execution records"""
    execution_monitor.clear_old_records(max_age_hours)
    return {"status": "success", "message": f"Cleaned records older than {max_age_hours} hours"}

@router.get("/health")
async def monitoring_health() -> Dict[str, Any]:
    """Get monitoring system health status"""
    metrics = execution_monitor.get_success_metrics()
    
    if metrics.get('no_data'):
        return {
            "status": "healthy",
            "message": "Monitoring system active, no executions yet",
            "executions": 0
        }
    
    recent_success_rate = metrics.get('recent_success_rate', 0.0)
    total_executions = metrics.get('total_executions', 0)
    
    if recent_success_rate >= 0.8:
        status = "healthy"
    elif recent_success_rate >= 0.5:
        status = "warning"
    else:
        status = "critical"
    
    return {
        "status": status,
        "recent_success_rate": recent_success_rate,
        "total_executions": total_executions,
        "message": f"Recent success rate: {recent_success_rate:.1%}"
    }