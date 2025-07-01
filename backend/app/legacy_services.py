# app/services.py
import os
import json
import uuid
import time
import glob
import logging
import pandas as pd
from pathlib import Path
import asyncio
import traceback
from functools import lru_cache
from typing import Dict, List, Tuple, Any, Optional, Iterator
import tempfile

# Set Matplotlib backend to a non-GUI backend to avoid threading issues
import matplotlib
matplotlib.use('Agg')  # Must be before any other matplotlib imports

from agno.agent import Agent, RunResponse
from agno.workflow import Workflow

from .core.config import settings
from .prompts import load_prompt
# from .agents import create_agent  # Legacy import - removed
# Placeholder for create_agent function
def create_agent(*args, **kwargs):
    raise NotImplementedError("create_agent has been removed in the Agno-native refactor")
# from .agents.utils.directory_manager import AgentDirectoryManager  # Legacy import - removed
# from .agents.utils.execution_monitor import execution_monitor  # Legacy import - removed

# Placeholder classes
class AgentDirectoryManager:
    def __init__(self, *args, **kwargs):
        pass
    def get_agent_dir(self, *args, **kwargs):
        return tempfile.mkdtemp()

class ExecutionMonitor:
    def track_execution(self, *args, **kwargs):
        return lambda x: x
    def get_success_metrics(self):
        return {}
    def get_failure_patterns(self):
        return {}

execution_monitor = ExecutionMonitor()

logger = logging.getLogger(__name__)

# Lazy import for WebSocket to avoid circular dependency
event_broadcaster = None

def _get_event_broadcaster():
    global event_broadcaster
    if event_broadcaster is None:
        try:
            from .routers.websocket import event_broadcaster as eb
            event_broadcaster = eb
        except ImportError:
            # Fallback if WebSocket not available
            logger.warning("WebSocket event broadcaster not available")
            event_broadcaster = None
    return event_broadcaster

# Lazy import to avoid circular dependency
model_service = None

def _get_model_service():
    global model_service
    if model_service is None:
        try:
            from .utils.model_utils import get_model_service
            model_service = get_model_service()
        except ImportError:
            # Fallback if circular import issues
            model_service = None
    return model_service

def get_agno_model() -> str:
    """Get the configured model for Agno processing."""
    # Try to get a model that supports 'agno' purpose
    service = _get_model_service()
    if service:
        try:
            agno_models = service.get_models_for_purpose("agno")
            if agno_models:
                # Prefer 2.0-flash models for speed, fall back to 2.5-flash for compatibility
                for model in agno_models:
                    if "2.0-flash" in model["id"]:
                        return model["id"]
                for model in agno_models:
                    if "2.5-flash" in model["id"]:
                        return model["id"]
                # Return first available agno model
                return agno_models[0]["id"]
        except Exception as e:
            logger.warning(f"Failed to get agno models from service: {e}")
    
    # Fallback to default if no agno models found or service unavailable
    return settings.DEFAULT_AI_MODEL

# Set up Agno monitoring environment variables if configured
if settings.AGNO_API_KEY:
    os.environ["AGNO_API_KEY"] = settings.AGNO_API_KEY
if settings.AGNO_MONITOR:
    os.environ["AGNO_MONITOR"] = "true"
if settings.AGNO_DEBUG:
    os.environ["AGNO_DEBUG"] = "true"

# Agent pool for reusing initialized agents (lightweight in Agno ~3.75 KiB per agent)
AGENT_POOL: Dict[str, Agent] = {}
MAX_POOL_SIZE = settings.MAX_POOL_SIZE  # Reasonable limit for different model types

AGENT_CLASSES = {
    # Transform data agents
    "strategist": ("transform_data", "StrategistAgent"),
    "search": ("transform_data", "SearchAgent"),
    "codegen": ("transform_data", "CodeGenAgent"),
    "qa": ("transform_data", "QualityAssuranceAgent"),
    # Prompt engineer agent
    "prompt_engineer": ("prompt_engineer", "PromptEngineerAgent"),
}

def get_agent_by_key(agent_type: str, **kwargs) -> Agent:
    """Get or create an agent from the pool based on type and current model configuration.
    
    Args:
        agent_type: Type of agent ('search', 'strategist', 'qa', 'codegen')
        **kwargs: Additional arguments for agent creation (e.g., temp_dir for codegen, model_id for custom model)
    
    Returns:
        Agent instance from pool or newly created
    """
    if agent_type not in AGENT_CLASSES:
        raise ValueError(f"Unknown agent type: {agent_type}")

    # Get model - use provided model_id or fallback to default agno model
    model_id = kwargs.pop('model_id', None)
    current_model = model_id if model_id else get_agno_model()
    cache_key = f"{agent_type}_{current_model}"
    
    # Check if agent exists in pool
    if cache_key in AGENT_POOL:
        logger.debug(f"Retrieved {agent_type} agent from pool for model {current_model}")
        return AGENT_POOL[cache_key]
    
    # Clean up pool if it's at capacity
    if len(AGENT_POOL) >= MAX_POOL_SIZE:
        # Remove oldest entries (simple FIFO for now)
        oldest_key = next(iter(AGENT_POOL))
        removed_agent = AGENT_POOL.pop(oldest_key)
        logger.info(f"Removed agent {oldest_key} from pool to make space")
    
    # Create new agent using factory function
    module_path, agent_class_name = AGENT_CLASSES[agent_type]
    agent = create_agent(agent_type, model_id=current_model, **kwargs)
    
    # Add to pool
    AGENT_POOL[cache_key] = agent
    logger.info(f"Created and cached {agent_type} agent for model {current_model} (pool size: {len(AGENT_POOL)})")
    
    return agent


# Agent creation functions removed - now using agent classes from .agents module


class FinancialReportWorkflow(Workflow):
    """A stateful, deterministic workflow for generating financial reports."""

    def __init__(self, temp_dir: str = None, model_id: Optional[str] = None):
        super().__init__()
        
        # Use configured temp directory or create one
        if temp_dir:
            self.temp_dir = AgentDirectoryManager.ensure_directory_exists(temp_dir)
        elif settings.AGENT_TEMP_DIR:
            self.temp_dir = AgentDirectoryManager.ensure_directory_exists(settings.AGENT_TEMP_DIR)
        else:
            self.temp_dir = AgentDirectoryManager.get_safe_temp_dir()
            
        self.model_id = model_id
        # Use pooled agents for better performance and dynamic model selection
        self.strategist = get_agent_by_key("strategist", model_id=model_id)
        self.search_agent = get_agent_by_key("search", model_id=model_id)
        self.code_gen_agent = get_agent_by_key("codegen", temp_dir=self.temp_dir, model_id=model_id)
        self.qa_agent = get_agent_by_key("qa", model_id=model_id)

    def run_workflow(self, json_data: Dict[str, Any], cancellation_event: asyncio.Event) -> Iterator[RunResponse]:
        """Executes the financial report generation workflow."""
        # Start monitoring
        execution_id = f"workflow_{self.run_id}_{int(time.time())}"
        execution_monitor.start_execution(execution_id, "workflow", self.temp_dir)
        
        # Broadcast workflow start event
        broadcaster = _get_event_broadcaster()
        if broadcaster:
            try:
                asyncio.create_task(broadcaster.workflow_started(
                    workflow_id=execution_id,
                    request_id=self.run_id,
                    agents=["strategist", "search", "codegen", "qa"]
                ))
            except Exception as e:
                logger.warning(f"Failed to broadcast workflow start: {e}")
        
        workflow_success = False
        error_message = None
        
        try:
            # Use a unique key for caching based on the JSON data content
            cache_key = json.dumps(json_data, sort_keys=True)
            if self.session_state.get(cache_key):
                logger.info(f"Cache hit for the report.")
                workflow_success = True
                yield RunResponse(
                    run_id=self.run_id, content=self.session_state.get(cache_key)
                )
                return

            # 1. Strategist Agent
            if broadcaster:
                try:
                    asyncio.create_task(broadcaster.agent_started("strategist", self.run_id))
                except Exception as e:
                    logger.warning(f"Failed to broadcast strategist start: {e}")
                    
            plan_prompt = f"Create a detailed execution plan to convert the following JSON data into a comprehensive Excel report:\\\\n\\\\n{json.dumps(json_data, indent=2)}"
            yield from self.strategist.run(plan_prompt, stream=True)
            plan = self.strategist.run_response.content
            
            if broadcaster:
                try:
                    asyncio.create_task(broadcaster.agent_completed("strategist", self.run_id, True, {"plan": plan[:500] + "..." if len(plan) > 500 else plan}))
                except Exception as e:
                    logger.warning(f"Failed to broadcast strategist completion: {e}")
            logger.info(f"Strategist Plan:\\n{plan}")

            if cancellation_event.is_set():
                raise asyncio.CancelledError("Workflow cancelled by client request.")

            # 3. Code Generation Agent
            codegen_prompt = load_prompt(
                "services/legacy_codegen_prompt.txt",
                temp_dir=self.temp_dir,
                json_data=json.dumps(json_data, indent=2)
            )
            
            if broadcaster:
                try:
                    asyncio.create_task(broadcaster.agent_started("codegen", self.run_id))
                except Exception as e:
                    logger.warning(f"Failed to broadcast codegen start: {e}")
                    
            yield from self.code_gen_agent.run(codegen_prompt, stream=True)
            
            if broadcaster:
                try:
                    asyncio.create_task(broadcaster.agent_completed("codegen", self.run_id, True, {"status": "Code execution completed"}))
                except Exception as e:
                    logger.warning(f"Failed to broadcast codegen completion: {e}")

            if cancellation_event.is_set():
                raise asyncio.CancelledError("Workflow cancelled by client request.")

            # 4. Quality Assurance Agent
            qa_prompt = """Review the generated Excel file and code execution results. Provide constructive feedback.

REQUIREMENTS TO CHECK:
1. Excel file exists at: {}/financial_report.xlsx
2. Multiple sheets with proper data organization
3. Professional formatting with colors and styling
4. Complete data extraction from JSON
5. Executive Summary with key metrics

PROVIDE FEEDBACK ON:
- Data completeness and accuracy
- Visual presentation and formatting
- Suggestions for improvements (but do not block completion)
- Overall report quality assessment

Code Generation Results:
{}

Focus on constructive feedback rather than blocking approval. If the file exists and contains data, consider it acceptable.""".format(self.temp_dir, getattr(getattr(self.code_gen_agent, 'run_response', None), 'content', 'No code execution detected') if hasattr(self.code_gen_agent, 'run_response') and self.code_gen_agent.run_response else 'No code execution detected')
            
            if broadcaster:
                try:
                    asyncio.create_task(broadcaster.agent_started("qa", self.run_id))
                except Exception as e:
                    logger.warning(f"Failed to broadcast qa start: {e}")
                    
            yield from self.qa_agent.run(qa_prompt, stream=True)
            
            if broadcaster:
                try:
                    asyncio.create_task(broadcaster.agent_completed("qa", self.run_id, True, {"status": "Quality assurance completed"}))
                except Exception as e:
                    logger.warning(f"Failed to broadcast qa completion: {e}")
            logger.info(f"QA Agent Response:\\n{self.qa_agent.run_response.content}")

            # Enhanced file detection with multiple patterns and wait logic

            
            # Try multiple detection attempts with delays
            detection_attempts = 5
            wait_between_attempts = 2  # seconds
            
            output_files = []
            for attempt in range(detection_attempts):
                logger.info(f"File detection attempt {attempt + 1}/{detection_attempts}")
                
                # Try multiple file patterns
                search_patterns = [
                    f"{self.temp_dir}/financial_report.xlsx",
                    f"{self.temp_dir}/report.xlsx", 
                    f"{self.temp_dir}/backup_report.xlsx",
                    f"{self.temp_dir}/*.xlsx",
                    f"{self.temp_dir}/**/*.xlsx"  # Recursive search
                ]
                
                for pattern in search_patterns:
                    files = glob.glob(pattern, recursive=True)
                    if files:
                        # Filter out empty files
                        valid_files = [f for f in files if os.path.exists(f) and os.path.getsize(f) > 0]
                        if valid_files:
                            output_files = valid_files
                            logger.info(f"Found {len(valid_files)} valid Excel files: {valid_files}")
                            break
                
                if output_files:
                    break
                    
                if attempt < detection_attempts - 1:
                    logger.info(f"No files found, waiting {wait_between_attempts}s before retry...")
                    time.sleep(wait_between_attempts)
            
            if not output_files:
                # Enhanced error reporting
                logger.error(f"CRITICAL: No Excel files found after {detection_attempts} attempts")
                logger.error(f"Temp directory: {self.temp_dir}")
                logger.error(f"Directory exists: {os.path.exists(self.temp_dir)}")
                if os.path.exists(self.temp_dir):
                    try:
                        contents = os.listdir(self.temp_dir)
                        logger.error(f"Directory contents: {contents}")
                        # Log file details
                        for item in contents:
                            item_path = os.path.join(self.temp_dir, item)
                            if os.path.isfile(item_path):
                                size = os.path.getsize(item_path)
                                logger.error(f"  File: {item}, Size: {size} bytes")
                    except Exception as e:
                        logger.error(f"Could not list directory contents: {e}")
                else:
                    logger.error("Temp directory does not exist!")
                
                # Try one more time to find any files
                all_files = []
                try:
                    for root, dirs, files in os.walk(self.temp_dir):
                        for file in files:
                            all_files.append(os.path.join(root, file))
                    logger.error(f"All files in temp directory tree: {all_files}")
                except Exception as e:
                    logger.error(f"Could not walk directory tree: {e}")
                    
                raise Exception("Code Generation Agent failed to create an Excel file after multiple attempts.")

            final_excel_path = output_files[0]
            self.session_state[cache_key] = final_excel_path
            workflow_success = True
            yield RunResponse(run_id=self.run_id, content=final_excel_path)
        
        except Exception as e:
            error_message = str(e)
            logger.error(f"Workflow failed: {e}")
            raise
        finally:
            # Broadcast workflow completion
            if broadcaster:
                try:
                    results = {"success": workflow_success}
                    if workflow_success and 'final_excel_path' in locals():
                        results["output_file"] = final_excel_path
                    
                    asyncio.create_task(broadcaster.workflow_completed(
                        workflow_id=execution_id,
                        request_id=self.run_id,
                        success=workflow_success,
                        results=results,
                        error=error_message
                    ))
                except Exception as e:
                    logger.warning(f"Failed to broadcast workflow completion: {e}")
            
            # Record execution results
            execution_monitor.end_execution(
                execution_id, "workflow", self.temp_dir,
                success=workflow_success,
                details={
                    "run_id": self.run_id,
                    "data_size": len(json.dumps(json_data)),
                    "model_id": self.model_id
                },
                error_message=error_message
            )

# All agent creation functions have been moved to /app/agents/ module


async def direct_json_to_excel_async(json_data: str, file_name: str, chunk_size: int, temp_dir: str) -> Tuple[str, str, str]:
    """Async version of direct_json_to_excel for better performance."""
    # Run the synchronous function in a thread pool to make it non-blocking
    return await asyncio.to_thread(direct_json_to_excel, json_data, file_name, chunk_size, temp_dir)


def direct_json_to_excel(json_data: str, file_name: str, chunk_size: int, temp_dir: str) -> Tuple[str, str, str]:
    """
    Convert JSON data directly to Excel with automatic retry mechanism.
    Will retry up to 3 times with different approaches on each retry.
    """
    max_retries = 3
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            decoder = json.JSONDecoder()
            pos = 0
            data_objects = []
            clean_json_data = json_data.strip()
            
            # Try different parsing approaches based on retry count
            if retry_count == 0:
                # First attempt: Standard parsing
                while pos < len(clean_json_data):
                    obj, end_pos = decoder.raw_decode(clean_json_data[pos:])
                    data_objects.append(obj)
                    pos = end_pos
                    while pos < len(clean_json_data) and clean_json_data[pos].isspace():
                        pos += 1
            elif retry_count == 1:
                # Second attempt: Line-by-line parsing
                for line in clean_json_data.split('\n'):
                    if line.strip():
                        try:
                            obj = json.loads(line.strip())
                            data_objects.append(obj)
                        except json.JSONDecodeError:
                            continue
            else:
                # Third attempt: Try with more lenient approach (wrap in array if needed)
                try:
                    data_objects = [json.loads(clean_json_data)]
                except json.JSONDecodeError:
                    try:
                        data_objects = [json.loads(f"[{clean_json_data}]")]
                    except:
                        # Last resort: Try to extract any valid JSON objects
                        import re
                        json_pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}'
                        matches = re.findall(json_pattern, clean_json_data)
                        for match in matches:
                            try:
                                obj = json.loads(match)
                                data_objects.append(obj)
                            except:
                                continue
            
            if not data_objects:
                raise ValueError("No valid JSON objects found in the input data")
            
            data = data_objects[0] if len(data_objects) == 1 else data_objects

            file_id = str(uuid.uuid4())
            safe_filename = "".join(c for c in file_name if c.isalnum() or c in (' ', '-', '_')).strip()
            xlsx_filename = f"{safe_filename}_direct.xlsx"
            file_path = os.path.join(temp_dir, f"{file_id}_{xlsx_filename}")

            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                sheets_created = False
                
                if isinstance(data, list):
                    if len(data) > 0:  # Only process if list is not empty
                        try:
                            if len(data) > chunk_size:
                                for i in range(0, len(data), chunk_size):
                                    chunk_data = data[i:i + chunk_size]
                                    if chunk_data:  # Ensure chunk is not empty
                                        try:
                                            df = pd.json_normalize(chunk_data)
                                            if not df.empty:  # Only create sheet if DataFrame has data
                                                df.to_excel(writer, sheet_name=f'Data_Chunk_{i//chunk_size + 1}', index=False)
                                                sheets_created = True
                                        except Exception as e:
                                            logger.warning(f"Failed to normalize chunk {i}: {e}")
                                            # Create a simple representation of the chunk
                                            df = pd.DataFrame([{"chunk_data": str(chunk_data)}])
                                            df.to_excel(writer, sheet_name=f'Chunk_{i//chunk_size + 1}_Raw', index=False)
                                            sheets_created = True
                            else:
                                try:
                                    df = pd.json_normalize(data)
                                    if not df.empty:  # Only create sheet if DataFrame has data
                                        df.to_excel(writer, sheet_name='Data', index=False)
                                        sheets_created = True
                                except Exception as e:
                                    logger.warning(f"Failed to normalize list data: {e}")
                                    # Create a simple representation of the data
                                    df = pd.DataFrame([{"raw_data": str(item)} for item in data])
                                    df.to_excel(writer, sheet_name='Raw_Data', index=False)
                                    sheets_created = True
                        except Exception as e:
                            logger.warning(f"Failed to process list data: {e}")
                            # Last resort: create basic representation
                            df = pd.DataFrame([{"list_item": str(item), "index": i} for i, item in enumerate(data)])
                            df.to_excel(writer, sheet_name='List_Items', index=False)
                            sheets_created = True
                
                elif isinstance(data, dict):
                    # Handle dictionary data
                    if data:  # Only process if dict is not empty
                        for key, value in data.items():
                            if isinstance(value, list) and value:  # Only process non-empty lists
                                df = pd.json_normalize(value)
                                if not df.empty:
                                    safe_sheet_name = str(key)[:31].replace('/', '_').replace('\\', '_')
                                    df.to_excel(writer, sheet_name=safe_sheet_name, index=False)
                                    sheets_created = True
                        
                        # If no list values were found, create a sheet with the dict itself
                        if not sheets_created:
                            df = pd.json_normalize([data])
                            if not df.empty:
                                df.to_excel(writer, sheet_name='Data', index=False)
                                sheets_created = True
                
                else:
                    # Handle primitive data types
                    df = pd.DataFrame([{'value': data}])
                    df.to_excel(writer, sheet_name='Data', index=False)
                    sheets_created = True
                
                # Ensure at least one sheet exists
                if not sheets_created:
                    # Create a minimal sheet with error information
                    df = pd.DataFrame([{'error': 'No valid data found', 'original_data_type': str(type(data))}])
                    df.to_excel(writer, sheet_name='Error', index=False)

            return file_id, xlsx_filename, file_path
            
        except Exception as e:
            retry_count += 1
            last_error = str(e)
            error_details = traceback.format_exc()
            logger.error(f"Direct conversion failed (attempt {retry_count}/{max_retries}): {e}\n{error_details}")
            
            if retry_count >= max_retries:
                logger.error(f"All {max_retries} direct conversion attempts failed. Giving up.")
                raise
            
            # Wait briefly before retrying (with increasing delay)
            time.sleep(retry_count)
            logger.info(f"Retrying direct conversion (attempt {retry_count+1}/{max_retries})...")





def extract_currencies_from_json(json_data: str) -> List[str]:
    """Extract unique currency codes from the JSON data."""
    currencies = set()
    
    try:
        data = json.loads(json_data)
        
        # Recursive function to find currency fields
        def find_currencies(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if "currency" in key.lower() and isinstance(value, str) and len(value) == 3:
                        if value != "USD":  # We need to convert non-USD currencies
                            currencies.add(value)
                    find_currencies(value, f"{path}.{key}")
            elif isinstance(obj, list):
                for item in obj:
                    find_currencies(item, path)
        
        find_currencies(data)
    except Exception as e:
        logger.warning(f"Failed to extract currencies: {e}")
    
    return list(currencies)





def find_newest_file(directory: str, files_before: set) -> Optional[str]:
    """Enhanced file detection with multiple strategies"""
    import shutil
    
    logger.info(f"Starting enhanced file detection in: {directory}")
    
    # Strategy 1: Direct path check for common filenames
    direct_paths = [
        os.path.join(directory, 'financial_report.xlsx'),
        os.path.join(directory, 'report.xlsx'),
        os.path.join(directory, 'backup_report.xlsx'),
        os.path.join(directory, 'backup_financial_report.xlsx')
    ]
    
    for path in direct_paths:
        if os.path.exists(path) and path not in files_before:
            logger.info(f"Found file via direct path: {path}")
            return path
    
    # Strategy 2: Pattern matching with multiple attempts
    patterns = [
        os.path.join(directory, "*.xlsx"),
        os.path.join(directory, "**", "*.xlsx"),  # Recursive search
    ]
    
    max_attempts = 5
    attempt_delay = 0.5  # Start with 500ms
    
    for attempt in range(max_attempts):
        if attempt > 0:
            time.sleep(attempt_delay)
            attempt_delay *= 1.5  # Exponential backoff
        
        files_after = set()
        for pattern in patterns:
            files_after.update(glob.glob(pattern, recursive=True))
        
        new_files = files_after - files_before
        if new_files:
            logger.info(f"File detection succeeded on attempt {attempt + 1}")
            break
        
        logger.info(f"File detection attempt {attempt + 1}/{max_attempts} - no new files yet")
    
    # Strategy 3: Check common mistake locations and recover files
    if not new_files:
        logger.info("No files found in target directory, checking mistake locations...")
        
        mistake_locations = [
            os.getcwd(),  # Current working directory
            os.path.dirname(directory),  # Parent directory
            tempfile.gettempdir(),  # System temp
            os.path.expanduser("~"),  # Home directory
            "/tmp" if os.path.exists("/tmp") else None,  # Unix temp
        ]
        
        # Remove None values and duplicates
        mistake_locations = list(set(filter(None, mistake_locations)))
        
        for location in mistake_locations:
            if location != directory and os.path.exists(location):
                logger.info(f"Checking mistake location: {location}")
                
                # Look for Excel files created recently (last 10 minutes)
                cutoff_time = time.time() - 600  # 10 minutes ago
                
                try:
                    files = glob.glob(os.path.join(location, "*.xlsx"))
                    for file in files:
                        if (file not in files_before and 
                            os.path.exists(file) and 
                            os.path.getmtime(file) > cutoff_time):
                            
                            # Move to correct location
                            dest = os.path.join(directory, os.path.basename(file))
                            try:
                                # Ensure destination doesn't exist
                                if os.path.exists(dest):
                                    base, ext = os.path.splitext(dest)
                                    counter = 1
                                    while os.path.exists(f"{base}_{counter}{ext}"):
                                        counter += 1
                                    dest = f"{base}_{counter}{ext}"
                                
                                shutil.move(file, dest)
                                logger.info(f"Recovered file from {location}: {file} -> {dest}")
                                
                                # Update files_after to include recovered file
                                files_after.add(dest)
                                new_files = files_after - files_before
                                break
                                
                            except Exception as e:
                                logger.error(f"Failed to recover file {file}: {e}")
                                
                except Exception as e:
                    logger.warning(f"Could not check location {location}: {e}")
                
                if new_files:
                    break
    
    # Strategy 4: Final verification and selection
    if not new_files:
        logger.warning(f"No new Excel files found after all strategies")
        return None
    
    logger.info(f"=== FILE DETECTION DEBUG ===")
    logger.info(f"Directory being searched: {directory}")
    logger.info(f"Directory exists: {os.path.exists(directory)}")
    logger.info(f"Search patterns: {patterns}")
    logger.info(f"Files before: {len(files_before)} - {list(files_before)}")
    logger.info(f"Files after: {len(files_after)} - {list(files_after)}")
    
    # Also check for all files in the directory for debugging
    all_files = []
    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                full_path = os.path.join(root, file)
                all_files.append(full_path)
        logger.info(f"ALL files in directory tree: {all_files}")
    except Exception as e:
        logger.warning(f"Could not walk directory {directory}: {e}")
    
    # ALSO check current working directory as fallback
    cwd = os.getcwd()
    logger.info(f"Current working directory: {cwd}")
    if cwd != directory:
        logger.info(f"Checking for Excel files in CWD as fallback...")
        cwd_xlsx_files = glob.glob(os.path.join(cwd, "*.xlsx"))
        logger.info(f"Excel files found in CWD: {cwd_xlsx_files}")
        
        # If no files in temp dir but files in CWD, log this issue
        if not files_after and cwd_xlsx_files:
            logger.error(f"ERROR: Agent created files in wrong location! Files in CWD: {cwd_xlsx_files}")
            logger.error(f"These should have been created in: {directory}")
    
    # Re-calculate new_files after all debug logging
    new_files = files_after - files_before
    logger.info(f"New files: {list(new_files)}")
    logger.info(f"=== END FILE DETECTION DEBUG ===")
    
    if not new_files:
        logger.warning(f"No new Excel files found in {directory} after {max_attempts} attempts")
        return None
    
    # Wait a bit more to ensure file is fully written before checking modification time
    time.sleep(0.2)
    
    try:
        newest_file = max(new_files, key=os.path.getmtime)
        # Verify file is readable and has non-zero size
        if os.path.getsize(newest_file) > 0:
            logger.info(f"Newest file selected: {newest_file} (size: {os.path.getsize(newest_file)} bytes)")
            return newest_file
        else:
            logger.warning(f"Newest file {newest_file} has zero size")
            return None
    except Exception as e:
        logger.error(f"Error accessing newest file: {e}")
        return None


# Cleanup function to manage the agent pool and storage
def cleanup_agent_pool():
    """Remove agents from the pool to free up memory."""
    global AGENT_POOL
    logger.info(f"Cleaning up agent pool with {len(AGENT_POOL)} agents")
    AGENT_POOL.clear()

def refresh_agent_pool_for_model_change():
    """Refresh agent pool when model configuration changes.
    
    This ensures agents use the new model configuration without requiring
    a complete application restart.
    """
    old_pool_size = len(AGENT_POOL)
    cleanup_agent_pool()
    logger.info(f"Agent pool refreshed due to model configuration change (removed {old_pool_size} agents)")

def get_agent_pool_status() -> Dict[str, Any]:
    """Get current status of the agent pool."""
    return {
        "pool_size": len(AGENT_POOL),
        "max_pool_size": MAX_POOL_SIZE,
        "agents": list(AGENT_POOL.keys()),
        "current_agno_model": get_agno_model()
    }


def cleanup_storage_files():
    """Clean up old storage files to prevent disk space issues."""
    import glob
    import time
    storage_dir = Path("storage")
    if storage_dir.exists():
        # Remove storage files older than 1 hour
        cutoff_time = time.time() - 3600  # 1 hour
        for db_file in glob.glob(str(storage_dir / "agents_*.db")):
            if os.path.getmtime(db_file) < cutoff_time:
                try:
                    os.remove(db_file)
                    logger.debug(f"Cleaned up old storage file: {db_file}")
                except OSError as e:
                    logger.warning(f"Failed to remove old storage file {db_file}: {e}")


# Export main functions for use in main.py
__all__ = [
    'FinancialReportWorkflow',
    'direct_json_to_excel_async', 
    'direct_json_to_excel',
    'cleanup_agent_pool',
    'get_agent_pool_status',
    'ModelService',
    'GenerationService', 
    'TokenService',
    'model_service',
    'generation_service',
    'token_service'
]