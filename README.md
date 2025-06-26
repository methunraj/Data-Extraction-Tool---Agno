# IntelliExtract - AI-Powered Data Extraction Tool

IntelliExtract is an enterprise-grade, full-stack application that leverages AI agents to extract, transform, and analyze data from various sources. Built with FastAPI and Next.js, it provides a robust, scalable solution for automated data processing workflows.

## 🚀 Key Features

- **Multi-Agent Architecture**: Specialized AI agents for different data processing tasks
- **Enterprise Security**: Sandboxed execution with comprehensive validation
- **Real-time Monitoring**: Complete observability and performance tracking  
- **Flexible Processing**: Support for multiple data formats and extraction patterns
- **Production Ready**: 99.9%+ reliability with automatic failover mechanisms

## 🏗️ Architecture Overview

### Backend (FastAPI + Agno)
- **Agent Framework**: Modular AI agents with isolated execution contexts
- **Security Layer**: Comprehensive code validation and sandboxed execution
- **Monitoring System**: Real-time performance tracking and health monitoring
- **Configuration Management**: Centralized, validated configuration system

### Frontend (Next.js + TypeScript)
- **Modern UI**: Built with Radix UI components and Tailwind CSS
- **Real-time Updates**: Live monitoring and progress tracking
- **Type Safety**: Full TypeScript coverage with Zod validation
- **Responsive Design**: Mobile-first, accessible interface

## 🤖 Agent Systems

### 1. Prompt Engineer Agent
**Purpose**: Generates optimized extraction configurations from user requirements.

**Capabilities**:
- JSON schema generation
- System and user prompt optimization
- Few-shot example creation
- Configuration validation

**Example Usage**:
```
"Create a schema for extracting invoice data including vendor, amount, and date"
"Generate a configuration for parsing financial reports with revenue metrics"
```

### 2. Transform Data Agents
**Purpose**: Multi-agent system for complex data processing workflows.

**Agent Pipeline**:
1. **Strategist**: Creates execution plan and coordinates workflow
2. **Search**: Gathers and indexes information from source documents  
3. **Codegen**: Generates and executes Python code for data extraction
4. **QA**: Validates extracted data quality and completeness

**Example Usage**:
```
"Extract all invoice data from the uploaded documents and export to Excel"
"Process financial reports and generate summary analytics dashboard"
```

## 🛠️ Technology Stack

### Backend Dependencies
- **FastAPI** (0.104.0+) - High-performance web framework
- **Agno** (0.22.0+) - AI agent orchestration framework
- **Pandas** (2.0.0+) - Data manipulation and analysis
- **Pydantic** (2.0.0+) - Data validation and settings management
- **Pytest** (7.4.0+) - Testing framework with async support

### Frontend Dependencies  
- **Next.js** (15.2.3) - React framework with SSR/SSG
- **React** (18.3.1) - UI library with hooks
- **TypeScript** (5.x) - Type-safe JavaScript
- **Tailwind CSS** (3.4.1) - Utility-first CSS framework
- **Radix UI** - Accessible component primitives
- **React Hook Form** + **Zod** - Form handling and validation

## 📋 Prerequisites

- **Python** 3.9+ with pip
- **Node.js** 18+ with npm
- **Google API Key** for AI services

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/your-username/Data-Extraction-Tool---Agno.git
cd Data-Extraction-Tool---Agno
```

### 2. Environment Setup
```bash
# Automated setup (recommended)
./setup-env.sh

# Manual setup (alternative)
cp .env.shared backend/.env
cp .env.shared frontend/.env.local
```

**Configure your Google API key in `.env.shared`:**
```bash
GOOGLE_API_KEY=your_actual_google_api_key_here
```

### 3. Backend Installation
```bash
cd backend
pip install -r requirements.txt
```

### 4. Frontend Installation  
```bash
cd frontend
npm install
```

### 5. Start Services

**Backend** (Terminal 1):
```bash
# From project root
./start.sh
# Server runs on http://localhost:8000
```

**Frontend** (Terminal 2):
```bash
cd frontend
npm run dev
# App runs on http://localhost:9002
```

## 🧪 Testing

### Quick Smoke Test
```bash
cd backend
python run_tests.py smoke
```

### Comprehensive Test Suite
```bash
cd backend  
python run_tests.py full
```

### Server Health Check
```bash
cd backend
python run_tests.py check
```

### Frontend Testing
```bash
cd frontend
npm run lint        # Code linting
npm run typecheck   # Type checking
npm run build       # Production build test
```

## 📁 Project Structure

```
IntelliExtract/
├── backend/
│   ├── app/
│   │   ├── agents/                 # AI agent implementations
│   │   │   ├── prompt_engineer/    # Configuration generation agent
│   │   │   ├── transform_data/     # Data processing agents
│   │   │   ├── utils/             # Agent utilities
│   │   │   ├── execution_context.py # Execution isolation
│   │   │   ├── sandbox.py         # Secure code execution
│   │   │   └── validation_framework.py # Security validation
│   │   ├── core/                  # Core application logic
│   │   ├── routers/               # API endpoints
│   │   ├── schemas/               # Pydantic models
│   │   └── services/              # Business logic
│   ├── tests/                     # Test suite
│   ├── ARCHITECTURE.md            # Detailed architecture docs
│   └── requirements.txt           # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/            # React components
│   │   │   ├── configuration/     # Config management UI
│   │   │   ├── monitoring/        # Real-time monitoring
│   │   │   └── ui/               # Reusable UI components
│   │   ├── hooks/                # Custom React hooks
│   │   └── services/             # API integration
│   └── package.json              # Node.js dependencies
├── AGENTS.md                     # Agent development guide
└── README.md                     # This file
```

## 🔧 Development Commands

### Backend
```bash
# Start development server
uvicorn app.main:app --reload --port 8000

# Run specific tests
python run_tests.py smoke|full|check

# Code formatting (if configured)
black app/
isort app/
```

### Frontend  
```bash
# Development server (port 9002)
npm run dev

# Production build
npm run build

# Code quality
npm run lint
npm run typecheck

# Genkit AI development
npm run genkit:dev
```

## 📊 Monitoring & Observability

### Health Endpoints
- **Backend Health**: `http://localhost:8000/`
- **Metrics**: `http://localhost:8000/metrics`  
- **Agent Monitoring**: `http://localhost:8000/monitoring/`

### Real-time Monitoring
The application includes comprehensive monitoring:
- Agent execution tracking
- Performance metrics collection
- Error rate analysis
- Resource usage monitoring
- Configuration validation

## 🔒 Security Features

### Code Execution Security
- **Sandboxed Execution**: All agent code runs in isolated environments
- **Input Validation**: Comprehensive validation of all inputs and code
- **Path Restrictions**: File operations limited to designated directories
- **Resource Limits**: Memory and execution time constraints

### Data Security
- **Environment Isolation**: Clean environment for each execution
- **Temporary File Management**: Automatic cleanup of sensitive data
- **Access Controls**: Restricted file system access
- **Audit Logging**: Complete execution audit trail

## 🚀 Production Deployment

### Environment Variables
```bash
# Required
GOOGLE_API_KEY=your_google_api_key

# Optional (with defaults)
BACKEND_PORT=8000
FRONTEND_PORT=9002
LOG_LEVEL=INFO
TEMP_DIR=/tmp/intelliextract
```

### Production Checklist
- [ ] Configure production environment variables
- [ ] Set up proper logging and monitoring
- [ ] Configure reverse proxy (nginx/Apache)
- [ ] Set up SSL certificates
- [ ] Configure backup and recovery
- [ ] Test disaster recovery procedures

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Follow the coding standards in `AGENTS.md`
4. Run tests (`python run_tests.py full`)
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📚 Documentation

- **[ARCHITECTURE.md](backend/ARCHITECTURE.md)** - Detailed system architecture
- **[AGENTS.md](AGENTS.md)** - Agent development guidelines
- **API Documentation** - Available at `http://localhost:8000/docs` when running

## 🐛 Troubleshooting

### Common Issues

**Backend won't start:**
```bash
# Check Python version
python --version  # Should be 3.9+

# Install dependencies
pip install -r backend/requirements.txt

# Check port availability
lsof -i :8000
```

**Frontend build fails:**
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Check Node version  
node --version  # Should be 18+
```

**Agent execution errors:**
- Check Google API key configuration
- Verify temp directory permissions
- Review agent logs in monitoring dashboard

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Agno Framework** - AI agent orchestration
- **FastAPI** - High-performance web framework  
- **Next.js** - React framework
- **Radix UI** - Accessible component library
