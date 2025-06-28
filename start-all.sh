#!/bin/bash
# Start both frontend and backend

echo "🚀 Starting IntelliExtract Services..."
echo ""

# Start backend in background
echo "1️⃣  Starting Backend (port 8000)..."
cd backend
python3 manage.py start --background
cd ..

echo ""

# Start frontend
echo "2️⃣  Starting Frontend (port 9002)..."
cd frontend
npm run dev