# app/services/model_service.py
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
from datetime import datetime
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

logger = logging.getLogger(__name__)

class ModelConfigWatcher(FileSystemEventHandler):
    """Watch for changes to models.json file."""
    
    def __init__(self, callback):
        self.callback = callback
        
    def on_modified(self, event):
        if isinstance(event, FileModifiedEvent) and event.src_path.endswith('models.json'):
            logger.info("models.json file modified, reloading configuration")
            self.callback()

class ModelService:
    """Service for managing AI model configurations and pricing calculations."""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            # Default to app/config/models.json
            config_path = str(Path(__file__).parent.parent / "config" / "models.json")
        
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self._load_config()
        self._setup_file_watcher()
    
    def _load_config(self):
        """Load configuration from models.json file."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            logger.info(f"Loaded model configuration from {self.config_path}")
        except FileNotFoundError:
            logger.error(f"Model configuration file not found: {self.config_path}")
            self.config = {"models": {}}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in model configuration: {e}")
            self.config = {"models": {}}
    
    def _setup_file_watcher(self):
        """Set up file watcher for automatic config reload."""
        try:
            self.observer = Observer()
            event_handler = ModelConfigWatcher(self._load_config)
            self.observer.schedule(
                event_handler,
                path=str(Path(self.config_path).parent),
                recursive=False
            )
            self.observer.start()
            logger.info("File watcher set up for models.json")
        except Exception as e:
            logger.warning(f"Could not set up file watcher: {e}")
    
    def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get model configuration by ID."""
        return self.config.get("models", {}).get(model_id)
    
    def get_all_models(self) -> List[Dict[str, Any]]:
        """Get all available models."""
        return list(self.config.get("models", {}).values())
    
    def get_models_for_purpose(self, purpose: str) -> List[Dict[str, Any]]:
        """Get models that support a specific purpose (extraction, agno, etc)."""
        models = []
        for model in self.config.get("models", {}).values():
            if purpose in model.get("supportedIn", []):
                models.append(model)
        return models
    
    def get_model_pricing(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get pricing information for a specific model."""
        model = self.get_model(model_id)
        if model:
            return model.get("pricing")
        return None
    
    def calculate_cost(self, model_id: str, usage: Dict[str, int]) -> float:
        """
        Calculate cost based on token usage.
        
        Args:
            model_id: The model ID
            usage: Dictionary with keys:
                - input_tokens: Number of input tokens
                - output_tokens: Number of output tokens
                - cached_tokens: Number of cached input tokens (optional)
                - thinking_tokens: Number of thinking tokens (optional)
                - cache_storage_hours: Hours of cache storage (optional)
        
        Returns:
            Total cost in USD
        """
        model = self.get_model(model_id)
        if not model or "pricing" not in model:
            logger.warning(f"No pricing information found for model {model_id}")
            return 0.0
        
        pricing = model["pricing"]
        total_cost = 0.0
        
        # Calculate input cost
        input_tokens = usage.get("input_tokens", 0)
        cached_tokens = usage.get("cached_tokens", 0)
        uncached_tokens = max(0, input_tokens - cached_tokens)
        
        if isinstance(pricing["input"], dict):
            # Handle tiered pricing
            # Use "default" or "text" as base rate
            base_rate_key = "default" if "default" in pricing["input"] else "text"
            base_rate = pricing["input"][base_rate_key]
            
            if uncached_tokens > 200000 and "above200k" in pricing["input"]:
                # First 200k at base rate
                total_cost += (200000 / 1_000_000) * base_rate
                # Remaining at above200k rate
                total_cost += ((uncached_tokens - 200000) / 1_000_000) * pricing["input"]["above200k"]
            else:
                total_cost += (uncached_tokens / 1_000_000) * base_rate
            
            # Add cached token cost
            if cached_tokens > 0 and "cached" in pricing["input"]:
                if cached_tokens > 200000 and "cachedAbove200k" in pricing["input"]:
                    total_cost += (200000 / 1_000_000) * pricing["input"]["cached"]
                    total_cost += ((cached_tokens - 200000) / 1_000_000) * pricing["input"]["cachedAbove200k"]
                else:
                    total_cost += (cached_tokens / 1_000_000) * pricing["input"]["cached"]
        else:
            # Simple pricing
            total_cost += (input_tokens / 1_000_000) * pricing["input"]
        
        # Calculate output cost
        output_tokens = usage.get("output_tokens", 0)
        thinking_tokens = usage.get("thinking_tokens", 0)
        
        if isinstance(pricing["output"], dict):
            # Check if thinking is included in output
            if pricing["output"].get("includesThinking", False):
                total_output_tokens = output_tokens  # Thinking already included
            else:
                total_output_tokens = output_tokens + thinking_tokens
            
            # Handle tiered output pricing
            # Use "default" or "text" as base rate
            output_base_rate_key = "default" if "default" in pricing["output"] else "text"
            output_base_rate = pricing["output"][output_base_rate_key]
            
            if total_output_tokens > 200000 and "above200k" in pricing["output"]:
                total_cost += (200000 / 1_000_000) * output_base_rate
                total_cost += ((total_output_tokens - 200000) / 1_000_000) * pricing["output"]["above200k"]
            else:
                total_cost += (total_output_tokens / 1_000_000) * output_base_rate
        else:
            total_cost += ((output_tokens + thinking_tokens) / 1_000_000) * pricing["output"]
        
        # Calculate cache storage cost
        cache_hours = usage.get("cache_storage_hours", 0)
        if cache_hours > 0 and "cacheStorage" in pricing:
            # Cache storage is per million tokens per hour
            cache_size_tokens = usage.get("cached_content_size", cached_tokens)
            total_cost += (cache_size_tokens / 1_000_000) * cache_hours * pricing["cacheStorage"]
        
        return round(total_cost, 6)  # Round to 6 decimal places
    
    def estimate_tokens(self, model_id: str, content: Dict[str, Any]) -> Dict[str, int]:
        """
        Estimate token count for different types of content.
        
        Args:
            model_id: The model ID
            content: Dictionary with content types:
                - text: String of text
                - images: List of image info dicts with dimensions
                - documents: Number of document pages
                - video_seconds: Number of video seconds
                - audio_seconds: Number of audio seconds
        
        Returns:
            Dictionary with estimated token counts by type
        """
        model = self.get_model(model_id)
        if not model:
            return {}
        
        token_calc = model.get("tokenCalculation", {})
        estimates = {}
        
        # Text tokens (rough estimate: 1 token ≈ 4 characters)
        if "text" in content:
            estimates["text"] = len(content["text"]) // 4
        
        # Image tokens
        if "images" in content and "image" in token_calc:
            image_tokens = 0
            for img in content["images"]:
                width = img.get("width", 0)
                height = img.get("height", 0)
                max_dim = max(width, height)
                
                if max_dim <= token_calc["image"]["small"]["maxDimension"]:
                    image_tokens += token_calc["image"]["small"]["tokens"]
                else:
                    # Calculate tiles needed
                    tile_size = token_calc["image"]["tileSize"]
                    tiles_w = (width + tile_size - 1) // tile_size
                    tiles_h = (height + tile_size - 1) // tile_size
                    total_tiles = tiles_w * tiles_h
                    image_tokens += total_tiles * token_calc["image"]["tokensPerTile"]
            
            estimates["images"] = image_tokens
        
        # Document tokens
        if "documents" in content and "document" in token_calc:
            estimates["documents"] = content["documents"] * token_calc["document"]["tokensPerPage"]
        
        # Video tokens
        if "video_seconds" in content and "video" in token_calc:
            estimates["video"] = content["video_seconds"] * token_calc["video"]["tokensPerSecond"]
        
        # Audio tokens
        if "audio_seconds" in content and "audio" in token_calc:
            estimates["audio"] = content["audio_seconds"] * token_calc["audio"]["tokensPerSecond"]
        
        # Total
        estimates["total"] = sum(estimates.values())
        
        return estimates
    
    def get_provider_info(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """Get provider information."""
        return self.config.get("providers", {}).get(provider_id)
    
    def validate_model_for_purpose(self, model_id: str, purpose: str) -> bool:
        """Check if a model supports a specific purpose."""
        model = self.get_model(model_id)
        if not model:
            return False
        return purpose in model.get("supportedIn", [])
    
    def get_model_capabilities(self, model_id: str) -> Dict[str, Any]:
        """Get capabilities for a specific model."""
        model = self.get_model(model_id)
        if model:
            return model.get("capabilities", {})
        return {}
    
    def cleanup(self):
        """Clean up resources (stop file watcher)."""
        if hasattr(self, 'observer') and self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
            logger.info("File watcher stopped")

# Singleton instance
_model_service_instance = None

def get_model_service() -> ModelService:
    """Get the singleton ModelService instance."""
    global _model_service_instance
    if _model_service_instance is None:
        _model_service_instance = ModelService()
    return _model_service_instance