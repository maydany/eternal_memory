#!/bin/bash

# Colors
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ASCII Art Banner
clear
echo -e "${PURPLE}"
cat << "EOF"
================================================================
                                                                
   ███████╗████████╗███████╗██████╗ ███╗   ██╗ █████╗ ██╗     
   ██╔════╝╚══██╔══╝██╔════╝██╔══██╗████╗  ██║██╔══██╗██║     
   █████╗     ██║   █████╗  ██████╔╝██╔██╗ ██║███████║██║     
   ██╔══╝     ██║   ██╔══╝  ██╔══██╗██║╚██╗██║██╔══██║██║     
   ███████╗   ██║   ███████╗██║  ██║██║ ╚████║██║  ██║███████╗
   ╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝
                                                                
   ███╗   ███╗███████╗███╗   ███╗ ██████╗ ██████╗ ██╗   ██╗   
   ████╗ ████║██╔════╝████╗ ████║██╔═══██╗██╔══██╗╚██╗ ██╔╝   
   ██╔████╔██║█████╗  ██╔████╔██║██║   ██║██████╔╝ ╚████╔╝    
   ██║╚██╔╝██║██╔══╝  ██║╚██╔╝██║██║   ██║██╔══██╗  ╚██╔╝     
   ██║ ╚═╝ ██║███████╗██║ ╚═╝ ██║╚██████╔╝██║  ██║   ██║      
   ╚═╝     ╚═╝╚══════╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝      
                                                                
              🧠  Never Forget Again  ✨                       
                                                                
================================================================
EOF
echo -e "${NC}"
echo ""
sleep 1

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
echo -e "${CYAN}🔧 Starting Backend...${NC}"
source .venv/bin/activate
uvicorn eternal_memory.api.main:app --host 0.0.0.0 --port 8000 &
PID_BACKEND=$!


# Wait for Backend to be ready
sleep 3

# Start Frontend
echo -e "${CYAN}🎨 Starting Frontend...${NC}"
cd ui
npm run dev &
PID_FRONTEND=$!


echo ""
echo -e "${GREEN}================================================================${NC}"
echo -e "${GREEN}                                                                ${NC}"
echo -e "${GREEN}       🚀  ${YELLOW}System Successfully Started!${GREEN}  🚀                   ${NC}"
echo -e "${GREEN}                                                                ${NC}"
echo -e "${GREEN}  ${BLUE}📡 Backend API:${NC}  ${CYAN}http://localhost:8000${NC}"
echo -e "${GREEN}  ${BLUE}💻 Frontend UI:${NC}  ${CYAN}http://localhost:5173${NC}"
echo -e "${GREEN}                                                                ${NC}"
echo -e "${GREEN}  ${YELLOW}Press Ctrl+C to stop all services${NC}"
echo -e "${GREEN}                                                                ${NC}"
echo -e "${GREEN}================================================================${NC}"
echo ""

# Wait for processes
wait $PID_BACKEND $PID_FRONTEND
