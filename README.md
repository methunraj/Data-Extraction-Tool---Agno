# Final App - AI Data Extraction Platform

A full-stack application for AI-powered data extraction with Google Gemini models, featuring a Next.js frontend and FastAPI backend.

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+** - Backend runtime
- **Node.js 18+** - Frontend runtime  
- **npm** - Package manager

### One-Command Setup

```bash
./start.sh
```

This script will:
- Install all dependencies (Python & Node.js)
- Create Python virtual environment
- Start backend server on port 8000
- Start frontend server on port 9002

### Manual Setup

If you prefer to set up manually:

#### Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python start_server.py
```

#### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## 📍 Access Points

- **Frontend (UI)**: http://localhost:9002
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the `backend` directory:

```env
GOOGLE_API_KEY=your_google_api_key_here
```

### API Keys

1. Get a Google AI API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Add it to your backend `.env` file
3. Optionally configure it in the frontend UI (LLM Configuration page)

## 🔧 Available Models

The platform supports these Google Gemini models:
- `gemini-2.5-flash-preview-05-20` (Latest, fast)
- `gemini-2.5-pro-preview-05-06` (Enhanced reasoning)  
- `gemini-2.0-flash` (Next generation)
- `gemini-2.0-flash-lite` (Cost efficient)

Update models in: `frontend/src/contexts/LLMContext.tsx`

## 📁 Project Structure

```
Final App/
├── backend/           # FastAPI backend
│   ├── app/           # Application code
│   ├── requirements.txt
│   └── start_server.py
├── frontend/          # Next.js frontend
│   ├── src/           # Source code
│   ├── package.json
│   └── next.config.js
├── start.sh           # One-command startup script
└── README.md          # This file
```

## 🛠️ Development

### Backend Commands
```bash
cd backend
source venv/bin/activate

# Run tests
pytest

# Code formatting
black .
isort .

# Type checking
mypy .
```

### Frontend Commands
```bash
cd frontend

# Development server
npm run dev

# Type checking
npm run typecheck

# Linting
npm run lint

# Build production
npm run build
```

## 🔍 Troubleshooting

### Port Conflicts
- Backend uses port **8000**
- Frontend uses port **9002** 
- If ports are in use, stop other services or modify ports in configuration files

### API Key Issues
- Ensure `GOOGLE_API_KEY` is set in backend `.env` file
- Check API key format and permissions
- Verify quota limits in Google Cloud Console

### Connection Issues
- Confirm both services are running
- Check firewall settings
- Verify backend is accessible at http://localhost:8000

### Python Virtual Environment
```bash
# If venv activation fails
cd backend
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Node.js Dependencies
```bash
# If npm install fails
cd frontend
rm -rf node_modules package-lock.json
npm install
```
