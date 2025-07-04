"""
Agno-native model configuration for IntelliExtract.
Pure Agno approach - no custom wrappers or abstractions.
"""
import os
from agno.models.google import Gemini
from typing import Optional


def get_extraction_model(model_id: Optional[str] = None, api_key: Optional[str] = None) -> Gemini:
    """Model for document extraction - fast and efficient."""
    return Gemini(
        id=model_id or os.environ.get("EXTRACTION_MODEL", "gemini-2.0-flash"),
        api_key=api_key or os.environ.get("GOOGLE_API_KEY")
    )


def get_reasoning_model(model_id: Optional[str] = None, api_key: Optional[str] = None) -> Gemini:
    """Model for complex reasoning - with thinking capability."""
    return Gemini(
        id=model_id or os.environ.get("AGNO_MODEL", "gemini-2.0-flash"), 
        api_key=api_key or os.environ.get("GOOGLE_API_KEY")
    )


def get_search_model(model_id: Optional[str] = None, api_key: Optional[str] = None) -> Gemini:
    """Model with search and grounding capabilities."""
    return Gemini(
        id=model_id or os.environ.get("SEARCH_MODEL", "gemini-2.0-flash"),
        api_key=api_key or os.environ.get("GOOGLE_API_KEY"),
        search=True,
        grounding=True
    )


def get_structured_model(model_id: Optional[str] = None, api_key: Optional[str] = None) -> Gemini:
    """Model for structured output generation."""
    return Gemini(
        id=model_id or os.environ.get("STRUCTURED_MODEL", "gemini-2.0-flash"),
        api_key=api_key or os.environ.get("GOOGLE_API_KEY")
    )


def get_transform_model(model_id: Optional[str] = None, api_key: Optional[str] = None) -> Gemini:
    """Model for data transformation and Excel generation."""
    return Gemini(
        id=model_id or os.environ.get("TRANSFORM_MODEL", "gemini-2.0-flash"),
        api_key=api_key or os.environ.get("GOOGLE_API_KEY")
    )