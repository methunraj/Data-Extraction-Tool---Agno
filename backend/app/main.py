"""
Minimal FastAPI API layer for IntelliExtract.
Direct workflow usage with no custom abstractions - let Agno handle complexity.
"""

import os
import uuid
import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

# Load environment variables
from dotenv import load_dotenv

# Load from parent directory .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import our Agno-native workflows
from .workflows.data_transform import DataTransformWorkflow
from .workflows.prompt_engineer import PromptEngineerWorkflow, ExtractionSchema

# Import model factory functions
from .agents.models import get_extraction_model, get_transform_model

# Import routers - commented out due to legacy code conflicts
# from .routers import models, generation, extraction, cache, agents, monitoring


# Pydantic models for API requests
class ConfigRequest(BaseModel):
    requirements: str
    sample_documents: Optional[List[str]] = None


class ExtractionRequest(BaseModel):
    request: str
    session_id: Optional[str] = None
    model_name: Optional[str] = None
    document_text: Optional[str] = None
    document_file: Optional[Dict[str, Any]] = None
    schema_definition: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None
    examples: Optional[List[Dict[str, str]]] = None


# Initialize FastAPI app
app = FastAPI(
    title="IntelliExtract API",
    description="AI-powered data extraction using Agno workflows",
    version="2.0.0",
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
                request.requirements, request.sample_documents
            )
        else:
            config: ExtractionSchema = prompt_engineer.run(request.requirements)

        # Return Pydantic model as dict - no custom serialization needed
        return config.model_dump()

    except Exception as e:
        # Minimal error handling - let FastAPI handle HTTP errors
        raise HTTPException(
            status_code=500, detail=f"Configuration generation failed: {str(e)}"
        )


@app.post("/api/generate-unified-config", response_model=Dict[str, Any])
async def generate_unified_config(request: Dict[str, Any]):
    """
    Generate unified extraction configuration (frontend-compatible endpoint).
    Maps frontend parameters to PromptEngineerWorkflow.
    """
    try:
        # Extract model_name from request
        model_name = request.get("model_name")
        print(f"[generate-unified-config] Received model_name: {model_name}")

        # Initialize workflow with the selected model
        prompt_engineer = PromptEngineerWorkflow(model_id=model_name)

        # Map frontend parameters to backend format
        requirements = request.get("user_intent", "")
        sample_documents = (
            request.get("sample_data", "").split("\n")
            if request.get("sample_data")
            else None
        )

        if not requirements:
            raise HTTPException(status_code=400, detail="user_intent is required")

        # Generate configuration
        if sample_documents and any(doc.strip() for doc in sample_documents):
            config: ExtractionSchema = prompt_engineer.run_with_examples(
                requirements, [doc.strip() for doc in sample_documents if doc.strip()]
            )
        else:
            config: ExtractionSchema = prompt_engineer.run(requirements)

        # Convert to frontend format
        result = config.model_dump()

        # Add additional fields expected by frontend
        # Convert Example objects to dicts if needed
        examples = result.get("examples", [])
        if examples and hasattr(examples[0], "model_dump"):
            examples = [ex.model_dump() for ex in examples]

        return {
            "schema": result.get("json_schema", "{}"),
            "system_prompt": result.get("system_prompt", ""),
            "user_prompt_template": result.get("user_prompt_template", ""),
            "examples": examples,
            "reasoning": "Configuration generated successfully using Agno PromptEngineerWorkflow",
            "cost": 0.001,  # Placeholder cost
            "tokens_used": 1000,  # Placeholder token count
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Unified configuration generation failed: {str(e)}"
        )


@app.post("/api/refine-config", response_model=Dict[str, Any])
async def refine_config(current_config: Dict[str, Any], feedback: str):
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
        raise HTTPException(
            status_code=500, detail=f"Configuration refinement failed: {str(e)}"
        )


@app.post("/api/extract-data")
async def extract_data_json(request: Dict[str, Any]):
    """
    Extract data endpoint that accepts JSON input (frontend-compatible).
    Uses Agno to process documents directly.
    """
    try:
        import os
        from agno.agent import Agent
        from agno.models.google import Gemini

        # Extract parameters from request
        document_text = request.get("document_text", "")
        document_file = request.get("document_file")
        schema_definition = request.get("schema_definition", "{}")
        system_prompt = request.get(
            "system_prompt", "Extract data according to the schema"
        )
        user_prompt_template = request.get("user_prompt_template", "{document_text}")
        examples = request.get("examples", [])
        model_name = request.get("model_name", "gemini-2.0-flash")
        print(f"[extract-data] Received model_name: {model_name}")
        print(f"[extract-data] Has document_text: {bool(document_text)}")
        print(f"[extract-data] Has document_file: {bool(document_file)}")
        if document_file:
            print(f"[extract-data] File mime_type: {document_file.get('mime_type')}")
            print(
                f"[extract-data] File data length: {len(document_file.get('data', ''))}"
            )

        # Handle document content
        content = document_text
        files = []

        if not content and document_file:
            # Handle PDF/image files with Agno's multimodal capabilities
            import base64
            from agno.media import File

            mime_type = document_file.get("mime_type", "application/pdf")
            file_data = document_file.get("data", "")

            # Create a temporary file for the PDF
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                # Decode base64 data and write to file
                file_bytes = base64.b64decode(file_data)
                tmp_file.write(file_bytes)
                tmp_file_path = tmp_file.name

            # Create Agno File object
            files = [File(filepath=tmp_file_path)]
            content = "Please extract data from the attached PDF document."

        # Create extraction agent with the selected model
        agent = Agent(
            name="DataExtractor",
            model=Gemini(id=model_name, api_key=os.environ.get("GOOGLE_API_KEY")),
            instructions=[system_prompt],
            markdown=False,
            show_tool_calls=False,
        )

        # Build the extraction prompt
        if files:
            # For PDF/image files, adjust the prompt
            prompt = system_prompt + "\n\n"
            prompt += user_prompt_template.replace(
                "{document_text}", "the attached PDF document"
            )
            prompt += (
                f"\n\nExtract data according to this JSON schema:\n{schema_definition}"
            )
        else:
            # For text content
            prompt = user_prompt_template.replace("{document_text}", content)
            prompt += (
                f"\n\nExtract data according to this JSON schema:\n{schema_definition}"
            )

        if examples:
            prompt += "\n\nExamples:"
            for ex in examples:
                prompt += (
                    f"\nInput: {ex.get('input', '')}\nOutput: {ex.get('output', '')}\n"
                )

        # Run extraction with files if available
        if files:
            response = agent.run(prompt, files=files)
        else:
            response = agent.run(prompt)

        # Extract the content
        extracted_json = ""
        if hasattr(response, "content"):
            extracted_json = response.content
            # Try to parse as JSON if it's a string
            if isinstance(extracted_json, str):
                try:
                    import json

                    extracted_json = json.loads(extracted_json)
                except:
                    # If it fails, keep as string
                    pass

        # Clean up temporary file if created
        if files and "tmp_file_path" in locals():
            import os

            try:
                os.unlink(tmp_file_path)
            except:
                pass

        # Return response in expected format
        return {
            "extracted_json": (
                json.dumps(extracted_json)
                if not isinstance(extracted_json, str)
                else extracted_json
            ),
            "token_usage": {
                "prompt_tokens": 1000,  # Placeholder
                "completion_tokens": 500,  # Placeholder
                "total_tokens": 1500,  # Placeholder
                "cached_tokens": 0,
                "thinking_tokens": 0,
            },
            "cost": 0.001,  # Placeholder
            "model_used": model_name,
            "cache_hit": False,
            "retry_count": 0,
            "thinking_text": None,
        }

    except Exception as e:
        import traceback

        error_detail = f"Extraction failed: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)  # Log to console
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/extract-data-old")
async def extract_data(
    request: ExtractionRequest,
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None,
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
            file_path = os.path.join(
                session_dir, file.filename or f"file_{uuid.uuid4().hex[:8]}"
            )
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            saved_files.append(
                {
                    "name": file.filename,
                    "path": file_path,
                    "type": file.content_type,
                    "size": len(content),
                }
            )

        # Initialize workflow with session directory and model
        data_transform = DataTransformWorkflow(
            working_dir=session_dir, model_id=request.model_name
        )

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
                    if hasattr(response, "content") and response.content:
                        # SSE format: data: {content}\n\n
                        yield f"data: {response.content}\n\n"

                # Send completion event
                yield f'data: {{"status": "completed", "session_id": "{session_id}"}}\n\n'

            except Exception as e:
                # Stream error as SSE
                yield f'data: {{"error": "Workflow failed: {str(e)}"}}\n\n'

        # Schedule cleanup as background task
        if background_tasks:
            background_tasks.add_task(
                cleanup_session, session_dir, delay_seconds=300
            )  # 5 minutes

        # Return streaming response
        return StreamingResponse(
            stream_responses(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Session-ID": session_id,
            },
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
        raise HTTPException(
            status_code=404, detail="No Excel report found for this session"
        )

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
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.post("/api/agno-process")
async def agno_process(request: Request, background_tasks: BackgroundTasks):
    """
    Process extracted data with Agno to generate Excel file.
    """
    try:
        # Parse request body
        body = await request.json()
        extracted_data = body.get("extractedData")
        file_name = body.get("fileName", "output.xlsx")
        model_name = body.get("model", "gemini-2.0-flash-exp")

        if not extracted_data:
            raise HTTPException(status_code=400, detail="Missing extractedData")

        # Parse extracted data if it's a string
        if isinstance(extracted_data, str):
            try:
                extracted_data = json.loads(extracted_data)
            except json.JSONDecodeError:
                # If it fails to parse, keep as string
                pass

        # Create session directory
        session_id = str(uuid.uuid4())
        session_dir = os.path.join(TEMP_DIR, f"session_{session_id}")
        os.makedirs(session_dir, exist_ok=True)

        # Save extracted data as JSON file for processing
        json_file_path = os.path.join(session_dir, "extracted_data.json")
        with open(json_file_path, "w") as f:
            json.dump(extracted_data, f, indent=2)

        # Initialize Excel generation workflow
        from .agents.excel_generator import ExcelGeneratorAgent
        excel_agent = ExcelGeneratorAgent(
            model=get_transform_model(model_id=model_name), working_dir=session_dir
        )
        print("[agno-process] Using ExcelGeneratorAgent")

        # Generate Excel file with clear, step-by-step prompt
        excel_prompt = f"""Convert the JSON data at {json_file_path} to an Excel file at {os.path.join(session_dir, file_name)}.

Follow these steps:

1. Install required packages:
   - pip_install_package pandas
   - pip_install_package openpyxl

2. Read and analyze the JSON:
   - Use read_file to read {json_file_path}
   - Understand the data structure

3. Write a Python script that:
   - Reads the JSON file
   - Creates an Excel workbook with pandas
   - Creates separate sheets for different data categories
   - Handles nested structures properly
   - Saves to {os.path.join(session_dir, file_name)}

4. Execute your script using save_to_file_and_run

5. Verify the Excel file was created successfully

Remember: The JSON contains financial data with nested structures. Create appropriate sheets for company info, financial metrics, and metadata."""

        # Run Excel generation
        print(f"[agno-process] Running Excel generation for session {session_id}")
        print(f"[agno-process] Working directory: {session_dir}")
        print(f"[agno-process] Expected output file: {file_name}")
        
        # Run Excel generation with proper continuation handling
        print(f"[agno-process] Starting Excel generation for session {session_id}")
        
        try:
            # Initial run
            result = excel_agent.run(excel_prompt)
            print(f"[agno-process] Initial run completed. Type: {type(result)}")
            
            # Handle continuation using the proper pattern from documentation
            max_continuations = 10
            continuation_count = 0
            
            while continuation_count < max_continuations:
                # Check if agent is paused (preferred method)
                if hasattr(excel_agent, 'is_paused') and excel_agent.is_paused:
                    print("[agno-process] Agent is paused, continuing...")
                    result = excel_agent.continue_run()
                    continuation_count += 1
                    continue
                
                # Check status if available
                if hasattr(result, 'status'):
                    print(f"[agno-process] Run status: {result.status}")
                    
                    if result.status == "PAUSED":
                        print("[agno-process] Status is PAUSED, continuing...")
                        result = excel_agent.continue_run(run_response=result)
                        continuation_count += 1
                        continue
                    elif result.status in ["COMPLETED", "CANCELLED"]:
                        print(f"[agno-process] Run {result.status}")
                        break
                
                # Check if Excel file was created
                excel_path = os.path.join(session_dir, file_name)
                if os.path.exists(excel_path):
                    print(f"[agno-process] Success! Excel file created at: {excel_path}")
                    break
                
                # If no pause/status but no file, try one more continuation
                if continuation_count == 0:
                    print("[agno-process] No file created yet, attempting continuation...")
                    try:
                        result = excel_agent.continue_run()
                        continuation_count += 1
                    except Exception as e:
                        print(f"[agno-process] Continue failed: {e}")
                        break
                else:
                    # No more continuations
                    break
            
            # Final check for Excel file
            excel_path = os.path.join(session_dir, file_name)
            if not os.path.exists(excel_path):
                # Check for any Excel files
                excel_files = list(Path(session_dir).glob("*.xlsx"))
                if excel_files:
                    excel_path = str(excel_files[0])
                    file_name = excel_files[0].name
                    print(f"[agno-process] Found Excel file: {excel_path}")
                else:
                    all_files = list(Path(session_dir).iterdir())
                    print(f"[agno-process] No Excel file created. Files: {[f.name for f in all_files]}")
                    raise HTTPException(
                        status_code=500,
                        detail="Excel generation failed - no output file created"
                    )
                    
        except Exception as e:
            print(f"[agno-process] Excel generation error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Excel generation failed: {str(e)}"
            )

        # After all attempts, check if Excel file was created
        excel_path = os.path.join(session_dir, file_name)
        print(f"[agno-process] Final check for Excel file at: {excel_path}")
        
        if not os.path.exists(excel_path):
            # Try to find any Excel file in the directory
            excel_files = list(Path(session_dir).glob("*.xlsx"))
            print(f"[agno-process] Excel files found in directory: {[str(f) for f in excel_files]}")
            
            if excel_files:
                excel_path = str(excel_files[0])
                file_name = excel_files[0].name
                print(f"[agno-process] Using found Excel file: {excel_path}")
            else:
                # List all files in the directory for debugging
                all_files = list(Path(session_dir).iterdir())
                print(f"[agno-process] All files in directory: {[str(f) for f in all_files]}")
                
                # One final attempt with explicit instructions
                print("[agno-process] Making final attempt with explicit script...")
                final_prompt = f"""No Excel file was created. Let me provide you with a complete solution.

Use save_to_file_and_run with this exact script:

```python
import json
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows

# Read JSON
with open('{json_file_path}', 'r') as f:
    data = json.load(f)

# Create workbook
wb = Workbook()
wb.remove(wb.active)

# Sheet 1: Company Info
ws1 = wb.create_sheet("Company Information")
if 'company_identification' in data:
    for key, value in data['company_identification'].items():
        ws1.append([key.replace('_', ' ').title(), str(value)])

# Sheet 2: Financial Metrics
if 'financial_metrics' in data:
    for metric_type, metric_list in data['financial_metrics'].items():
        if isinstance(metric_list, list) and metric_list:
            ws = wb.create_sheet(metric_type.replace('_', ' ').title()[:31])
            if metric_list:
                headers = list(metric_list[0].keys())
                ws.append(headers)
                for item in metric_list:
                    ws.append([item.get(h, '') for h in headers])

# Save
wb.save('{excel_path}')
print(f"Excel file created at: {excel_path}")
```

Execute this script now."""
                
                try:
                    final_result = excel_agent.run(final_prompt)
                    print(f"[agno-process] Final attempt result: {final_result}")
                    
                    # Check one more time
                    if os.path.exists(excel_path):
                        print(f"[agno-process] Success! Excel file created at: {excel_path}")
                    else:
                        raise HTTPException(
                            status_code=500, detail="Excel file generation failed - no .xlsx file created"
                        )
                except Exception as e:
                    print(f"[agno-process] Final attempt failed: {str(e)}")
                    raise HTTPException(
                        status_code=500, detail="Excel file generation failed - no .xlsx file created"
                    )

        # Schedule cleanup
        background_tasks.add_task(
            cleanup_session, session_dir, delay_seconds=3600
        )  # 1 hour

        # Return download URL
        return {
            "success": True,
            "download_url": f"/api/download-report/{session_id}?filename={file_name}",
            "file_name": file_name,
            "session_id": session_id,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agno processing failed: {str(e)}")


@app.post("/api/test-excel-generation")
async def test_excel_generation():
    """
    Test endpoint for Excel generation to debug issues.
    """
    try:
        # Create test data
        test_data = {
            "products": [
                {"id": 1, "name": "Product A", "price": 100.50, "quantity": 10},
                {"id": 2, "name": "Product B", "price": 200.75, "quantity": 5},
                {"id": 3, "name": "Product C", "price": 50.25, "quantity": 20}
            ]
        }
        
        # Create session directory
        session_id = str(uuid.uuid4())
        session_dir = os.path.join(TEMP_DIR, f"test_{session_id}")
        os.makedirs(session_dir, exist_ok=True)
        
        # Save test data
        json_file_path = os.path.join(session_dir, "test_data.json")
        with open(json_file_path, "w") as f:
            json.dump(test_data, f, indent=2)
        
        # Initialize Excel generator
        from .agents.excel_generator import ExcelGeneratorAgent
        excel_agent = ExcelGeneratorAgent(
            model=get_transform_model(model_id="gemini-2.0-flash"),
            working_dir=session_dir
        )
        
        # Simple prompt
        excel_prompt = f"""
        You need to create an Excel file from JSON data using Python.
        
        Input file: {json_file_path}
        Output file: {os.path.join(session_dir, "test_output.xlsx")}
        
        Steps:
        1. First install pandas and openpyxl using pip_install_package
        2. Write a Python script that reads the JSON and creates an Excel file
        3. Use save_to_file_and_run to execute your script
        
        The JSON contains product data with id, name, price, and quantity fields.
        """
        
        # Run generation
        result = excel_agent.run(excel_prompt)
        
        # Check results
        excel_files = list(Path(session_dir).glob("*.xlsx"))
        
        return {
            "success": True,
            "session_id": session_id,
            "session_dir": session_dir,
            "excel_files": [str(f) for f in excel_files],
            "all_files": [str(f) for f in Path(session_dir).iterdir()],
            "agent_result": str(result.content) if hasattr(result, 'content') else str(result)
        }
        
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


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
            files.append(
                {
                    "name": file_path.name,
                    "size": file_path.stat().st_size,
                    "type": (
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        if file_path.suffix == ".xlsx"
                        else "unknown"
                    ),
                }
            )

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
            formatted_models.append(
                {
                    "id": model["id"],
                    "displayName": model["displayName"],
                    "description": model["description"],
                    "provider": model["provider"],
                    "supportedIn": model["supportedIn"],
                    "capabilities": model.get("capabilities", {}),
                    "limits": model.get("limits", {}),
                    "pricing": model.get("pricing", {}),
                    "status": model.get("status", "stable"),
                }
            )

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
                    "status": "stable",
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
        "temp_dir_exists": os.path.exists(TEMP_DIR),
    }


@app.get("/")
async def root():
    """
    Root endpoint.
    """
    return {
        "message": "IntelliExtract API - AI-powered data extraction using Agno workflows",
        "docs": "/docs",
        "health": "/health",
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
        "app.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )
