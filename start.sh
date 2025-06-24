#!/bin/bash

# Start script for Final App - Backend and Frontend
# This script installs dependencies and starts both services

set -e

echo "🚀 Starting Final App - Backend and Frontend"
echo "=============================================="

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is available
port_available() {
    ! lsof -i:$1 >/dev/null 2>&1
}

# Function to cleanup background processes on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    # Kill background processes
    jobs -p | xargs -r kill
    exit 0
}

# Set up trap to cleanup on script exit
trap cleanup SIGINT SIGTERM EXIT

# Check required tools
echo "🔍 Checking required tools..."

if ! command_exists python3; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

if ! command_exists node; then
    echo "❌ Node.js is required but not installed"
    exit 1
fi

if ! command_exists npm; then
    echo "❌ npm is required but not installed"
    exit 1
fi

echo "✅ All required tools are available"

# Check if ports are available
echo "🔍 Checking port availability..."
if ! port_available 8000; then
    echo "❌ Port 8000 (backend) is already in use"
    exit 1
fi

if ! port_available 9002; then
    echo "❌ Port 9002 (frontend) is already in use"
    exit 1
fi

echo "✅ Ports 8000 and 9002 are available"

# Install backend dependencies
echo ""
echo "📦 Installing backend dependencies..."
cd backend

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "🔧 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade pip and dependencies
echo "📦 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Go back to root directory
cd ..

# Install frontend dependencies
echo ""
echo "📦 Installing frontend dependencies..."
cd frontend
npm install
cd ..

echo ""
echo "🚀 Starting services..."
echo "Backend will be available at: http://localhost:8000"
echo "Frontend will be available at: http://localhost:9002"
echo "Press Ctrl+C to stop both services"
echo ""

# Start backend in background
echo "🔧 Starting backend server..."
cd backend
source venv/bin/activate
python start_server.py --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to start
sleep 3

# Start frontend in background
echo "🔧 Starting frontend server..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Both services are starting up..."
echo "🔗 Backend: http://localhost:8000"
echo "🔗 Frontend: http://localhost:9002"
echo "📚 Backend API Docs: http://localhost:8000/docs"
echo ""
echo "💡 Waiting for services to be ready..."

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID