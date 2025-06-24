# app/main.py
import os
import uuid
import time
import glob
import shutil
import logging
import tempfile
import threading
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.concurrency import run_in_threadpool

from . import schemas, services
from .core.config import settings

# --- Application State and Logging ---
app_state = {}

logging.basicConfig(level=settings.LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# --- Lifespan Management (Startup and Shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles application startup and shutdown events."""
    # Startup
    app_state["TEMP_DIR"] = tempfile.mkdtemp(prefix=settings.TEMP_DIR_PREFIX)
    app_state["TEMP_FILES"] = {}
    app_state["METRICS"] = {
        'total_requests': 0, 'successful_conversions': 0, 'ai_conversions': 0,
        'direct_conversions': 0, 'failed_conversions': 0,
        'average_processing_time': 0.0
    }
    app_state["LOCK"] = threading.Lock()
    logger.info(f"Application startup complete. Temp directory: {app_state['TEMP_DIR']}")
    
    yield  # Application is now running
    
    # Shutdown
    logger.info("Application shutdown. Cleaning up temp directory...")
    # Clean up agent pool to free memory
    services.cleanup_agent_pool()
    shutil.rmtree(app_state["TEMP_DIR"])
    logger.info("Cleanup complete.")

app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# --- Utility Functions ---
def update_metrics(processing_time: float, method: str, success: bool):
    with app_state["LOCK"]:
        metrics = app_state["METRICS"]
        metrics['total_requests'] += 1
        if success:
            metrics['successful_conversions'] += 1
            if method == 'ai':
                metrics['ai_conversions'] += 1
            else:
                metrics['direct_conversions'] += 1
            
            total_time = metrics['average_processing_time'] * (metrics['successful_conversions'] - 1)
            metrics['average_processing_time'] = (total_time + processing_time) / metrics['successful_conversions']
        else:
            metrics['failed_conversions'] += 1

# --- API Endpoints ---
@app.post("/process", response_model=schemas.ProcessResponse)
async def process_json_data(fastapi_request: Request, request: schemas.ProcessRequest, background_tasks: BackgroundTasks):
    start_time = time.time()
    processing_method = "direct"  # Default method
    
    # Create a unique temp directory for THIS request to avoid conflicts
    request_id = str(uuid.uuid4())[:8]
    request_temp_dir = os.path.join(app_state["TEMP_DIR"], f"request_{request_id}")
    os.makedirs(request_temp_dir, exist_ok=True)
    
    logger.info(f"Created isolated temp directory for request: {request_temp_dir}")
    
    # Get all Excel files before processing in THIS request's directory
    files_before = set()
    patterns = [
        os.path.join(request_temp_dir, "*.xlsx"),
        os.path.join(request_temp_dir, "**", "*.xlsx"),
    ]
    for pattern in patterns:
        files_before.update(glob.glob(pattern, recursive=True))
    
    logger.info(f"Files before processing in {request_temp_dir}: {list(files_before)}")
    
    # Schedule cleanup of request directory and agents after processing with delay
    def cleanup_request_resources():
        try:
            # Use configurable delay from settings
            import time
            time.sleep(settings.CLEANUP_DELAY_SECONDS)  # Configurable delay before cleanup (default: 5 minutes)
            
            # Clean up temp directory
            if os.path.exists(request_temp_dir):
                shutil.rmtree(request_temp_dir)
                logger.info(f"Cleaned up request temp directory: {request_temp_dir}")
            
            # Note: Agents are now pooled by model and reused across requests
            # No per-request cleanup needed - agents persist for efficiency
            logger.debug(f"Agent pool maintained for reuse (size: {len(services.AGENT_POOL)})")
                
        except Exception as e:
            logger.warning(f"Failed to cleanup request resources for {request_temp_dir}: {e}")
    
    background_tasks.add_task(cleanup_request_resources)

    try:
        # --- AI Processing Logic ---
        if request.processing_mode in ["auto", "ai_only"]:
            try:
                                # Create a cancellation event that can be triggered if the client disconnects
                cancellation_event = asyncio.Event()

                async def check_disconnect():
                    while True:
                        if await fastapi_request.is_disconnected():
                            logger.warning("Client disconnected, cancelling workflow.")
                            cancellation_event.set()
                            break
                        await asyncio.sleep(0.1)

                disconnect_task = asyncio.create_task(check_disconnect())

                try:
                    workflow = services.FinancialReportWorkflow(
                        temp_dir=request_temp_dir
                    )
                    # The workflow's run method is a generator, so we need to iterate through it.
                    # We'll run it in a thread pool since the underlying agent calls are blocking.
                    final_excel_path = None
                    
                    def run_workflow_sync():
                        """Run the workflow synchronously and collect all responses"""
                        responses = []
                        try:
                            for response in workflow.run_workflow(request.json_data, cancellation_event):
                                responses.append(response)
                        except Exception as e:
                            logger.error(f"Workflow execution error: {e}")
                            raise
                        return responses
                    
                    # We await the result of the threadpool execution, which will be a list of responses
                    responses = await run_in_threadpool(run_workflow_sync)
                    for response in responses:
                        if response.content:
                            final_excel_path = response.content

                    if not final_excel_path:
                        raise Exception("Workflow did not produce a file path.")

                finally:
                    disconnect_task.cancel()

                ai_response_content = "Agentic workflow completed."
                actual_session_id = request.session_id

                logger.info(f"AI processing completed. Verifying file existence...")
                if final_excel_path and os.path.exists(final_excel_path):
                    logger.info(f"Found generated file: {final_excel_path}")
                    processing_method = "ai"
                    file_id = str(uuid.uuid4())
                    original_filename = os.path.basename(final_excel_path)

                    with app_state["LOCK"]:
                        app_state["TEMP_FILES"][file_id] = {'path': final_excel_path, 'filename': original_filename}

                    processing_time = time.time() - start_time
                    update_metrics(processing_time, processing_method, True)

                    return schemas.ProcessResponse(
                        success=True, file_id=file_id, file_name=original_filename,
                        download_url=f"/download/{file_id}", ai_analysis=ai_response_content,
                        processing_method=processing_method, processing_time=processing_time,
                        data_size=len(request.json_data),
                        user_id=request.user_id or f"user_{request_id}",
                        session_id=actual_session_id
                    )

                logger.warning(f"AI processing completed but no file was found. Falling back to direct conversion.")
                if request.processing_mode == "ai_only":
                    raise HTTPException(status_code=500, detail="AI processing was requested, but no file was generated.")

            except asyncio.CancelledError:
                logger.warning("AI processing was cancelled by the user.")
                # Do not fall back, just raise a specific error or return a message
                raise HTTPException(status_code=499, detail="AI processing cancelled by client")
            except Exception as e:
                logger.warning(f"AI processing failed: {e}. Falling back to direct conversion.")
                if request.processing_mode == "ai_only":
                    raise HTTPException(status_code=500, detail=f"AI-only processing failed: {e}")

        # --- Direct Conversion (Fallback or direct_only mode) ---
        logger.info("Using direct conversion...")
        # Use async version for better performance with isolated temp directory
        file_id, xlsx_filename, file_path = await services.direct_json_to_excel_async(
            request.json_data, request.file_name, request.chunk_size, request_temp_dir
        )
        
        with app_state["LOCK"]:
            app_state["TEMP_FILES"][file_id] = {'path': file_path, 'filename': xlsx_filename}

        processing_time = time.time() - start_time
        update_metrics(processing_time, processing_method, True)

        return schemas.ProcessResponse(
            success=True, file_id=file_id, file_name=xlsx_filename,
            download_url=f"/download/{file_id}", processing_method=processing_method,
            processing_time=processing_time, data_size=len(request.json_data),
            user_id=request.user_id or f"user_{request_id}",  # Return user_id for consistency
            session_id=request.session_id or f"session_{request_id}"  # Return session_id for direct conversions
        )

    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        update_metrics(time.time() - start_time, processing_method, False)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


@app.get("/download/{file_id}")
async def download_file(file_id: str):
    with app_state["LOCK"]:
        file_info = app_state["TEMP_FILES"].get(file_id)
    
    if not file_info or not os.path.exists(file_info['path']):
        raise HTTPException(status_code=404, detail="File not found or has expired.")
        
    return FileResponse(
        path=file_info['path'],
        filename=file_info['filename'],
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@app.get("/metrics", response_model=schemas.SystemMetrics)
async def get_system_metrics():
    with app_state["LOCK"]:
        metrics = app_state["METRICS"].copy()
        active_files = len(app_state["TEMP_FILES"])

    success_rate = (metrics['successful_conversions'] / max(metrics['total_requests'], 1)) * 100
    
    return schemas.SystemMetrics(
        total_requests=metrics['total_requests'],
        successful_conversions=metrics['successful_conversions'],
        ai_conversions=metrics['ai_conversions'],
        direct_conversions=metrics['direct_conversions'],
        failed_conversions=metrics['failed_conversions'],
        success_rate=round(success_rate, 2),
        average_processing_time=round(metrics['average_processing_time'], 2),
        active_files=active_files,
        temp_directory=app_state["TEMP_DIR"]
    )


@app.get("/")
async def root():
    return {"message": "Welcome to the IntelliExtract Agno AI API for Financial Document Processing. See /docs for more info."}


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    health_status = {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "temp_directory_exists": os.path.exists(app_state.get("TEMP_DIR", "")),
        "agent_pool_size": len(services.AGENT_POOL),
        "active_files": len(app_state.get("TEMP_FILES", {})),
    }
    
    # Check Google API key availability
    health_status["google_api_configured"] = bool(settings.GOOGLE_API_KEY)
    
    # Check temp directory is writable
    try:
        test_file = os.path.join(app_state.get("TEMP_DIR", "/tmp"), "health_check.tmp")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        health_status["temp_directory_writable"] = True
    except:
        health_status["temp_directory_writable"] = False
        health_status["status"] = "degraded"
    
    # Return appropriate status code
    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(content=health_status, status_code=status_code)