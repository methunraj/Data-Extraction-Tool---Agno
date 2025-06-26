import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class AgentDirectoryManager:
    """Ensures agents work in correct directories"""
    
    @staticmethod
    @contextmanager
    def agent_workspace(temp_dir: str):
        """Context manager to ensure agent works in correct directory"""
        original_cwd = os.getcwd()
        abs_temp_dir = os.path.abspath(temp_dir)
        
        try:
            # Create and enter directory
            os.makedirs(abs_temp_dir, exist_ok=True)
            os.chdir(abs_temp_dir)
            
            # Set environment variable (use realpath for consistency)
            real_path = os.path.realpath(abs_temp_dir)
            os.environ['AGENT_WORKSPACE'] = real_path
            os.environ['INTELLIEXTRACT_OUTPUT_DIR'] = real_path
            
            logger.info(f"Agent workspace set to: {abs_temp_dir}")
            # Resolve any symlinks to get the real path for comparison
            yield os.path.realpath(abs_temp_dir)
            
        finally:
            # Restore original directory
            os.chdir(original_cwd)
            if 'AGENT_WORKSPACE' in os.environ:
                del os.environ['AGENT_WORKSPACE']
            if 'INTELLIEXTRACT_OUTPUT_DIR' in os.environ:
                del os.environ['INTELLIEXTRACT_OUTPUT_DIR']
            logger.info(f"Restored working directory to: {original_cwd}")
    
    @staticmethod
    def ensure_directory_exists(directory: str) -> str:
        """Ensure directory exists and return absolute path"""
        abs_dir = os.path.abspath(directory)
        os.makedirs(abs_dir, exist_ok=True)
        return abs_dir
    
    @staticmethod
    def get_safe_temp_dir(base_name: str = "intelliextract") -> str:
        """Get a safe temporary directory for agent operations"""
        temp_dir = tempfile.mkdtemp(prefix=f"{base_name}_")
        logger.info(f"Created temporary directory: {temp_dir}")
        return temp_dir