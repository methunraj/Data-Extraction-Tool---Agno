"""
Minimal FastAPI API layer for IntelliExtract.
Direct workflow usage with no custom abstractions - let Agno handle complexity.
"""
import os
import uuid
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional

# Load environment variables
from dotenv import load_dotenv
# Load from parent directory .env file
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import our Agno-native workflows
from .workflows.data_transform import DataTransformWorkflow
from .workflows.prompt_engineer import PromptEngineerWorkflow, ExtractionSchema

# Import routers - commented out due to legacy code conflicts
# from .routers import models, generation, extraction, cache, agents, monitoring


# Pydantic models for API requests
class ConfigRequest(BaseModel):
    requirements: str
    sample_documents: Optional[List[str]] = None


class ExtractionRequest(BaseModel):
    request: str
    session_id: Optional[str] = None


# Initialize FastAPI app
app = FastAPI(
    title="IntelliExtract API",
    description="AI-powered data extraction using Agno workflows",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers - commented out due to legacy code conflicts
# app.include_router(models.router)
# app.include_router(generation.router)
# app.include_router(extraction.router)
# app.include_router(cache.router)
# app.include_router(agents.router)
# app.include_router(monitoring.router)

# Global settings
TEMP_DIR = os.environ.get("AGENT_TEMP_DIR", "/tmp/intelliextract")
Path(TEMP_DIR).mkdir(parents=True, exist_ok=True)


@app.post("/api/generate-config", response_model=Dict[str, Any])
async def generate_config(request: ConfigRequest):
    """
    Generate extraction configuration using PromptEngineerWorkflow.
    Direct workflow usage - no custom abstractions.
    """
    try:
        # Initialize workflow (lightweight - ~3μs in Agno)
        prompt_engineer = PromptEngineerWorkflow()
        
        # Single agent call returns structured data automatically
        if request.sample_documents:
            config: ExtractionSchema = prompt_engineer.run_with_examples(
                request.requirements,
                request.sample_documents
            )
        else:
            config: ExtractionSchema = prompt_engineer.run(request.requirements)
        
        # Return Pydantic model as dict - no custom serialization needed
        return config.model_dump()
        
    except Exception as e:
        # Minimal error handling - let FastAPI handle HTTP errors
        raise HTTPException(status_code=500, detail=f"Configuration generation failed: {str(e)}")


@app.post("/api/generate-unified-config", response_model=Dict[str, Any])
async def generate_unified_config(request: Dict[str, Any]):
    """
    Generate unified extraction configuration (frontend-compatible endpoint).
    Maps frontend parameters to PromptEngineerWorkflow.
    """
    try:
        # Initialize workflow
        prompt_engineer = PromptEngineerWorkflow()
        
        # Map frontend parameters to backend format
        requirements = request.get("user_intent", "")
        sample_documents = request.get("sample_data", "").split("\n") if request.get("sample_data") else None
        
        if not requirements:
            raise HTTPException(status_code=400, detail="user_intent is required")
        
        # Generate configuration
        if sample_documents and any(doc.strip() for doc in sample_documents):
            config: ExtractionSchema = prompt_engineer.run_with_examples(
                requirements,
                [doc.strip() for doc in sample_documents if doc.strip()]
            )
        else:
            config: ExtractionSchema = prompt_engineer.run(requirements)
        
        # Convert to frontend format
        result = config.model_dump()
        
        # Add additional fields expected by frontend
        # Convert Example objects to dicts if needed
        examples = result.get("examples", [])
        if examples and hasattr(examples[0], 'model_dump'):
            examples = [ex.model_dump() for ex in examples]
        
        return {
            "schema": result.get("json_schema", "{}"),
            "system_prompt": result.get("system_prompt", ""),
            "user_prompt_template": result.get("user_prompt_template", ""),
            "examples": examples,
            "reasoning": "Configuration generated successfully using Agno PromptEngineerWorkflow",
            "cost": 0.001,  # Placeholder cost
            "tokens_used": 1000  # Placeholder token count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unified configuration generation failed: {str(e)}")


@app.post("/api/refine-config", response_model=Dict[str, Any])
async def refine_config(
    current_config: Dict[str, Any],
    feedback: str
):
    """
    Refine existing configuration based on feedback.
    """
    try:
        prompt_engineer = PromptEngineerWorkflow()
        
        # Convert dict back to Pydantic model
        config_obj = ExtractionSchema(**current_config)
        
        # Refine configuration
        refined_config = prompt_engineer.refine_configuration(config_obj, feedback)
        return refined_config.model_dump()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Configuration refinement failed: {str(e)}")


@app.post("/api/extract-data")
async def extract_data(
    request: ExtractionRequest,
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Extract data and generate Excel report with streaming responses.
    Uses Agno's native streaming - Iterator[RunResponse] -> SSE.
    """
    
    # Create unique session directory
    session_id = request.session_id or str(uuid.uuid4())
    session_dir = os.path.join(TEMP_DIR, f"session_{session_id}")
    Path(session_dir).mkdir(parents=True, exist_ok=True)
    
    # Save uploaded files to session directory
    saved_files = []
    try:
        for file in files:
            file_path = os.path.join(session_dir, file.filename or f"file_{uuid.uuid4().hex[:8]}")
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            saved_files.append({
                "name": file.filename,
                "path": file_path,
                "type": file.content_type,
                "size": len(content)
            })
        
        # Initialize workflow with session directory
        data_transform = DataTransformWorkflow(working_dir=session_dir)
        
        # Stream workflow responses using Server-Sent Events
        def stream_responses():
            """
            Stream Agno workflow responses as SSE.
            Direct Iterator[RunResponse] -> SSE conversion.
            """
            try:
                # Run workflow with streaming - pure Python iterator
                for response in data_transform.run(request.request, saved_files):
                    # Convert RunResponse to SSE format
                    if hasattr(response, 'content') and response.content:
                        # SSE format: data: {content}\n\n
                        yield f"data: {response.content}\n\n"
                
                # Send completion event
                yield f"data: {{\"status\": \"completed\", \"session_id\": \"{session_id}\"}}\n\n"
                
            except Exception as e:
                # Stream error as SSE
                yield f"data: {{\"error\": \"Workflow failed: {str(e)}\"}}\n\n"
        
        # Schedule cleanup as background task
        if background_tasks:
            background_tasks.add_task(cleanup_session, session_dir, delay_seconds=300)  # 5 minutes
        
        # Return streaming response
        return StreamingResponse(
            stream_responses(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Session-ID": session_id
            }
        )
        
    except Exception as e:
        # Cleanup on immediate failure
        cleanup_session_sync(session_dir)
        raise HTTPException(status_code=500, detail=f"Data extraction failed: {str(e)}")


@app.get("/api/download-report/{session_id}")
async def download_report(session_id: str, filename: Optional[str] = None):
    """
    Download generated Excel report from session directory.
    """
    session_dir = os.path.join(TEMP_DIR, f"session_{session_id}")
    
    # Look for Excel files in session directory
    excel_files = list(Path(session_dir).glob("*.xlsx"))
    
    if not excel_files:
        raise HTTPException(status_code=404, detail="No Excel report found for this session")
    
    # Use specified filename or first found Excel file
    if filename:
        report_path = os.path.join(session_dir, filename)
        if not os.path.exists(report_path):
            raise HTTPException(status_code=404, detail=f"File {filename} not found")
    else:
        report_path = str(excel_files[0])
    
    # Return file response
    return FileResponse(
        path=report_path,
        filename=filename or "extracted_data.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.get("/api/sessions/{session_id}/files")
async def list_session_files(session_id: str):
    """
    List files in a session directory.
    """
    session_dir = os.path.join(TEMP_DIR, f"session_{session_id}")
    
    if not os.path.exists(session_dir):
        raise HTTPException(status_code=404, detail="Session not found")
    
    files = []
    for file_path in Path(session_dir).iterdir():
        if file_path.is_file():
            files.append({
                "name": file_path.name,
                "size": file_path.stat().st_size,
                "type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if file_path.suffix == ".xlsx" else "unknown"
            })
    
    return {"session_id": session_id, "files": files}


@app.delete("/api/sessions/{session_id}")
async def cleanup_session_endpoint(session_id: str, background_tasks: BackgroundTasks):
    """
    Manually cleanup a session directory.
    """
    session_dir = os.path.join(TEMP_DIR, f"session_{session_id}")
    
    if not os.path.exists(session_dir):
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Schedule cleanup as background task
    background_tasks.add_task(cleanup_session_sync, session_dir)
    
    return {"message": f"Session {session_id} cleanup scheduled"}


@app.get("/api/models")
async def get_models():
    """
    Get available models from models.json configuration.
    """
    try:
        # Import here to avoid circular dependency
        from .services.model_service import get_model_service
        
        model_service = get_model_service()
        models = model_service.get_all_models()
        
        # Convert to frontend-compatible format
        formatted_models = []
        for model in models:
            formatted_models.append({
                "id": model["id"],
                "displayName": model["displayName"],
                "description": model["description"],
                "provider": model["provider"],
                "supportedIn": model["supportedIn"],
                "capabilities": model.get("capabilities", {}),
                "limits": model.get("limits", {}),
                "pricing": model.get("pricing", {}),
                "status": model.get("status", "stable")
            })
        
        return {"models": formatted_models}
    except Exception as e:
        # Fallback to minimal hardcoded models if service fails
        print(f"Error loading models from service: {e}")
        return {
            "models": [
                {
                    "id": "gemini-2.0-flash-001",
                    "displayName": "Gemini 2.0 Flash",
                    "description": "Fast model for extraction",
                    "provider": "googleAI",
                    "supportedIn": ["extraction", "generation", "agno"],
                    "capabilities": {"vision": True},
                    "limits": {"maxInputTokens": 1000000},
                    "pricing": {"input": 0.0001, "output": 0.0004},
                    "status": "stable"
                }
            ]
        }


@app.get("/health")
async def health():
    """
    Health check endpoint.
    """
    return {
        "status": "healthy",
        "framework": "agno",
        "api_version": "2.0.0",
        "temp_dir": TEMP_DIR,
        "temp_dir_exists": os.path.exists(TEMP_DIR)
    }


@app.get("/")
async def root():
    """
    Root endpoint.
    """
    return {
        "message": "IntelliExtract API - AI-powered data extraction using Agno workflows",
        "docs": "/docs",
        "health": "/health"
    }


# Utility functions for cleanup
async def cleanup_session(session_dir: str, delay_seconds: int = 0):
    """
    Async cleanup function for background tasks.
    """
    if delay_seconds > 0:
        await asyncio.sleep(delay_seconds)
    
    cleanup_session_sync(session_dir)


def cleanup_session_sync(session_dir: str):
    """
    Synchronous cleanup function.
    """
    try:
        import shutil
        if os.path.exists(session_dir):
            shutil.rmtree(session_dir)
            print(f"Cleaned up session directory: {session_dir}")
    except Exception as e:
        print(f"Failed to cleanup session directory {session_dir}: {e}")


# App startup event
@app.on_event("startup")
async def startup_event():
    """
    Application startup - ensure temp directory exists.
    """
    Path(TEMP_DIR).mkdir(parents=True, exist_ok=True)
    print(f"IntelliExtract API started - Temp directory: {TEMP_DIR}")


# App shutdown event  
@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown - optional cleanup.
    """
    print("IntelliExtract API shutting down")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )