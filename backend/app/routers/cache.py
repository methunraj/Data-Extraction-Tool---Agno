# app/routers/cache.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

from ..core.dependencies import ModelServiceDep, APIKeyDep
from ..services.cache_service import get_cache_service, CacheEntry, CacheStats

router = APIRouter(prefix="/api/cache", tags=["cache"])

@router.get("/stats")
async def get_cache_stats(
    api_key: APIKeyDep,
    model_service: ModelServiceDep = ModelServiceDep
) -> CacheStats:
    """
    Get cache statistics including hits, misses, savings, and costs.
    
    Returns:
    - Total cache entries
    - Hit/miss counts
    - Tokens saved through caching
    - Cost savings vs storage costs
    - Net savings
    """
    try:
        cache_service = get_cache_service(model_service)
        stats = await cache_service.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def list_caches(
    api_key: APIKeyDep,
    model_id: Optional[str] = Query(None, description="Filter by model ID"),
    include_expired: bool = Query(False, description="Include expired entries"),
    model_service: ModelServiceDep = ModelServiceDep
) -> List[dict]:
    """
    List all cache entries with metadata.
    
    Each entry includes:
    - Cache ID
    - Model ID
    - Token count
    - Creation and expiration times
    - Hit count
    - Time to live remaining
    """
    try:
        cache_service = get_cache_service(model_service)
        entries = await cache_service.list_caches(
            model_id=model_id,
            include_expired=include_expired
        )
        
        # Convert to dict for response
        return [entry.to_dict() for entry in entries]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{cache_id}")
async def get_cache(
    cache_id: str,
    api_key: APIKeyDep,
    model_service: ModelServiceDep = ModelServiceDep
) -> dict:
    """
    Get a specific cache entry by ID.
    
    Returns cache metadata including:
    - All cache entry fields
    - Whether the cache is still valid
    - Google cache resource name (if available)
    """
    try:
        cache_service = get_cache_service(model_service)
        entry = await cache_service.get_cache(cache_id)
        
        if not entry:
            raise HTTPException(status_code=404, detail=f"Cache {cache_id} not found or expired")
        
        return entry.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{cache_id}")
async def delete_cache(
    cache_id: str,
    api_key: APIKeyDep,
    model_service: ModelServiceDep = ModelServiceDep
) -> dict:
    """
    Delete a specific cache entry.
    
    This will:
    - Remove the cache from memory
    - Delete the associated Google cache resource
    - Return success/failure status
    """
    try:
        cache_service = get_cache_service(model_service)
        success = await cache_service.delete_cache(cache_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Cache {cache_id} not found")
        
        return {"message": f"Cache {cache_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cleanup")
async def cleanup_expired(
    api_key: APIKeyDep,
    model_service: ModelServiceDep = ModelServiceDep
) -> dict:
    """
    Manually trigger cleanup of expired cache entries.
    
    This is normally done automatically, but can be triggered
    manually for maintenance purposes.
    """
    try:
        cache_service = get_cache_service(model_service)
        cleaned = await cache_service.cleanup_expired()
        
        return {
            "message": f"Cleaned up {cleaned} expired cache entries",
            "entries_removed": cleaned
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/stats")
async def export_cache_stats(
    api_key: APIKeyDep,
    model_service: ModelServiceDep = ModelServiceDep
) -> dict:
    """
    Export detailed cache statistics for monitoring.
    
    Returns comprehensive data including:
    - Overall statistics
    - Per-entry details
    - Timestamp for tracking
    
    Useful for monitoring dashboards and analytics.
    """
    try:
        cache_service = get_cache_service(model_service)
        return cache_service.export_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))