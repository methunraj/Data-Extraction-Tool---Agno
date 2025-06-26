# IntelliExtract Agent Architecture

## Overview

This document describes the long-term architecture improvements implemented to prevent file creation and directory management issues in the IntelliExtract system.

## Architecture Components

### 1. Execution Context System (`execution_context.py`)

**Purpose**: Encapsulate all execution context for agents with proper isolation and management.

**Key Features**:
- Absolute path enforcement
- Environment variable management
- Directory structure creation (output, temp, logs)
- Context validation and cleanup
- Session-based isolation

**Usage**:
```python
from app.agents.execution_context import AgentExecutionContext, context_manager

# Create context
context = context_manager.create_context(
    temp_dir="/tmp/agent_work",
    request_id="req_123",
    user_id="user_456"
)

# Use context
with context:
    # Agent operations here
    output_path = context.get_output_path("report.xlsx")
```

### 2. Agent Sandbox (`sandbox.py`)

**Purpose**: Provide isolated execution environment for agent code with proper directory management.

**Key Features**:
- Subprocess isolation
- Working directory enforcement
- Environment variable injection
- Execution monitoring and statistics
- Timeout and resource management

**Usage**:
```python
from app.agents.sandbox import AgentSandbox, sandbox_manager

# Create sandbox
sandbox = sandbox_manager.create_sandbox(context)

# Execute code
stdout, stderr, returncode = sandbox.execute_python(code, timeout=300)
```

### 3. Configuration Management (`config_manager.py`)

**Purpose**: Centralized configuration for all agent types with validation and defaults.

**Key Features**:
- Agent-specific configurations
- System-wide settings
- Environment variable integration
- Configuration validation
- Persistent configuration storage

**Configuration Structure**:
```python
@dataclass
class AgentConfig:
    agent_type: str
    default_timeout: int = 300
    max_retries: int = 3
    memory_limit_mb: int = 512
    temp_dir_prefix: str = "agent"
    allowed_imports: List[str] = None
    restricted_operations: List[str] = None
    environment_vars: Dict[str, str] = None
```

### 4. Validation Framework (`validation_framework.py`)

**Purpose**: Comprehensive validation of code and execution context before agent execution.

**Validation Rules**:
- **Security**: Check for dangerous operations (subprocess, eval, etc.)
- **Imports**: Validate against allowed import list
- **File Operations**: Ensure operations stay within bounds
- **Resources**: Check for potential memory/performance issues

**Usage**:
```python
from app.agents.validation_framework import execution_validator

# Validate code and context
summary = execution_validator.get_validation_summary(context, code)
if summary['overall_status'] == 'blocked':
    raise SecurityError("Code validation failed")
```

## Integration with Existing System

### Enhanced Agent Base Class

The existing `BaseAgent` class has been enhanced to use the new architecture:

```python
class BaseAgent(ABC):
    def __init__(self, agent_type: str, temp_dir: Optional[str] = None, model_id: Optional[str] = None):
        self.agent_type = agent_type
        self.temp_dir = temp_dir
        self.model_id = model_id
        
        # NEW: Get configuration
        self.config = config_manager.get_agent_config(agent_type)
        
        # NEW: Create execution context
        self.context = None
        if temp_dir:
            self.context = context_manager.create_context(
                temp_dir=temp_dir,
                request_id=f"{agent_type}_{uuid.uuid4().hex[:8]}",
                metadata={'agent_type': agent_type}
            )
```

### Enhanced CodeGen Agent

The `CodeGenAgent` now uses the new architecture:

```python
class CodeGenAgent(BaseAgent):
    def execute_code(self, code: str) -> Tuple[str, str, int]:
        # Validate code before execution
        validation = execution_validator.get_validation_summary(self.context, code)
        if validation['overall_status'] == 'blocked':
            raise ValidationError("Code validation failed")
        
        # Create sandbox and execute
        sandbox = sandbox_manager.create_sandbox(self.context)
        return sandbox.execute_python(code, timeout=self.config.default_timeout)
```

## Directory Management Strategy

### 1. Hierarchical Directory Structure

```
/tmp/intelliextract/
├── codegen_req123/
│   ├── output/          # Final output files
│   ├── temp/           # Temporary files
│   ├── logs/           # Execution logs
│   └── workspace/      # Agent working directory
├── strategist_req124/
└── search_req125/
```

### 2. Path Resolution Rules

1. **All paths are absolute**: No relative path confusion
2. **Context-based paths**: All file operations go through context
3. **Validation before use**: Paths validated before any operation
4. **Cleanup on completion**: Automatic cleanup of temporary resources

### 3. Environment Variable Management

Each agent execution gets isolated environment variables:

```bash
AGENT_TEMP_DIR=/tmp/intelliextract/codegen_req123
AGENT_OUTPUT_DIR=/tmp/intelliextract/codegen_req123/output
AGENT_LOGS_DIR=/tmp/intelliextract/codegen_req123/logs
AGENT_REQUEST_ID=req123
AGENT_SESSION_ID=session_abc123
AGENT_TYPE=codegen
```

## Security Considerations

### 1. Code Validation

- **Import restrictions**: Only allowed imports can be used
- **Operation restrictions**: Dangerous operations are blocked
- **Path validation**: File operations must stay within bounds
- **Resource limits**: Memory and execution time limits

### 2. Execution Isolation

- **Subprocess isolation**: Code runs in separate process
- **Working directory enforcement**: Guaranteed correct working directory
- **Environment isolation**: Clean environment for each execution
- **Timeout protection**: Prevents runaway processes

### 3. File System Protection

- **Sandboxed file access**: All file operations within designated directories
- **Path traversal prevention**: No access to system directories
- **Permission validation**: Proper file permissions enforced
- **Cleanup guarantees**: Temporary files always cleaned up

## Monitoring and Observability

### 1. Execution Monitoring

- **Real-time tracking**: All executions monitored
- **Performance metrics**: Duration, memory usage, success rates
- **Error analysis**: Detailed error categorization and patterns
- **Historical data**: Execution history for trend analysis

### 2. Configuration Monitoring

- **Configuration validation**: Continuous validation of settings
- **Change tracking**: All configuration changes logged
- **Performance impact**: Monitor impact of configuration changes
- **Alerting**: Notifications for configuration issues

### 3. Health Monitoring

- **System health**: Overall system health status
- **Resource usage**: Monitor disk space, memory, CPU
- **Error rates**: Track error rates and patterns
- **Performance trends**: Long-term performance analysis

## Migration Strategy

### Phase 1: Backward Compatibility
- New architecture components added alongside existing code
- Existing agents continue to work without changes
- Gradual migration of agents to new architecture

### Phase 2: Enhanced Integration
- Update existing agents to use new context system
- Add validation to critical code paths
- Implement monitoring for all executions

### Phase 3: Full Migration
- All agents use new architecture
- Remove legacy code paths
- Full validation and monitoring coverage

## Best Practices

### 1. Agent Development

```python
# DO: Use execution context
context = context_manager.create_context(temp_dir, request_id)
output_path = context.get_output_path("report.xlsx")

# DON'T: Use hardcoded paths
output_path = "/tmp/report.xlsx"  # BAD

# DO: Validate before execution
validation = execution_validator.validate_code(context, code)
if validation['status'] == 'blocked':
    raise ValidationError()

# DON'T: Execute without validation
exec(code)  # BAD
```

### 2. Configuration Management

```python
# DO: Use configuration manager
config = config_manager.get_agent_config('codegen')
timeout = config.default_timeout

# DON'T: Hardcode configuration
timeout = 300  # BAD

# DO: Validate configuration
issues = config_manager.validate_config('codegen')
if issues:
    logger.error(f"Config issues: {issues}")
```

### 3. Error Handling

```python
# DO: Comprehensive error handling
try:
    result = sandbox.execute_python(code)
except ValidationError as e:
    logger.error(f"Validation failed: {e}")
    return error_response(e)
except TimeoutError as e:
    logger.error(f"Execution timeout: {e}")
    return timeout_response(e)
finally:
    context_manager.cleanup_context(session_id)
```

## Future Enhancements

### 1. Advanced Sandboxing
- Container-based isolation (Docker)
- Resource quotas and limits
- Network isolation
- File system quotas

### 2. Enhanced Monitoring
- Real-time dashboards
- Predictive analytics
- Automated alerting
- Performance optimization suggestions

### 3. Configuration Management
- Dynamic configuration updates
- A/B testing for configurations
- Configuration versioning
- Rollback capabilities

### 4. Security Enhancements
- Code signing and verification
- Advanced threat detection
- Audit logging
- Compliance reporting

## Conclusion

This architecture provides a robust, secure, and maintainable foundation for agent execution that prevents the directory and file management issues experienced previously. The modular design allows for gradual adoption and future enhancements while maintaining backward compatibility.

The key benefits include:

1. **Reliability**: Consistent file creation in correct locations
2. **Security**: Comprehensive validation and sandboxing
3. **Maintainability**: Centralized configuration and monitoring
4. **Scalability**: Modular design supports future growth
5. **Observability**: Complete visibility into system behavior

This architecture ensures that similar issues will not occur in the future and provides a solid foundation for continued development and enhancement of the IntelliExtract system.