#!/bin/bash

# Kill running processes
pkill -f "uvicorn eternal_memory.api.main:app"
pkill -f "vite"

# Start Backend
echo "Starting Backend..."
source .venv/bin/activate
uvicorn eternal_memory.api.main:app --host 0.0.0.0 --port 8000 &
PID_BACKEND=$!

# Wait for Backend
sleep 3

# Start Frontend
echo "Starting Frontend..."
cd ui
npm run dev &
PID_FRONTEND=$!

echo "Eternal Memory System is running!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"

# Wait for processes
wait $PID_BACKEND $PID_FRONTEND
