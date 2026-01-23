#!/bin/bash

# Payday Budget Start Script

# Check if virtual environment exists
if [ ! -f "venv/bin/activate" ]; then
    echo "Error: Virtual environment not found."
    echo "Please run ./install.sh first"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Set production secret key if not set
if [ -z "$SECRET_KEY" ]; then
    export SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
fi

echo "Starting Payday Budget Application..."
echo "Access the application at: http://localhost:5000"
echo "Press Ctrl+C to stop the server"
echo ""

# Start the application
python3 app.py
