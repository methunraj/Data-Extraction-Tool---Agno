# Unified Generation Flow Update

## Overview
Updated the frontend to use the backend API for unified configuration generation instead of the frontend-based unified-generation-flow.

## Changes Made

### 1. Frontend Changes

#### ConfigurationContext.tsx
- Modified the `generateFromPrompt` method to use the backend API service instead of the frontend unified-generation-flow
- Added API key passing to the backend service call
- Updated example format conversion to handle backend response format
- Removed unused mock generation functions

#### backend-api.ts
- Updated `generateUnifiedConfig` method to accept an optional API key parameter
- Added X-API-Key header support for authentication

### 2. Backend Integration
The backend already had the necessary endpoints in place:
- `/api/generate-unified-config` - Generates complete extraction configuration
- The endpoint is properly registered in main.py via the generation_router

## API Details

### Request Format
```json
{
  "user_intent": "string",
  "document_type": "string (optional)",
  "sample_data": "string (optional)",
  "model_name": "string",
  "temperature": 0.7,
  "include_examples": true,
  "example_count": 2,
  "include_reasoning": true
}
```

### Response Format
```json
{
  "schema": "string (JSON schema)",
  "system_prompt": "string",
  "user_prompt_template": "string",
  "examples": [
    {
      "input": "string",
      "output": {}
    }
  ],
  "reasoning": "string (optional)",
  "cost": 0.0,
  "tokens_used": 0
}
```

## Testing
A test script has been created at `backend/test_unified_generation.py` to verify the endpoint functionality.

To test:
1. Ensure the backend server is running
2. Run: `python test_unified_generation.py`

## Benefits
- Centralized AI generation logic in the backend
- Better API key management and security
- Consistent model handling across frontend and backend
- Easier to maintain and update AI generation logic