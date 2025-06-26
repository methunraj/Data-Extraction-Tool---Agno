# Agent Guidelines for Data Extraction Tool

## Build/Test Commands
- **Frontend**: `cd frontend && npm run dev` (port 9002), `npm run build`, `npm run lint`, `npm run typecheck`
- **Backend**: `cd backend && uvicorn app.main:app --reload` (port 8000), `python run_tests.py smoke|full|check`
- **Single test**: `python run_tests.py smoke` for quick validation

## Code Style

### Python (Backend)
- Use FastAPI with async/await patterns
- Type hints required (Pydantic models for schemas)
- Import order: stdlib, third-party, local (`from ..core.dependencies import`)
- Class naming: PascalCase, functions: snake_case
- Error handling: Custom exceptions in `core.exceptions`, HTTP exceptions for API
- Logging: `logger = logging.getLogger(__name__)`

### TypeScript (Frontend)
- Next.js 15 with React 18, strict TypeScript
- Use `'use client'` for client components
- Import aliases: `@/` for src directory
- Component naming: PascalCase, files: PascalCase.tsx
- UI components: Radix UI + Tailwind CSS
- State: React hooks, forms with react-hook-form + zod validation
- Error handling: toast notifications via useToast hook

## Architecture
- Backend: FastAPI + Agno agents + Pydantic schemas
- Frontend: Next.js + TypeScript + Tailwind + shadcn/ui
- No Cursor/Copilot rules found - follow existing patterns