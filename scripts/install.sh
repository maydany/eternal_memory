#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "\n${BLUE}===================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Main installation
print_header "Eternal Memory System - Installation"

# 1. Check system requirements
print_info "Checking system requirements..."

# Check if macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    print_error "This script is designed for macOS. Please install dependencies manually."
    exit 1
fi
print_success "macOS detected"

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    print_error "Homebrew is not installed. Please install it first:"
    echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    exit 1
fi
print_success "Homebrew installed"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Installing via Homebrew..."
    brew install python@3.11
fi
print_success "Python 3 available"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    print_warning "Node.js not found. Installing via Homebrew..."
    brew install node
fi
print_success "Node.js available"

# 2. Install and setup PostgreSQL
print_header "Setting up PostgreSQL + pgvector"

if ! brew list postgresql@16 &> /dev/null; then
    print_info "Installing PostgreSQL 16..."
    brew install postgresql@16
    print_success "PostgreSQL 16 installed"
else
    print_success "PostgreSQL 16 already installed"
fi

# Start PostgreSQL
if ! brew services list | grep "postgresql@16.*started" &> /dev/null; then
    print_info "Starting PostgreSQL..."
    brew services start postgresql@16
    sleep 3
    print_success "PostgreSQL started"
else
    print_success "PostgreSQL already running"
fi

# Install pgvector
if ! brew list pgvector &> /dev/null; then
    print_info "Installing pgvector extension..."
    brew install pgvector
    print_success "pgvector installed"
else
    print_success "pgvector already installed"
fi

# Create database
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
if ! psql -lqt | cut -d \| -f 1 | grep -qw eternal_memory; then
    print_info "Creating eternal_memory database..."
    createdb eternal_memory
    print_success "Database created"
else
    print_success "Database already exists"
fi

# Enable vector extension
print_info "Enabling vector extension..."
psql -d eternal_memory -c "CREATE EXTENSION IF NOT EXISTS vector;" &> /dev/null
print_success "Vector extension enabled"

# 3. Setup Python environment
print_header "Setting up Python Environment"

if [ ! -d ".venv" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv .venv
    print_success "Virtual environment created"
else
    print_success "Virtual environment already exists"
fi

print_info "Installing Python dependencies..."
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -e ".[dev]"
print_success "Python dependencies installed"

# 4. Setup Frontend
print_header "Setting up Frontend (UI)"

cd ui
if [ ! -d "node_modules" ]; then
    print_info "Installing Node.js dependencies..."
    npm install --silent
    print_success "Node.js dependencies installed"
else
    print_success "Node.js dependencies already installed"
fi
cd ..

# 5. Setup configuration
print_header "Setting up Configuration"

if [ ! -f "setting/.env" ]; then
    print_info "Creating .env file from template..."
    cp setting/.env.example setting/.env
    print_success ".env file created"
    
    # Ask for API key interactively (if terminal is interactive)
    if [ -t 0 ]; then
        echo ""
        print_info "Please enter your OpenAI API key (or press Enter to skip):"
        read -p "API Key: " api_key
        if [ ! -z "$api_key" ]; then
            # Update .env file with the API key
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s/your_openai_api_key_here/$api_key/" setting/.env
            else
                sed -i "s/your_openai_api_key_here/$api_key/" setting/.env
            fi
            print_success "API key saved to setting/.env"
        else
            print_warning "Skipped API key setup. You can add it later in setting/.env"
        fi
    else
        print_warning "Non-interactive mode. Please add your API key to setting/.env manually"
    fi
else
    print_success "Configuration file already exists"
fi

# 6. Verification
print_header "Verifying Installation"

# Check database connection
if psql -d eternal_memory -c "SELECT 1;" &> /dev/null; then
    print_success "Database connection works"
else
    print_error "Database connection failed"
    exit 1
fi

# Check Python installation
if python -c "import eternal_memory" 2> /dev/null; then
    print_success "Python package installed correctly"
else
    print_error "Python package import failed"
    exit 1
fi

# Final message
print_header "Installation Complete! 🎉"

echo -e "${GREEN}Everything is set up and ready to go!${NC}\n"
echo "Next steps:"
echo "  1. Make sure your API key is set in: ${BLUE}setting/.env${NC}"
echo "  2. Start the system: ${BLUE}./scripts/run.sh${NC}"
echo ""
echo "You can also run individual components:"
echo "  - Backend only: ${BLUE}source .venv/bin/activate && uvicorn eternal_memory.api.main:app --reload${NC}"
echo "  - Frontend only: ${BLUE}cd ui && npm run dev${NC}"
echo ""
print_success "Happy memorizing! 🧠✨"
