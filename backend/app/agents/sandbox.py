import subprocess
import sys
import os
import tempfile
import logging
import time
from typing import Optional, Dict, Any, Tuple, List
from pathlib import Path
from .execution_context import AgentExecutionContext

logger = logging.getLogger(__name__)

class AgentSandbox:
    """Run agent code in isolated environment with proper directory management"""
    
    def __init__(self, context: AgentExecutionContext):
        self.context = context
        self.working_dir = context.temp_dir
        self.execution_history: List[Dict[str, Any]] = []
    
    def execute_python(self, code: str, timeout: int = 300) -> Tuple[str, str, int]:
        """Execute Python code in sandbox with correct working directory"""
        execution_start = time.time()
        
        # Validate context before execution
        issues = self.context.validate_context()
        if issues:
            error_msg = "Context validation failed: " + "; ".join(issues)
            logger.error(error_msg)
            return "", error_msg, 1
        
        # Create wrapper script with comprehensive setup
        wrapper_code = self._create_wrapper_code(code)
        
        # Prepare execution environment
        env = self._prepare_environment()
        
        try:
            # Execute in subprocess with proper isolation
            result = subprocess.run(
                [sys.executable, '-c', wrapper_code],
                capture_output=True,
                text=True,
                cwd=self.working_dir,
                env=env,
                timeout=timeout
            )
            
            execution_time = time.time() - execution_start
            
            # Record execution
            self._record_execution(code, result, execution_time)
            
            return result.stdout, result.stderr, result.returncode
            
        except subprocess.TimeoutExpired:
            error_msg = f"Code execution timed out after {timeout} seconds"
            logger.error(error_msg)
            self._record_execution(code, None, time.time() - execution_start, error_msg)
            return "", error_msg, 124  # Timeout exit code
            
        except Exception as e:
            error_msg = f"Execution failed: {e}"
            logger.error(error_msg)
            self._record_execution(code, None, time.time() - execution_start, error_msg)
            return "", error_msg, 1
    
    def _create_wrapper_code(self, user_code: str) -> str:
        """Create wrapper code with proper environment setup"""
        # Indent user code properly
        indented_user_code = '\n'.join('    ' + line for line in user_code.split('\n'))
        
        return f'''
import os
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure we're in the correct working directory
target_dir = r'{self.working_dir}'
current_dir = os.getcwd()

if current_dir != target_dir:
    logger.info(f'Changing directory from {{current_dir}} to {{target_dir}}')
    os.chdir(target_dir)

# Verify directory change
actual_dir = os.getcwd()
logger.info(f'Working directory confirmed: {{actual_dir}}')

# Add working directory to Python path
if target_dir not in sys.path:
    sys.path.insert(0, target_dir)

# Set up environment variables for the execution
os.environ['AGENT_EXECUTION_MODE'] = 'sandbox'
os.environ['AGENT_WORKING_DIR'] = target_dir

# Verify environment
logger.info(f'Environment setup complete:')
logger.info(f'  Working directory: {{os.getcwd()}}')
logger.info(f'  Python path: {{sys.path[:3]}}...')
logger.info(f'  Agent temp dir: {{os.environ.get("AGENT_TEMP_DIR", "Not set")}}')

try:
    # Execute user code
{indented_user_code}
    
except Exception as e:
    logger.error(f'User code execution failed: {{e}}')
    import traceback
    traceback.print_exc()
    raise
'''
    
    def _prepare_environment(self) -> Dict[str, str]:
        """Prepare execution environment with all necessary variables"""
        env = os.environ.copy()
        
        # Add context environment variables
        env.update(self.context.env_vars)
        
        # Add sandbox-specific variables
        env.update({
            'AGENT_SANDBOX_MODE': 'true',
            'AGENT_EXECUTION_ID': f"exec_{int(time.time())}_{len(self.execution_history)}",
            'PYTHONPATH': self.working_dir,
            'PYTHONUNBUFFERED': '1',  # Ensure immediate output
        })
        
        return env
    
    def _record_execution(self, code: str, result: Optional[subprocess.CompletedProcess], 
                         execution_time: float, error: Optional[str] = None):
        """Record execution details for analysis"""
        record = {
            'timestamp': time.time(),
            'code_length': len(code),
            'execution_time': execution_time,
            'success': result is not None and result.returncode == 0 if result else False,
            'return_code': result.returncode if result else None,
            'stdout_length': len(result.stdout) if result and result.stdout else 0,
            'stderr_length': len(result.stderr) if result and result.stderr else 0,
            'error': error,
            'working_dir': self.working_dir,
            'context_session': self.context.session_id
        }
        
        self.execution_history.append(record)
        
        # Log execution summary
        status = "SUCCESS" if record['success'] else "FAILED"
        logger.info(f"Code execution {status}: {execution_time:.2f}s, "
                   f"stdout: {record['stdout_length']} chars, "
                   f"stderr: {record['stderr_length']} chars")
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        if not self.execution_history:
            return {'no_executions': True}
        
        total_executions = len(self.execution_history)
        successful_executions = sum(1 for record in self.execution_history if record['success'])
        
        execution_times = [record['execution_time'] for record in self.execution_history]
        avg_execution_time = sum(execution_times) / len(execution_times)
        
        return {
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'success_rate': successful_executions / total_executions,
            'average_execution_time': avg_execution_time,
            'total_execution_time': sum(execution_times),
            'context_session': self.context.session_id,
            'working_directory': self.working_dir
        }
    
    def validate_sandbox(self) -> List[str]:
        """Validate sandbox environment"""
        issues = []
        
        # Check working directory
        if not os.path.exists(self.working_dir):
            issues.append(f"Working directory does not exist: {self.working_dir}")
        elif not os.access(self.working_dir, os.W_OK):
            issues.append(f"No write access to working directory: {self.working_dir}")
        
        # Check Python executable
        if not os.path.exists(sys.executable):
            issues.append(f"Python executable not found: {sys.executable}")
        
        # Check context validation
        context_issues = self.context.validate_context()
        issues.extend(context_issues)
        
        # Test basic execution
        try:
            test_result = subprocess.run(
                [sys.executable, '-c', 'print("sandbox_test")'],
                capture_output=True,
                text=True,
                cwd=self.working_dir,
                timeout=5
            )
            
            if test_result.returncode != 0:
                issues.append(f"Basic Python execution failed: {test_result.stderr}")
            elif "sandbox_test" not in test_result.stdout:
                issues.append("Basic Python execution did not produce expected output")
                
        except Exception as e:
            issues.append(f"Could not test basic execution: {e}")
        
        return issues

class SandboxManager:
    """Manage multiple sandboxes"""
    
    def __init__(self):
        self.sandboxes: Dict[str, AgentSandbox] = {}
    
    def create_sandbox(self, context: AgentExecutionContext) -> AgentSandbox:
        """Create a new sandbox for the given context"""
        sandbox = AgentSandbox(context)
        
        # Validate sandbox before registering
        issues = sandbox.validate_sandbox()
        if issues:
            raise RuntimeError(f"Sandbox validation failed: {'; '.join(issues)}")
        
        self.sandboxes[context.session_id] = sandbox
        logger.info(f"Created sandbox for session: {context.session_id}")
        
        return sandbox
    
    def get_sandbox(self, session_id: str) -> Optional[AgentSandbox]:
        """Get sandbox by session ID"""
        return self.sandboxes.get(session_id)
    
    def cleanup_sandbox(self, session_id: str):
        """Cleanup and remove sandbox"""
        if session_id in self.sandboxes:
            del self.sandboxes[session_id]
            logger.info(f"Cleaned up sandbox: {session_id}")
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all sandboxes"""
        return {
            session_id: sandbox.get_execution_stats()
            for session_id, sandbox in self.sandboxes.items()
        }

# Global sandbox manager instance
sandbox_manager = SandboxManager()