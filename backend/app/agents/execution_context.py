from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import os
import uuid
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class AgentExecutionContext:
    """Encapsulate all execution context for agents"""
    temp_dir: str
    request_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    env_vars: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    
    def __post_init__(self):
        # Ensure absolute paths
        self.temp_dir = os.path.abspath(self.temp_dir)
        
        # Generate session_id if not provided
        if self.session_id is None:
            self.session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        # Add standard env vars
        self.env_vars.update({
            'AGENT_TEMP_DIR': self.temp_dir,
            'AGENT_REQUEST_ID': self.request_id,
            'AGENT_SESSION_ID': self.session_id,
            'AGENT_WORKING_DIR': self.temp_dir,
        })
        
        # Add user context if available
        if self.user_id:
            self.env_vars['AGENT_USER_ID'] = self.user_id
    
    def setup_environment(self) -> bool:
        """Setup execution environment"""
        try:
            # Create directory structure
            os.makedirs(self.temp_dir, exist_ok=True)
            
            # Create subdirectories for organization
            subdirs = ['output', 'temp', 'logs']
            for subdir in subdirs:
                subdir_path = os.path.join(self.temp_dir, subdir)
                os.makedirs(subdir_path, exist_ok=True)
                self.env_vars[f'AGENT_{subdir.upper()}_DIR'] = subdir_path
            
            # Set environment variables
            for key, value in self.env_vars.items():
                os.environ[key] = value
            
            # Validate setup
            if not os.path.exists(self.temp_dir):
                raise RuntimeError(f"Failed to create temp directory: {self.temp_dir}")
            
            if not os.access(self.temp_dir, os.W_OK):
                raise RuntimeError(f"No write access to temp directory: {self.temp_dir}")
            
            logger.info(f"Execution context setup complete: {self.temp_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup execution context: {e}")
            return False
    
    def cleanup_environment(self):
        """Cleanup execution environment"""
        try:
            # Remove environment variables
            for key in list(self.env_vars.keys()):
                if key in os.environ:
                    del os.environ[key]
            
            logger.info(f"Execution context cleaned up: {self.session_id}")
            
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
    
    def get_output_path(self, filename: str) -> str:
        """Get path for output file"""
        output_dir = self.env_vars.get('AGENT_OUTPUT_DIR', self.temp_dir)
        return os.path.join(output_dir, filename)
    
    def get_temp_path(self, filename: str) -> str:
        """Get path for temporary file"""
        temp_dir = self.env_vars.get('AGENT_TEMP_DIR', self.temp_dir)
        return os.path.join(temp_dir, 'temp', filename)
    
    def get_log_path(self, filename: str) -> str:
        """Get path for log file"""
        log_dir = self.env_vars.get('AGENT_LOGS_DIR', self.temp_dir)
        return os.path.join(log_dir, filename)
    
    def validate_context(self) -> List[str]:
        """Validate execution context and return any issues"""
        issues = []
        
        # Check directory existence and permissions
        if not os.path.exists(self.temp_dir):
            issues.append(f"Temp directory does not exist: {self.temp_dir}")
        elif not os.access(self.temp_dir, os.W_OK):
            issues.append(f"No write access to temp directory: {self.temp_dir}")
        
        # Check required environment variables
        required_vars = ['AGENT_TEMP_DIR', 'AGENT_REQUEST_ID', 'AGENT_SESSION_ID']
        for var in required_vars:
            if var not in self.env_vars:
                issues.append(f"Missing required environment variable: {var}")
        
        # Check disk space (basic check)
        try:
            stat = os.statvfs(self.temp_dir)
            free_space = stat.f_bavail * stat.f_frsize
            if free_space < 100 * 1024 * 1024:  # Less than 100MB
                issues.append(f"Low disk space: {free_space / (1024*1024):.1f}MB available")
        except Exception as e:
            issues.append(f"Could not check disk space: {e}")
        
        return issues
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for serialization"""
        return {
            'temp_dir': self.temp_dir,
            'request_id': self.request_id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'env_vars': self.env_vars,
            'metadata': self.metadata,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentExecutionContext':
        """Create context from dictionary"""
        return cls(
            temp_dir=data['temp_dir'],
            request_id=data['request_id'],
            user_id=data.get('user_id'),
            session_id=data.get('session_id'),
            env_vars=data.get('env_vars', {}),
            metadata=data.get('metadata', {}),
            created_at=data.get('created_at', time.time())
        )

class ExecutionContextManager:
    """Manage multiple execution contexts"""
    
    def __init__(self):
        self.contexts: Dict[str, AgentExecutionContext] = {}
    
    def create_context(self, temp_dir: str, request_id: str, 
                      user_id: Optional[str] = None, 
                      **kwargs) -> AgentExecutionContext:
        """Create and register a new execution context"""
        context = AgentExecutionContext(
            temp_dir=temp_dir,
            request_id=request_id,
            user_id=user_id,
            **kwargs
        )
        
        # Setup the context
        if context.setup_environment():
            self.contexts[context.session_id] = context
            logger.info(f"Created execution context: {context.session_id}")
            return context
        else:
            raise RuntimeError(f"Failed to setup execution context for request: {request_id}")
    
    def get_context(self, session_id: str) -> Optional[AgentExecutionContext]:
        """Get execution context by session ID"""
        return self.contexts.get(session_id)
    
    def cleanup_context(self, session_id: str):
        """Cleanup and remove execution context"""
        if session_id in self.contexts:
            context = self.contexts[session_id]
            context.cleanup_environment()
            del self.contexts[session_id]
            logger.info(f"Cleaned up execution context: {session_id}")
    
    def cleanup_old_contexts(self, max_age_hours: int = 24):
        """Cleanup contexts older than specified age"""
        cutoff_time = time.time() - (max_age_hours * 3600)
        old_contexts = [
            session_id for session_id, context in self.contexts.items()
            if context.created_at < cutoff_time
        ]
        
        for session_id in old_contexts:
            self.cleanup_context(session_id)
        
        if old_contexts:
            logger.info(f"Cleaned up {len(old_contexts)} old execution contexts")
    
    def get_all_contexts(self) -> Dict[str, AgentExecutionContext]:
        """Get all active contexts"""
        return self.contexts.copy()

# Global context manager instance
context_manager = ExecutionContextManager()