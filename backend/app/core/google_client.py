# app/core/google_client.py
from google import genai
from google.genai import types
from typing import Optional, Dict, Any
import os
import logging
from .config import settings

logger = logging.getLogger(__name__)

class GoogleGenAIClient:
    """
    Singleton wrapper for Google GenAI client with configuration management.
    """
    _instance: Optional[genai.Client] = None
    
    @classmethod
    def get_client(cls) -> genai.Client:
        """Get or create the Google GenAI client instance."""
        if cls._instance is None:
            try:
                cls._instance = genai.Client(
                    api_key=settings.GOOGLE_API_KEY,
                    http_options=types.HttpOptions(api_version="v1beta")
                )
                logger.info("Google GenAI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Google GenAI client: {e}")
                raise
        return cls._instance
    
    @classmethod
    def reset_client(cls):
        """Reset the client instance (useful for testing)."""
        cls._instance = None
    
    @classmethod
    def validate_api_key(cls) -> bool:
        """Validate that the API key is set and appears valid."""
        if not settings.GOOGLE_API_KEY:
            return False
        return len(settings.GOOGLE_API_KEY) >= 20  # Basic length check
    
    @classmethod
    async def test_connection(cls) -> bool:
        """Test the connection to Google GenAI API."""
        try:
            client = cls.get_client()
            # Simple test: list available models
            models = await client.models.list()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Google GenAI: {e}")
            return False
    
    @classmethod
    def create_generation_config(
        cls,
        temperature: float = 0.7,
        response_mime_type: str = "text/plain",
        response_schema: Optional[Dict[str, Any]] = None,
        thinking_config: Optional[Dict[str, Any]] = None,
        max_output_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        stop_sequences: Optional[list] = None
    ) -> types.GenerateContentConfig:
        """Create a generation configuration with common settings."""
        config_dict = {
            "temperature": temperature,
            "response_mime_type": response_mime_type
        }
        
        if response_schema:
            config_dict["response_schema"] = response_schema
        
        if max_output_tokens:
            config_dict["max_output_tokens"] = max_output_tokens
        
        if top_p is not None:
            config_dict["top_p"] = top_p
        
        if top_k is not None:
            config_dict["top_k"] = top_k
        
        if stop_sequences:
            config_dict["stop_sequences"] = stop_sequences
        
        config = types.GenerateContentConfig(**config_dict)
        
        # Add thinking configuration if provided and supported
        if thinking_config:
            config.thinking_config = types.ThinkingConfig(
                thinking_budget=thinking_config.get("thinking_budget", -1)
            )
        
        return config