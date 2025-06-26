import os
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict
from ..core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class AgentConfig:
    """Configuration for a specific agent type"""
    agent_type: str
    default_timeout: int = 300
    max_retries: int = 3
    memory_limit_mb: int = 512
    temp_dir_prefix: str = "agent"
    allowed_imports: List[str] = None
    restricted_operations: List[str] = None
    environment_vars: Dict[str, str] = None
    
    def __post_init__(self):
        if self.allowed_imports is None:
            self.allowed_imports = [
                'os', 'sys', 'json', 'csv', 'pandas', 'openpyxl', 
                'xlsxwriter', 'numpy', 'datetime', 'time', 'logging'
            ]
        
        if self.restricted_operations is None:
            self.restricted_operations = [
                'subprocess', 'eval', 'exec', 'compile', '__import__',
                'open', 'file', 'input', 'raw_input'
            ]
        
        if self.environment_vars is None:
            self.environment_vars = {}

@dataclass
class SystemConfig:
    """System-wide configuration"""
    max_concurrent_agents: int = 10
    default_temp_dir: str = "/tmp/intelliextract"
    cleanup_interval_hours: int = 24
    monitoring_enabled: bool = True
    debug_mode: bool = False
    log_level: str = "INFO"
    
    def __post_init__(self):
        # Override with environment variables if available
        if hasattr(settings, 'AGENT_TEMP_DIR') and settings.AGENT_TEMP_DIR:
            self.default_temp_dir = settings.AGENT_TEMP_DIR
        
        if hasattr(settings, 'AGNO_DEBUG'):
            self.debug_mode = settings.AGNO_DEBUG
        
        if hasattr(settings, 'LOG_LEVEL'):
            self.log_level = settings.LOG_LEVEL

class ConfigurationManager:
    """Centralized configuration management for agents"""
    
    def __init__(self):
        self.system_config = SystemConfig()
        self.agent_configs: Dict[str, AgentConfig] = {}
        self.config_file_path = Path("config") / "agent_configs.json"
        self._load_configurations()
    
    def _load_configurations(self):
        """Load configurations from file and set defaults"""
        # Set default configurations for known agent types
        self._set_default_configs()
        
        # Try to load from file
        if self.config_file_path.exists():
            try:
                with open(self.config_file_path, 'r') as f:
                    config_data = json.load(f)
                
                # Load system config
                if 'system' in config_data:
                    system_data = config_data['system']
                    for key, value in system_data.items():
                        if hasattr(self.system_config, key):
                            setattr(self.system_config, key, value)
                
                # Load agent configs
                if 'agents' in config_data:
                    for agent_type, agent_data in config_data['agents'].items():
                        self.agent_configs[agent_type] = AgentConfig(
                            agent_type=agent_type,
                            **agent_data
                        )
                
                logger.info(f"Loaded configurations from {self.config_file_path}")
                
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}, using defaults")
    
    def _set_default_configs(self):
        """Set default configurations for known agent types"""
        
        # CodeGen agent - needs file operations
        self.agent_configs['codegen'] = AgentConfig(
            agent_type='codegen',
            default_timeout=600,  # Longer timeout for code generation
            max_retries=3,
            memory_limit_mb=1024,  # More memory for Excel operations
            temp_dir_prefix='codegen',
            allowed_imports=[
                'os', 'sys', 'json', 'csv', 'pandas', 'openpyxl', 
                'xlsxwriter', 'numpy', 'datetime', 'time', 'logging',
                'shutil', 'glob', 'pathlib', 'tempfile'
            ],
            environment_vars={
                'EXCEL_ENGINE': 'openpyxl',
                'PANDAS_EXCEL_ENGINE': 'openpyxl'
            }
        )
        
        # Strategist agent - planning and analysis
        self.agent_configs['strategist'] = AgentConfig(
            agent_type='strategist',
            default_timeout=300,
            max_retries=2,
            memory_limit_mb=256,
            temp_dir_prefix='strategist'
        )
        
        # Search agent - web search operations
        self.agent_configs['search'] = AgentConfig(
            agent_type='search',
            default_timeout=180,
            max_retries=3,
            memory_limit_mb=256,
            temp_dir_prefix='search',
            allowed_imports=[
                'os', 'sys', 'json', 'requests', 'urllib', 'datetime', 'time'
            ]
        )
        
        # QA agent - quality assurance
        self.agent_configs['qa'] = AgentConfig(
            agent_type='qa',
            default_timeout=300,
            max_retries=2,
            memory_limit_mb=256,
            temp_dir_prefix='qa'
        )
    
    def get_agent_config(self, agent_type: str) -> AgentConfig:
        """Get configuration for specific agent type"""
        if agent_type not in self.agent_configs:
            logger.warning(f"No config found for agent type: {agent_type}, using default")
            return AgentConfig(agent_type=agent_type)
        
        return self.agent_configs[agent_type]
    
    def get_system_config(self) -> SystemConfig:
        """Get system configuration"""
        return self.system_config
    
    def update_agent_config(self, agent_type: str, **kwargs):
        """Update configuration for specific agent type"""
        if agent_type in self.agent_configs:
            config = self.agent_configs[agent_type]
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
                else:
                    logger.warning(f"Unknown config key: {key} for agent type: {agent_type}")
        else:
            self.agent_configs[agent_type] = AgentConfig(agent_type=agent_type, **kwargs)
        
        logger.info(f"Updated config for agent type: {agent_type}")
    
    def update_system_config(self, **kwargs):
        """Update system configuration"""
        for key, value in kwargs.items():
            if hasattr(self.system_config, key):
                setattr(self.system_config, key, value)
            else:
                logger.warning(f"Unknown system config key: {key}")
        
        logger.info("Updated system configuration")
    
    def save_configurations(self):
        """Save configurations to file"""
        try:
            # Ensure config directory exists
            self.config_file_path.parent.mkdir(exist_ok=True)
            
            config_data = {
                'system': asdict(self.system_config),
                'agents': {
                    agent_type: asdict(config) 
                    for agent_type, config in self.agent_configs.items()
                }
            }
            
            with open(self.config_file_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info(f"Saved configurations to {self.config_file_path}")
            
        except Exception as e:
            logger.error(f"Failed to save configurations: {e}")
    
    def validate_config(self, agent_type: str) -> List[str]:
        """Validate configuration for agent type"""
        issues = []
        
        config = self.get_agent_config(agent_type)
        
        # Check timeout values
        if config.default_timeout <= 0:
            issues.append(f"Invalid timeout: {config.default_timeout}")
        
        if config.default_timeout > 3600:  # 1 hour max
            issues.append(f"Timeout too high: {config.default_timeout}s (max 3600s)")
        
        # Check memory limits
        if config.memory_limit_mb <= 0:
            issues.append(f"Invalid memory limit: {config.memory_limit_mb}MB")
        
        if config.memory_limit_mb > 4096:  # 4GB max
            issues.append(f"Memory limit too high: {config.memory_limit_mb}MB (max 4096MB)")
        
        # Check retry values
        if config.max_retries < 0:
            issues.append(f"Invalid retry count: {config.max_retries}")
        
        if config.max_retries > 10:
            issues.append(f"Too many retries: {config.max_retries} (max 10)")
        
        return issues
    
    def get_temp_dir_for_agent(self, agent_type: str, request_id: str) -> str:
        """Get appropriate temp directory for agent"""
        config = self.get_agent_config(agent_type)
        
        # Use system default or agent-specific temp dir
        base_dir = self.system_config.default_temp_dir
        
        # Create agent-specific subdirectory
        agent_dir = os.path.join(base_dir, f"{config.temp_dir_prefix}_{request_id}")
        
        return agent_dir
    
    def get_environment_vars(self, agent_type: str) -> Dict[str, str]:
        """Get environment variables for agent type"""
        config = self.get_agent_config(agent_type)
        system_config = self.get_system_config()
        
        env_vars = {}
        
        # Add system-level environment variables
        env_vars.update({
            'AGENT_TYPE': agent_type,
            'AGENT_DEBUG_MODE': str(system_config.debug_mode),
            'AGENT_LOG_LEVEL': system_config.log_level,
            'AGENT_MONITORING_ENABLED': str(system_config.monitoring_enabled)
        })
        
        # Add agent-specific environment variables
        env_vars.update(config.environment_vars)
        
        return env_vars
    
    def export_config(self) -> Dict[str, Any]:
        """Export all configurations for debugging"""
        return {
            'system': asdict(self.system_config),
            'agents': {
                agent_type: asdict(config)
                for agent_type, config in self.agent_configs.items()
            }
        }

# Global configuration manager instance
config_manager = ConfigurationManager()