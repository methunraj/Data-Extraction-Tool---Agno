#!/bin/bash
# Stop both frontend and backend

echo "🛑 Stopping IntelliExtract Services..."
echo ""

# Stop backend
echo "1️⃣  Stopping Backend..."
cd backend
python3 manage.py stop
cd ..

echo ""

# Stop frontend (if running)
echo "2️⃣  Stopping Frontend..."
# Find and kill any process on port 9002
lsof -ti:9002 | xargs kill -9 2>/dev/null && echo "   ✅ Frontend stopped" || echo "   ℹ️  No frontend process found"

echo ""
echo "✅ All services stopped"