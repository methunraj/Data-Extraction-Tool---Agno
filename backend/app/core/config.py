# app/core/config.py
import os
import logging
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import field_validator
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Explicitly load the .env file with robust path discovery
def find_env_file():
    """Find .env file by searching up the directory tree."""
    current_path = Path(__file__).resolve()
    for parent in [current_path.parent] + list(current_path.parents):
        env_path = parent / ".env"
        if env_path.exists():
            return env_path
    return None

env_path = find_env_file()
if env_path:
    load_dotenv(env_path)
    logger.info(f"Loaded environment variables from {env_path}")
else:
    # Fallback to load_dotenv() which searches automatically
    load_dotenv()
    logger.warning("No .env file found, using system environment variables")

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    LOG_LEVEL: str = "INFO"
    APP_VERSION: str = "3.0.0-refactored"
    APP_TITLE: str = "IntelliExtract Agno AI JSON to XLSX Processing API"
    TEMP_DIR_PREFIX: str = "intelliextract_agno_xlsx_"
    
    # Model Configuration
    DEFAULT_AI_MODEL: str = os.getenv("DEFAULT_AI_MODEL", "gemini-2.0-flash-001")
    
    # Monitoring Configuration
    AGNO_API_KEY: str = os.getenv("AGNO_API_KEY", "")
    AGNO_MONITOR: bool = os.getenv("AGNO_MONITOR", "false").lower() == "true"
    AGNO_DEBUG: bool = os.getenv("AGNO_DEBUG", "false").lower() == "true"
    DEVELOPMENT_MODE: bool = os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"
    
    # Performance & Security Settings
    MAX_FILE_SIZE_MB: int = 100  # Maximum file size in MB
    MAX_REQUEST_SIZE_MB: int = 200  # Maximum total request size in MB
    MAX_UPLOAD_SIZE_MB: int = 150  # Maximum upload size in MB
    
    # CORS Configuration
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:9002")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    MAX_JSON_SIZE_MB: int = 50   # Maximum JSON payload size in MB
    REQUEST_TIMEOUT_SECONDS: int = 1200  # 20 minutes
    CLEANUP_DELAY_SECONDS: int = 300  # 5 minutes delay before cleanup
    MAX_POOL_SIZE: int = 10  # Maximum number of agents in pool
    AGENT_STORAGE_CLEANUP_HOURS: int = 24  # Clean up agent storage after 24 hours
    
    # Directory Configuration
    AGENT_TEMP_DIR: str = os.getenv("AGENT_TEMP_DIR", "")
    
    @field_validator('GOOGLE_API_KEY')
    @classmethod
    def validate_google_api_key(cls, v):
        if not v:
            logger.warning("GOOGLE_API_KEY is not set. AI processing will fail.")
        elif len(v) < 20:  # Basic length check
            logger.warning("GOOGLE_API_KEY appears to be invalid (too short).")
        return v
    
    @field_validator('AGNO_API_KEY')
    @classmethod
    def validate_agno_api_key(cls, v, info):
        # In Pydantic v2, we need to access other field values differently
        if hasattr(info, 'data') and info.data.get('AGNO_MONITOR') and not v:
            logger.warning("AGNO_MONITOR is enabled but AGNO_API_KEY is not set. Monitoring may not work properly.")
        return v

    class Config:
        # Use absolute path to .env file
        env_file = str(Path(__file__).parent.parent.parent / ".env")
        env_file_encoding = 'utf-8'

settings = Settings()

# Validate critical settings on startup
if not settings.GOOGLE_API_KEY:
    logger.critical("GOOGLE_API_KEY is not configured. AI features will not work!")
else:
    logger.info("Configuration loaded successfully")
