# Agno Agents Module

This module contains the organized agent architecture for the IntelliExtract Agno AI backend. The agents are responsible for different aspects of the financial report generation workflow.

## Agent Types

### 1. SearchAgent (`search_agent.py`)
- **Purpose**: Currency conversion and fact-checking with web search capabilities
- **Tools**: Native Google search and grounding (no external tools)
- **Use Case**: Finding current exchange rates and verifying financial data

### 2. StrategistAgent (`strategist_agent.py`)
- **Purpose**: Breaking down complex tasks into manageable steps
- **Tools**: None (pure reasoning)
- **Use Case**: Creating execution plans for Excel report generation

### 3. CodeGenAgent (`codegen_agent.py`)
- **Purpose**: Python code generation and execution for Excel creation
- **Tools**: PythonTools (code execution, file I/O, pip install)
- **Use Case**: Generating comprehensive Excel reports with multiple sheets
- **Required Args**: `temp_dir` (where to save files)
- **Optional Args**: `exchange_rates` (pre-fetched currency data)

### 4. QualityAssuranceAgent (`qa_agent.py`)
- **Purpose**: Verifying code quality and output correctness
- **Tools**: PythonTools (read-only for inspection)
- **Use Case**: Reviewing generated Excel files and code

## Architecture

### Base Agent (`base.py`)
All agents inherit from `BaseAgent` which provides:
- Dynamic model selection based on `models.json` configuration
- Automatic storage management with SQLite
- Common Gemini model creation
- Debug and monitoring support

### Factory Pattern (`factory.py`)
- `create_agent(agent_type, **kwargs)`: Creates agents by type
- `get_agent_info()`: Returns information about available agents

## Usage

```python
from app.agents import create_agent

# Create a search agent
search_agent = create_agent('search')

# Create a code generation agent with temp directory
codegen_agent = create_agent('codegen', temp_dir='/tmp/reports')

# Get information about available agents
from app.agents import get_agent_info
info = get_agent_info()
```

## Agent Pool Management

Agents are cached in a pool for performance optimization:
- Pool size is limited to `MAX_POOL_SIZE` (configurable)
- Agents are keyed by type and current model configuration
- Pool automatically refreshes when model configuration changes

## Model Selection

Each agent uses the model service to dynamically select the appropriate Gemini model:
1. Checks for models with "agno" purpose in `models.json`
2. Prefers Gemini 2.0 Flash models for speed
3. Falls back to Gemini 2.5 Flash for compatibility
4. Uses `DEFAULT_AI_MODEL` as last resort

## API Endpoints

The agents module exposes these endpoints via `/api/agents`:
- `GET /api/agents/info`: Get agent types and pool status
- `GET /api/agents/pool/status`: Get current pool statistics
- `POST /api/agents/pool/refresh`: Refresh pool with new model config
- `DELETE /api/agents/pool`: Clear entire agent pool

## Configuration

Agents respect these environment variables:
- `GOOGLE_API_KEY`: Required for all agents
- `AGNO_DEBUG`: Enable debug output
- `AGNO_MONITOR`: Enable session monitoring
- `DEFAULT_AI_MODEL`: Fallback model selection