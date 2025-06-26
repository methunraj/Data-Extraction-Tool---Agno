"""Model utilities to avoid circular imports."""

# Singleton instance
_model_service_instance = None

def get_model_service():
    """Get the singleton ModelService instance."""
    global _model_service_instance
    if _model_service_instance is None:
        from ..services.model_service import ModelService
        _model_service_instance = ModelService()
    return _model_service_instance