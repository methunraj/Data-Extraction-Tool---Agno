# app/routers/__init__.py
from .extraction import router as extraction_router
from .generation import router as generation_router
from .models import router as models_router
from .cache import router as cache_router
from .agents import router as agents_router

__all__ = [
    "extraction_router",
    "generation_router", 
    "models_router",
    "cache_router",
    "agents_router"
]