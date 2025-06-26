#!/bin/bash

# =============================================================================
# Environment Setup Script
# Data Extraction Tool - Agno AI
# =============================================================================

echo "🔧 Checking global environment configuration..."

# Check if global .env exists
if [ ! -f ".env" ]; then
    echo "❌ Error: Global .env not found. Please create it first."
    echo "   💡 Tip: Copy from .env.template: cp .env.template .env"
    exit 1
fi

# Check symlink for frontend
if [ ! -L "frontend/.env.local" ]; then
    echo "📁 Creating symlink for frontend..."
    cd frontend && ln -sf ../.env .env.local && cd ..
fi

echo "✅ Environment configuration complete!"
echo ""
echo "📝 Configuration Status:"
echo "   📍 Global config: .env"
echo "   📍 Backend reads: .env (via config.py)"  
echo "   📍 Frontend reads: .env (via symlink)"
echo ""
echo "🔑 Current API key status:"
if grep -q "AIzaSy" .env; then
    echo "   ✅ Google API key is set"
else
    echo "   ❌ Google API key needs to be set in .env"
fi
echo ""
echo "🚀 To start servers:"
echo "   Backend: cd backend && uvicorn app.main:app --reload"
echo "   Frontend: cd frontend && npm run dev"