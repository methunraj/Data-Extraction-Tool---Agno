# Agent Module Migration Notes

## What Was Done

The agent functionality was reorganized from being inline functions in `services.py` to a proper modular structure in the `agents/` folder.

### Changes Made:

1. **Created Agent Module Structure**:
   - `base.py`: Base class for all agents with common functionality
   - `search_agent.py`: Currency conversion and fact-checking agent
   - `strategist_agent.py`: Task planning and breakdown agent
   - `codegen_agent.py`: Python code generation agent for Excel creation
   - `qa_agent.py`: Quality assurance agent for verification
   - `factory.py`: Factory pattern for agent creation
   - `__init__.py`: Module exports

2. **Refactored services.py**:
   - Removed inline agent creation functions (`create_search_agent`, `create_strategist_agent`, etc.)
   - Updated `get_agent_by_key` to use the new factory function
   - Maintained backward compatibility with agent pool management

3. **Enhanced Agent Architecture**:
   - All agents now inherit from `BaseAgent`
   - Dynamic model selection based on `models.json` configuration
   - Proper separation of concerns with dedicated agent classes
   - Factory pattern for consistent agent creation

4. **Updated Dependencies**:
   - Fixed imports in `services.py` to use new agent module
   - Updated `test_execution.py` to use new agent creation API
   - Added agent info endpoint to show available agent types

## Benefits:

1. **Better Organization**: Each agent type is now in its own file
2. **Maintainability**: Easier to modify individual agents without affecting others
3. **Extensibility**: Simple to add new agent types by creating new classes
4. **Testability**: Each agent can be tested in isolation
5. **Documentation**: Clear structure with README and docstrings

## API Changes:

### Old Way:
```python
from app.services import create_code_gen_agent
agent = create_code_gen_agent(temp_dir)
```

### New Way:
```python
from app.agents import create_agent
agent = create_agent('codegen', temp_dir=temp_dir)
```

## New Endpoints:

- `GET /api/agents/info`: Get information about available agent types and pool status