#!/bin/bash
# Eternal Memory - Frontend & Backend Restart Script

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
UI_DIR="$PROJECT_DIR/ui"

echo "🔄 Restarting Eternal Memory..."

# Kill existing processes
echo "⏹ Stopping existing processes..."
pkill -f "uvicorn eternal_memory.api.server:app" 2>/dev/null || true
pkill -f "vite.*5173" 2>/dev/null || true
sleep 1

# Backend
echo "🚀 Starting Backend (port 8000)..."
cd "$PROJECT_DIR"
source .venv/bin/activate
nohup uvicorn eternal_memory.api.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/eternal_memory_backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

# Frontend
echo "🚀 Starting Frontend (port 5173)..."
cd "$UI_DIR"
nohup npm run dev > /tmp/eternal_memory_frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

# Wait and check
sleep 3
echo ""
echo "✅ Restart complete!"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo ""
echo "📋 Logs:"
echo "   Backend:  tail -f /tmp/eternal_memory_backend.log"
echo "   Frontend: tail -f /tmp/eternal_memory_frontend.log"
