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
from fastapi import Request

# Set Matplotlib backend to a non-GUI backend to avoid threading issues
import matplotlib
matplotlib.use('Agg')  # Must be before any other matplotlib imports

from agno.agent import Agent, RunResponse
from agno.workflow import Workflow
from agno.models.google import Gemini
from agno.storage.sqlite import SqliteStorage
from agno.tools.python import PythonTools
from .core.config import settings
from .services.model_service import get_model_service
from .agents import create_agent

logger = logging.getLogger(__name__)

# Get model service for dynamic model selection
model_service = get_model_service()

def get_agno_model() -> str:
    """Get the configured model for Agno processing."""
    # Try to get a model that supports 'agno' purpose
    agno_models = model_service.get_models_for_purpose("agno")
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
    
    # Fallback to default if no agno models found
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

def get_agent_by_key(agent_type: str, **kwargs) -> Agent:
    """Get or create an agent from the pool based on type and current model configuration.
    
    Args:
        agent_type: Type of agent ('search', 'strategist', 'qa', 'codegen')
        **kwargs: Additional arguments for agent creation (e.g., temp_dir for codegen)
    
    Returns:
        Agent instance from pool or newly created
    """
    # Get current model to include in cache key
    current_model = get_agno_model()
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
    agent = create_agent(agent_type, **kwargs)
    
    # Add to pool
    AGENT_POOL[cache_key] = agent
    logger.info(f"Created and cached {agent_type} agent for model {current_model} (pool size: {len(AGENT_POOL)})")
    
    return agent


# Agent creation functions removed - now using agent classes from .agents module


class FinancialReportWorkflow(Workflow):
    """A stateful, deterministic workflow for generating financial reports."""

    def __init__(self, temp_dir: str):
        super().__init__()
        self.temp_dir = temp_dir
        # Use pooled agents for better performance and dynamic model selection
        self.strategist = get_agent_by_key("strategist")
        self.search_agent = get_agent_by_key("search")
        self.code_gen_agent = get_agent_by_key("codegen", temp_dir=temp_dir)
        self.qa_agent = get_agent_by_key("qa")

    def run_workflow(self, json_data: Dict[str, Any], cancellation_event: asyncio.Event) -> Iterator[RunResponse]:
        """Executes the financial report generation workflow."""
        # Use a unique key for caching based on the JSON data content
        cache_key = json.dumps(json_data, sort_keys=True)
        if self.session_state.get(cache_key):
            logger.info(f"Cache hit for the report.")
            yield RunResponse(
                run_id=self.run_id, content=self.session_state.get(cache_key)
            )
            return

        # 1. Strategist Agent
        plan_prompt = f"Create a detailed execution plan to convert the following JSON data into a comprehensive Excel report:\n\n{json.dumps(json_data, indent=2)}"
        yield from self.strategist.run(plan_prompt, stream=True)
        plan = self.strategist.run_response.content
        logger.info(f"Strategist Plan:\n{plan}")

        if cancellation_event.is_set():
            raise asyncio.CancelledError("Workflow cancelled by client request.")

        # 2. Search Agent
        currencies = extract_currencies_from_json(json_data)
        if currencies:
            search_prompt = f"Get the current USD exchange rates for the following currencies: {', '.join(currencies)}"
            yield from self.search_agent.run(search_prompt, stream=True)
            logger.info(f"Search Agent Response:\n{self.search_agent.run_response.content}")

        if cancellation_event.is_set():
            raise asyncio.CancelledError("Workflow cancelled by client request.")

        # 3. Code Generation Agent
        codegen_prompt = f"Based on the following plan, and the provided JSON data, generate the python code to create the excel report and EXECUTE it immediately.\n\nIMPORTANT: You must RUN the Python code to actually create the Excel file - don't just show the code!\n\nPlan:\n{plan}\n\nJSON Data:\n{json.dumps(json_data, indent=2)}"
        yield from self.code_gen_agent.run(codegen_prompt, stream=True)

        if cancellation_event.is_set():
            raise asyncio.CancelledError("Workflow cancelled by client request.")

        # 4. Quality Assurance Agent
        qa_prompt = f"Review the following code and plan to ensure the generated report meets all requirements. Code:\n{self.code_gen_agent.run_response.content}"
        yield from self.qa_agent.run(qa_prompt, stream=True)
        logger.info(f"QA Agent Response:\n{self.qa_agent.run_response.content}")

        # Finalize and cache
        output_files = glob.glob(f"{self.temp_dir}/*.xlsx")
        if not output_files:
            raise Exception("Code Generation Agent failed to create an Excel file.")

        final_excel_path = output_files[0]
        self.session_state[cache_key] = final_excel_path
        yield RunResponse(run_id=self.run_id, content=final_excel_path)

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


async def convert_with_agno_async(fastapi_request, json_data: str, file_name: str, description: str, temp_dir: str, user_id: str = None, session_id: str = None) -> tuple[str, str]:
    """Async version of convert_with_agno for better performance."""

    cancelled = asyncio.Event()

    async def check_disconnection():
        while not cancelled.is_set():
            if await fastapi_request.is_disconnected():
                logger.warning("Client disconnected, setting cancellation event.")
                cancelled.set()
                break
            await asyncio.sleep(0.1) # Check every 100ms

    # Start a background task to check for disconnection
    disconnection_checker = asyncio.create_task(check_disconnection())

    loop = asyncio.get_event_loop()
    try:
        # Run the synchronous function in a thread pool
        result = await loop.run_in_executor(
            None,  # Default executor
            convert_with_agno,
            cancelled, # Pass cancellation event
            json_data,
            file_name,
            description,
            temp_dir,
            user_id,
            session_id
        )
        return result
    finally:
        # Stop the disconnection checker
        if not cancelled.is_set():
            cancelled.set() # Ensure the checker loop terminates
        await disconnection_checker # Wait for the checker to finish


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


def convert_with_agno(cancelled: asyncio.Event, json_data: str, file_name: str, description: str, temp_dir: str, user_id: str = None, session_id: str = None) -> tuple[str, str]:
    """
    Convert JSON data to Excel using a two-agent approach:
    1. Search agent to get exchange rates
    2. Python agent to generate Excel with the rates
    """
    import uuid
    
    # Get debug setting from configuration
    debug_enabled = settings.AGNO_DEBUG
    
    # Generate session IDs if not provided
    if not user_id:
        user_id = f"user_{uuid.uuid4().hex[:8]}"
    if not session_id:
        session_id = f"session_{uuid.uuid4().hex[:8]}"
    
    # Validate input
    if not json_data or not json_data.strip():
        raise ValueError("Empty JSON data provided - cannot process")
    
    max_retries = 2
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            # Step 1: Extract currencies from JSON data
            currencies_to_convert = extract_currencies_from_json(json_data)
            exchange_rates = {}
            
            # Step 2: Use search agent to get exchange rates if needed
            if currencies_to_convert:
                logger.info(f"Currencies found in data: {currencies_to_convert}")
                search_agent = create_search_agent()
                
                # Create search prompt
                currency_list = ", ".join(currencies_to_convert)
                search_prompt = f"""
                I need the current exchange rates for the following currencies to USD:
                {currency_list}
                
                Please provide the exchange rates in a clear format.
                For example: 1 EUR = X.XX USD
                """
                
                logger.info("Using search agent to get exchange rates...")
                search_response = search_agent.run(search_prompt, stream=False)
                
                if hasattr(search_response, 'content') and search_response.content:
                    logger.info(f"Exchange rates retrieved: {search_response.content[:200]}...")
                    
                    # Parse exchange rates from response (basic parsing)
                    # This is a simple parser - could be improved with regex
                    for line in search_response.content.split('\n'):
                        for currency in currencies_to_convert:
                            if currency in line and "USD" in line:
                                try:
                                    # Extract rate from patterns like "1 EUR = 1.0885 USD"
                                    parts = line.split('=')
                                    if len(parts) == 2:
                                        rate_str = parts[1].strip().replace('USD', '').strip()
                                        rate = float(rate_str)
                                        exchange_rates[currency] = rate
                                        logger.info(f"Parsed rate: 1 {currency} = {rate} USD")
                                except:
                                    pass
            
            # Step 3: Use Python agent to generate Excel with exchange rates
            python_agent = create_code_gen_agent(temp_dir, exchange_rates)
            
            # Create the prompt for Excel generation
            json_preview = json_data[:200] + "..." if len(json_data) > 200 else json_data
            
            prompt = f"""
            Create an Excel report from this financial data. Follow your instructions exactly.
            
            Base filename: {file_name}
            Data source: {description}
            
            REMEMBER: 
            1. Change directory to {temp_dir} FIRST in your script
            2. The currency conversion rates have been provided in your instructions
            3. Create columns for both original currency AND USD values using the provided rates
            4. Print the absolute file path when done
            5. Keep the analysis simple but include currency conversion
            6. Use openpyxl library for Excel creation
            
            **WORKING DIRECTORY:** {temp_dir}
            **IMPORTANT:** All files must be created in the working directory above. Use relative paths only.
            
            JSON Data:
            {json_data}
            """
            
            # Log clean debug info
            if debug_enabled:
                logger.info(f"🤖 AI PROMPT SUMMARY:")
                logger.info(f"   📁 Working Directory: {temp_dir}")
                logger.info(f"   📄 File Name: {file_name}")
                logger.info(f"   📝 Description: {description}")
                logger.info(f"   📊 JSON Data Size: {len(json_data)} characters")
                logger.info(f"   🔍 JSON Preview: {json_preview}")
                logger.info(f"   💱 Exchange Rates: {exchange_rates}")
                logger.info(f"   🎯 Task: Financial Excel report with currency conversion")
            
            # Execute Python agent
            logger.info(f"Starting Python agent processing (attempt {retry_count + 1}/{max_retries})...")
            


            # Since python_agent.run is blocking, we can't easily interrupt it.
            # The best we can do is check for cancellation *before* this long-running call.
            if cancelled.is_set():
                logger.warning("Cancellation detected before starting agent run.")
                raise asyncio.CancelledError("Processing cancelled before agent execution")

            response = python_agent.run(
                prompt,
                stream=False,
                show_tool_calls=True,
                markdown=True,
                user_id=user_id,
                session_id=session_id
            )

            # And check again immediately after.
            if cancelled.is_set():
                logger.warning("Cancellation detected after agent run.")
                # Clean up any files created by the agent if necessary
                raise asyncio.CancelledError("Processing cancelled after agent execution")
            
            # Validate response
            if not hasattr(response, 'content') or not response.content:
                logger.warning("Agent returned empty response")
                raise ValueError("Agent returned empty response content")
            
            logger.info(f"Python agent completed processing successfully")
            
            # Enhanced debug logging
            if debug_enabled:
                logger.info(f"🧠 AI RESPONSE ANALYSIS:")
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    logger.info(f"   🔧 Tool Calls: {len(response.tool_calls)} executed")
                    for i, tool_call in enumerate(response.tool_calls):
                        tool_name = getattr(tool_call, 'name', 'Unknown Tool')
                        logger.info(f"   🛠️  Tool {i+1}: {tool_name}")
                
                content_preview = response.content[:300] + "..." if len(response.content) > 300 else response.content
                logger.info(f"   📄 Response Length: {len(response.content)} characters")
                logger.info(f"   📋 Response Preview: {content_preview}")
            
            # Return response
            logger.info(f"Session management: user_id={user_id}, session_id={session_id}")
            return response.content, session_id
            
        except Exception as e:
            retry_count += 1
            last_error = str(e)
            error_details = traceback.format_exc()
            error_type = type(e).__name__
            
            logger.error(f"Agno AI processing failed (attempt {retry_count}/{max_retries})")
            logger.error(f"Error type: {error_type}")
            logger.error(f"Error message: {e}")
            logger.error(f"Full traceback:\n{error_details}")
            
            if retry_count >= max_retries:
                logger.error(f"All {max_retries} attempts failed. Final error type: {error_type}")
                logger.error(f"Final error message: {last_error}")
                raise
            
            # Exponential backoff
            delay = min(retry_count * 2, 10)
            logger.info(f"Retrying conversion in {delay} seconds (attempt {retry_count+1}/{max_retries})...")
            time.sleep(delay)


def find_newest_file(directory: str, files_before: set) -> Optional[str]:
    """Find the newest Excel file in directory with improved reliability."""
    # Check both the main directory and subdirectories for Excel files
    patterns = [
        os.path.join(directory, "*.xlsx"),
        os.path.join(directory, "**", "*.xlsx"),  # Recursive search
    ]
    
    # Improved file detection with multiple attempts
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
            # Found new files, proceed
            logger.info(f"File detection succeeded on attempt {attempt + 1}")
            break
        
        logger.info(f"File detection attempt {attempt + 1}/{max_attempts} - no new files yet")
    
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