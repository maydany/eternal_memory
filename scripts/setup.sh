#!/bin/bash
# Setup script for Eternal Memory System
# Installs pgvector extension for PostgreSQL 16

set -e

echo "=== Eternal Memory System Setup ==="

# Check if PostgreSQL is running
if ! brew services list | grep -q "postgresql@16.*started"; then
    echo "Starting PostgreSQL 16..."
    brew services start postgresql@16
fi

# Add PostgreSQL to PATH
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"

# Check if pgvector extension exists
if ! psql -d eternal_memory -c "SELECT * FROM pg_available_extensions WHERE name = 'vector';" 2>/dev/null | grep -q vector; then
    echo "Installing pgvector extension..."
    
    # Try to ensure Xcode command line tools are set up
    if [ ! -d "/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk" ]; then
        echo "Please install Xcode Command Line Tools first:"
        echo "  xcode-select --install"
        exit 1
    fi
    
    # Set SDK path
    export SDKROOT=$(xcrun --show-sdk-path)
    
    # Clone and install pgvector
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    git clone --branch v0.8.0 https://github.com/pgvector/pgvector.git
    cd pgvector
    make PG_CONFIG=/opt/homebrew/opt/postgresql@16/bin/pg_config
    sudo make install PG_CONFIG=/opt/homebrew/opt/postgresql@16/bin/pg_config
    
    # Cleanup
    rm -rf "$TEMP_DIR"
fi

# Create extension in database
echo "Enabling vector extension in database..."
psql -d eternal_memory -c "CREATE EXTENSION IF NOT EXISTS vector;"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To use the Eternal Memory System:"
echo "  1. Activate virtual environment: source .venv/bin/activate"
echo "  2. Set your OpenAI API key: export OPENAI_API_KEY='your-key'"
echo "  3. Run: python -c 'from eternal_memory import EternalMemorySystem; print(\"Ready!\")'"
