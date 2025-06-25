# app/services/cache_service.py
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
import asyncio
from collections import OrderedDict

from google import genai
from google.genai import types

from ..core.google_client import GoogleGenAIClient
from ..core.exceptions import CacheError
from .model_service import ModelService

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Represents a cache entry with metadata."""
    cache_id: str
    model_id: str
    content_hash: str
    token_count: int
    created_at: datetime
    expires_at: datetime
    hit_count: int = 0
    last_accessed: Optional[datetime] = None
    google_cache_name: Optional[str] = None  # Google's cache resource name
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['created_at'] = data['created_at'].isoformat()
        data['expires_at'] = data['expires_at'].isoformat()
        if data['last_accessed']:
            data['last_accessed'] = data['last_accessed'].isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CacheEntry':
        """Create from dictionary."""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        if data.get('last_accessed'):
            data['last_accessed'] = datetime.fromisoformat(data['last_accessed'])
        return cls(**data)

@dataclass
class CacheStats:
    """Cache statistics."""
    total_entries: int = 0
    total_hits: int = 0
    total_misses: int = 0
    tokens_saved: int = 0
    cost_saved: float = 0.0
    storage_cost: float = 0.0
    net_savings: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

class CacheService:
    """Service for managing content caching with Google GenAI."""
    
    # Minimum token thresholds for caching
    MIN_CACHE_TOKENS = {
        "flash": 1024,
        "pro": 2048,
        "default": 1024
    }
    
    def __init__(self, model_service: ModelService, max_memory_entries: int = 1000):
        self.model_service = model_service
        self.client = GoogleGenAIClient.get_client()
        
        # In-memory cache storage (LRU)
        self._cache_entries: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_entries = max_memory_entries
        
        # Statistics
        self._stats = CacheStats()
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        # Background cleanup task
        self._cleanup_task = None
    
    async def create_cache(
        self,
        content: List[Dict[str, Any]],
        model_id: str,
        ttl_hours: float = 1.0,
        cache_id: Optional[str] = None
    ) -> Tuple[str, CacheEntry]:
        """
        Create a cache entry for content.
        
        Args:
            content: Content to cache (system prompt, schema, etc.)
            model_id: Model ID for the cache
            ttl_hours: Time to live in hours
            cache_id: Optional custom cache ID
            
        Returns:
            Tuple of (cache_id, cache_entry)
        """
        # Ensure background cleanup is started
        await self.ensure_background_cleanup_started()
        
        async with self._lock:
            # Generate content hash
            content_hash = self._generate_content_hash(content)
            
            # Check if already cached
            existing = self._find_by_hash(content_hash, model_id)
            if existing:
                logger.info(f"Content already cached with ID: {existing.cache_id}")
                return existing.cache_id, existing
            
            # Estimate token count
            token_count = await self._estimate_content_tokens(content, model_id)
            
            # Check minimum token threshold
            if not self._meets_cache_threshold(model_id, token_count):
                raise CacheError(
                    f"Content has {token_count} tokens, below minimum for caching",
                    details={
                        "token_count": token_count,
                        "minimum_required": self._get_min_tokens(model_id)
                    }
                )
            
            # Generate cache ID if not provided
            if not cache_id:
                cache_id = f"cache_{content_hash[:12]}_{int(datetime.now().timestamp())}"
            
            # Create cache with Google GenAI
            try:
                # Convert content to proper format for caching
                cache_content = types.Content(
                    parts=[types.Part(text=json.dumps(c)) for c in content],
                    role="user"
                )
                
                google_cache = await self.client.caches.create_async(
                    model=model_id,
                    contents=[cache_content],
                    ttl=f"{int(ttl_hours * 3600)}s"
                )
                
                google_cache_name = google_cache.name
                logger.info(f"Created Google cache: {google_cache_name}")
                
            except Exception as e:
                logger.error(f"Failed to create Google cache: {e}")
                google_cache_name = None
            
            # Create cache entry
            now = datetime.now()
            cache_entry = CacheEntry(
                cache_id=cache_id,
                model_id=model_id,
                content_hash=content_hash,
                token_count=token_count,
                created_at=now,
                expires_at=now + timedelta(hours=ttl_hours),
                google_cache_name=google_cache_name
            )
            
            # Store in memory
            self._cache_entries[cache_id] = cache_entry
            self._enforce_memory_limit()
            
            return cache_id, cache_entry
    
    async def get_cache(self, cache_id: str) -> Optional[CacheEntry]:
        """Get a cache entry by ID."""
        async with self._lock:
            entry = self._cache_entries.get(cache_id)
            
            if entry:
                # Check if expired
                if datetime.now() > entry.expires_at:
                    logger.info(f"Cache {cache_id} has expired")
                    await self._remove_cache(cache_id)
                    return None
                
                # Update access info
                entry.hit_count += 1
                entry.last_accessed = datetime.now()
                self._stats.total_hits += 1
                
                # Move to end (LRU)
                self._cache_entries.move_to_end(cache_id)
                
                return entry
            
            self._stats.total_misses += 1
            return None
    
    async def list_caches(
        self,
        model_id: Optional[str] = None,
        include_expired: bool = False
    ) -> List[CacheEntry]:
        """List all cache entries."""
        async with self._lock:
            now = datetime.now()
            entries = []
            
            for entry in self._cache_entries.values():
                # Filter by model if specified
                if model_id and entry.model_id != model_id:
                    continue
                
                # Filter expired unless requested
                if not include_expired and now > entry.expires_at:
                    continue
                
                entries.append(entry)
            
            return entries
    
    async def delete_cache(self, cache_id: str) -> bool:
        """Delete a cache entry."""
        async with self._lock:
            return await self._remove_cache(cache_id)
    
    async def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        async with self._lock:
            # Calculate current stats
            self._stats.total_entries = len(self._cache_entries)
            
            # Calculate storage costs
            total_storage_hours = 0.0
            for entry in self._cache_entries.values():
                if entry.expires_at > datetime.now():
                    hours_stored = (datetime.now() - entry.created_at).total_seconds() / 3600
                    total_storage_hours += entry.token_count * hours_stored / 1_000_000
            
            # Get average pricing (simplified - would need model-specific in production)
            avg_cache_storage_cost = 1.0  # $1 per million tokens per hour
            self._stats.storage_cost = total_storage_hours * avg_cache_storage_cost
            
            # Calculate net savings
            self._stats.net_savings = self._stats.cost_saved - self._stats.storage_cost
            
            return self._stats
    
    async def record_cache_hit(
        self,
        cache_id: str,
        tokens_saved: int,
        cost_saved: float
    ):
        """Record a cache hit and update statistics."""
        async with self._lock:
            self._stats.tokens_saved += tokens_saved
            self._stats.cost_saved += cost_saved
    
    async def cleanup_expired(self) -> int:
        """Clean up expired cache entries."""
        async with self._lock:
            now = datetime.now()
            expired_ids = [
                cache_id for cache_id, entry in self._cache_entries.items()
                if now > entry.expires_at
            ]
            
            for cache_id in expired_ids:
                await self._remove_cache(cache_id)
            
            logger.info(f"Cleaned up {len(expired_ids)} expired cache entries")
            return len(expired_ids)
    
    def start_background_cleanup(self, interval_minutes: int = 15):
        """Start background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            return
        
        try:
            # Check if we're in an async context
            loop = asyncio.get_running_loop()
            
            async def cleanup_loop():
                while True:
                    try:
                        await asyncio.sleep(interval_minutes * 60)
                        await self.cleanup_expired()
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.error(f"Error in cleanup task: {e}")
            
            self._cleanup_task = asyncio.create_task(cleanup_loop())
            logger.info("Background cleanup task started")
        except RuntimeError:
            # No event loop running, skip background cleanup
            logger.info("No event loop running, skipping background cleanup initialization")
    
    def stop_background_cleanup(self):
        """Stop background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
    
    async def ensure_background_cleanup_started(self, interval_minutes: int = 15):
        """Ensure background cleanup task is started (async version)."""
        if self._cleanup_task and not self._cleanup_task.done():
            return
        
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(interval_minutes * 60)
                    await self.cleanup_expired()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in cleanup task: {e}")
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info("Background cleanup task started")
    
    def _generate_content_hash(self, content: List[Dict[str, Any]]) -> str:
        """Generate deterministic hash for content."""
        # Sort and serialize content for consistent hashing
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()
    
    def _find_by_hash(self, content_hash: str, model_id: str) -> Optional[CacheEntry]:
        """Find cache entry by content hash and model."""
        for entry in self._cache_entries.values():
            if (entry.content_hash == content_hash and 
                entry.model_id == model_id and
                datetime.now() < entry.expires_at):
                return entry
        return None
    
    async def _estimate_content_tokens(
        self, 
        content: List[Dict[str, Any]], 
        model_id: str
    ) -> int:
        """Estimate token count for content."""
        # Simple estimation - serialize and count
        content_str = json.dumps(content)
        # Rough estimate: 1 token ≈ 4 characters
        return len(content_str) // 4
    
    def _meets_cache_threshold(self, model_id: str, token_count: int) -> bool:
        """Check if content meets minimum token threshold for caching."""
        min_tokens = self._get_min_tokens(model_id)
        return token_count >= min_tokens
    
    def _get_min_tokens(self, model_id: str) -> int:
        """Get minimum token threshold for a model."""
        if "flash" in model_id.lower():
            return self.MIN_CACHE_TOKENS["flash"]
        elif "pro" in model_id.lower():
            return self.MIN_CACHE_TOKENS["pro"]
        else:
            return self.MIN_CACHE_TOKENS["default"]
    
    def _enforce_memory_limit(self):
        """Enforce memory limit using LRU eviction."""
        while len(self._cache_entries) > self._max_entries:
            # Remove least recently used
            oldest_id = next(iter(self._cache_entries))
            self._cache_entries.pop(oldest_id)
            logger.debug(f"Evicted cache entry {oldest_id} due to memory limit")
    
    async def _remove_cache(self, cache_id: str) -> bool:
        """Remove a cache entry (internal, assumes lock is held)."""
        entry = self._cache_entries.get(cache_id)
        if not entry:
            return False
        
        # Delete from Google if exists
        if entry.google_cache_name:
            try:
                await self.client.caches.delete_async(name=entry.google_cache_name)
                logger.info(f"Deleted Google cache: {entry.google_cache_name}")
            except Exception as e:
                logger.warning(f"Failed to delete Google cache: {e}")
        
        # Remove from memory
        del self._cache_entries[cache_id]
        return True
    
    def export_stats(self) -> Dict[str, Any]:
        """Export detailed statistics for monitoring."""
        stats = self._stats.to_dict()
        
        # Add cache entry details
        entries = []
        for entry in self._cache_entries.values():
            entries.append({
                "cache_id": entry.cache_id,
                "model_id": entry.model_id,
                "token_count": entry.token_count,
                "hit_count": entry.hit_count,
                "created_at": entry.created_at.isoformat(),
                "expires_at": entry.expires_at.isoformat(),
                "ttl_remaining": max(0, (entry.expires_at - datetime.now()).total_seconds())
            })
        
        stats["entries"] = entries
        stats["timestamp"] = datetime.now().isoformat()
        
        return stats

# Singleton instance
_cache_service_instance = None

def get_cache_service(model_service: ModelService) -> CacheService:
    """Get the singleton CacheService instance."""
    global _cache_service_instance
    if _cache_service_instance is None:
        _cache_service_instance = CacheService(model_service)
        # Background cleanup will be started when first needed in async context
    return _cache_service_instance