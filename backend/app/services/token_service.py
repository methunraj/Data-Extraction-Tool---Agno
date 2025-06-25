# app/services/token_service.py
import logging
from typing import Dict, Any, Optional
import tiktoken
import re

from .model_service import ModelService

logger = logging.getLogger(__name__)

class TokenService:
    """Service for token counting and estimation."""
    
    def __init__(self, model_service: ModelService):
        self.model_service = model_service
        # Initialize tokenizer (using cl100k_base as approximation for Gemini)
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.warning(f"Failed to load tiktoken encoder: {e}. Using character-based estimation.")
            self.tokenizer = None
    
    def estimate_text_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except Exception as e:
                logger.warning(f"Tokenizer failed, falling back to estimation: {e}")
        
        # Fallback: character-based estimation
        # Gemini models typically use ~4 characters per token
        return len(text) // 4
    
    def estimate_media_tokens(
        self, 
        media_type: str, 
        model_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Estimate token count for media content.
        
        Args:
            media_type: Type of media (image, video, audio, document)
            model_id: The model to use for token calculation
            metadata: Media metadata (dimensions, duration, pages, etc.)
            
        Returns:
            Estimated token count
        """
        model_config = self.model_service.get_model(model_id)
        if not model_config:
            # Default estimates
            defaults = {
                "image": 258,
                "video": 5000,
                "audio": 1000,
                "document": 1000
            }
            return defaults.get(media_type, 500)
        
        token_calc = model_config.get("tokenCalculation", {})
        metadata = metadata or {}
        
        if media_type == "image" and "image" in token_calc:
            return self._calculate_image_tokens(token_calc["image"], metadata)
        elif media_type == "video" and "video" in token_calc:
            duration = metadata.get("duration_seconds", 10)
            return duration * token_calc["video"]["tokensPerSecond"]
        elif media_type == "audio" and "audio" in token_calc:
            duration = metadata.get("duration_seconds", 30)
            return duration * token_calc["audio"]["tokensPerSecond"]
        elif media_type == "document" and "document" in token_calc:
            pages = metadata.get("pages", 4)
            return pages * token_calc["document"]["tokensPerPage"]
        else:
            # Default estimate
            return 500
    
    def _calculate_image_tokens(
        self, 
        image_config: Dict[str, Any], 
        metadata: Dict[str, Any]
    ) -> int:
        """Calculate tokens for an image based on dimensions."""
        width = metadata.get("width", 512)
        height = metadata.get("height", 512)
        max_dim = max(width, height)
        
        # Check if it's a small image
        if max_dim <= image_config["small"]["maxDimension"]:
            return image_config["small"]["tokens"]
        
        # Calculate tiles for larger images
        tile_size = image_config["tileSize"]
        tiles_w = (width + tile_size - 1) // tile_size
        tiles_h = (height + tile_size - 1) // tile_size
        total_tiles = tiles_w * tiles_h
        
        return total_tiles * image_config["tokensPerTile"]
    
    def estimate_json_tokens(self, json_obj: Any) -> int:
        """Estimate tokens for a JSON object."""
        import json
        json_str = json.dumps(json_obj, separators=(',', ':'))
        return self.estimate_text_tokens(json_str)
    
    def estimate_total_cost(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
        thinking_tokens: int = 0,
        cache_hours: float = 0
    ) -> Dict[str, float]:
        """
        Estimate total cost for token usage.
        
        Args:
            model_id: The model ID
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cached_tokens: Number of cached tokens
            thinking_tokens: Number of thinking tokens
            cache_hours: Hours of cache storage
            
        Returns:
            Dictionary with cost breakdown
        """
        usage = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_tokens": cached_tokens,
            "thinking_tokens": thinking_tokens,
            "cache_storage_hours": cache_hours,
            "cached_content_size": cached_tokens  # Assume cached content size equals cached tokens
        }
        
        total_cost = self.model_service.calculate_cost(model_id, usage)
        
        # Calculate breakdown
        breakdown = {
            "input_cost": 0.0,
            "output_cost": 0.0,
            "cache_cost": 0.0,
            "total_cost": total_cost
        }
        
        # Get detailed breakdown if possible
        model = self.model_service.get_model(model_id)
        if model and "pricing" in model:
            pricing = model["pricing"]
            
            # Input cost
            uncached_input = max(0, input_tokens - cached_tokens)
            if isinstance(pricing["input"], dict):
                breakdown["input_cost"] = (uncached_input / 1_000_000) * pricing["input"]["default"]
                if cached_tokens > 0 and "cached" in pricing["input"]:
                    breakdown["input_cost"] += (cached_tokens / 1_000_000) * pricing["input"]["cached"]
            else:
                breakdown["input_cost"] = (input_tokens / 1_000_000) * pricing["input"]
            
            # Output cost
            total_output = output_tokens
            if not pricing.get("output", {}).get("includesThinking", False):
                total_output += thinking_tokens
            
            if isinstance(pricing["output"], dict):
                breakdown["output_cost"] = (total_output / 1_000_000) * pricing["output"]["default"]
            else:
                breakdown["output_cost"] = (total_output / 1_000_000) * pricing["output"]
            
            # Cache cost
            if cache_hours > 0 and "cacheStorage" in pricing:
                breakdown["cache_cost"] = (cached_tokens / 1_000_000) * cache_hours * pricing["cacheStorage"]
        
        return breakdown
    
    def validate_token_limits(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Validate if token counts are within model limits.
        
        Args:
            model_id: The model ID
            input_tokens: Number of input tokens
            output_tokens: Expected number of output tokens
            
        Returns:
            Dictionary with validation results and warnings
        """
        model = self.model_service.get_model(model_id)
        if not model:
            return {
                "valid": False,
                "errors": [f"Model {model_id} not found"],
                "warnings": []
            }
        
        limits = model.get("limits", {})
        errors = []
        warnings = []
        
        # Check input token limit
        max_input = limits.get("maxInputTokens", float('inf'))
        if input_tokens > max_input:
            errors.append(f"Input tokens ({input_tokens}) exceed model limit ({max_input})")
        elif input_tokens > max_input * 0.9:
            warnings.append(f"Input tokens ({input_tokens}) are close to model limit ({max_input})")
        
        # Check output token limit if provided
        if output_tokens is not None:
            max_output = limits.get("maxOutputTokens", float('inf'))
            if output_tokens > max_output:
                errors.append(f"Output tokens ({output_tokens}) exceed model limit ({max_output})")
            elif output_tokens > max_output * 0.9:
                warnings.append(f"Output tokens ({output_tokens}) are close to model limit ({max_output})")
        
        # Check total context window
        context_window = limits.get("contextWindow", float('inf'))
        total_tokens = input_tokens + (output_tokens or 0)
        if total_tokens > context_window:
            errors.append(f"Total tokens ({total_tokens}) exceed context window ({context_window})")
        elif total_tokens > context_window * 0.9:
            warnings.append(f"Total tokens ({total_tokens}) are close to context window limit ({context_window})")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "limits": {
                "max_input_tokens": max_input,
                "max_output_tokens": limits.get("maxOutputTokens"),
                "context_window": context_window
            }
        }
    
    def truncate_text_to_tokens(self, text: str, max_tokens: int) -> str:
        """
        Truncate text to fit within token limit.
        
        Args:
            text: Text to truncate
            max_tokens: Maximum number of tokens
            
        Returns:
            Truncated text
        """
        if not text:
            return text
        
        current_tokens = self.estimate_text_tokens(text)
        if current_tokens <= max_tokens:
            return text
        
        # Binary search for the right length
        left, right = 0, len(text)
        result = ""
        
        while left < right:
            mid = (left + right + 1) // 2
            truncated = text[:mid]
            tokens = self.estimate_text_tokens(truncated)
            
            if tokens <= max_tokens:
                result = truncated
                left = mid
            else:
                right = mid - 1
        
        # Add ellipsis if truncated
        if len(result) < len(text):
            result = result.rstrip() + "..."
        
        return result