# AGENTS.md - IntelliExtract Development Guide

## Build/Test Commands
**Frontend (Next.js):**
- `cd frontend && npm run dev` - Start dev server on port 9002
- `cd frontend && npm run lint` - Run ESLint
- `cd frontend && npm run typecheck` - TypeScript type checking (tsc --noEmit)
- `cd frontend && npm run build` - Production build

**Backend (FastAPI/Python):**
- `cd backend && python3 -m pytest` - Run all tests
- `cd backend && python3 -m pytest test_agno_simple.py::test_prompt_engineer_accuracy -v` - Run single test
- `cd backend && python3 -m black .` - Format code
- `cd backend && python3 -m isort .` - Sort imports
- `cd backend && python3 -m flake8 .` - Lint code
- `cd backend && python3 -m mypy .` - Type checking

## Code Style Guidelines
- **Imports:** Group by standard lib, third-party, local. Use absolute imports (app.agents.models)
- **TypeScript:** Strict mode enabled, explicit types required, prefer interfaces over types
- **Python:** Follow PEP 8, use type hints, docstrings for public functions, async/await patterns
- **React:** Functional components only, 'use client' directive required, hooks for state
- **Naming:** camelCase for JS/TS, snake_case for Python, PascalCase for components/classes
- **Error Handling:** Try/catch in async functions, proper error boundaries in React components
- **File Structure:** Components in src/components, contexts in src/contexts, services in src/services
- **Path Aliases:** Use @/* for frontend imports (maps to ./src/*)