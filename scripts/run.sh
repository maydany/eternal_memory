#!/bin/bash

# Function to check if Postgres is running
check_postgres() {
    if pg_isready -q; then
        echo "✅ PostgreSQL is running."
    else
        echo "⚠️ PostgreSQL is NOT running."
        echo "Attempting to start PostgreSQL..."
        if command -v brew &> /dev/null; then
            brew services start postgresql@16
            
            # Wait for it to start
            for i in {1..10}; do
                if pg_isready -q; then
                    echo "✅ PostgreSQL started successfully."
                    return 0
                fi
                sleep 1
            done
            
            echo "❌ Failed to start PostgreSQL. Please start it manually."
            exit 1
        else
            echo "❌ 'brew' not found. Please start PostgreSQL manually."
            exit 1
        fi
    fi
}

# Kill running processes
pkill -f "uvicorn eternal_memory.api.main:app"
pkill -f "vite"

# Check & Start Database
check_postgres

# Start Backend
echo "Starting Backend..."
source .venv/bin/activate
uvicorn eternal_memory.api.main:app --host 0.0.0.0 --port 8000 &
PID_BACKEND=$!

# Wait for Backend to be ready
sleep 3

# Start Frontend
echo "Starting Frontend..."
cd ui
npm run dev &
PID_FRONTEND=$!

echo "🚀 Eternal Memory System is running!"
echo "📡 Backend: http://localhost:8000"
echo "💻 Frontend: http://localhost:5173"

# Wait for processes
wait $PID_BACKEND $PID_FRONTEND
