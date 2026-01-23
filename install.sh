#!/bin/bash

# Payday Budget Installation Script
# This script installs and sets up the Payday Budget application on a Linux system

set -e

echo "=========================================="
echo "  Payday Budget Installation"
echo "=========================================="
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Found Python version: $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Initialize database
echo "Initializing database..."
python3 -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database initialized successfully')"

echo ""
echo "=========================================="
echo "  Installation Complete!"
echo "=========================================="
echo ""
echo "To start the application:"
echo "  1. Run: ./start.sh"
echo "  2. Open browser to: http://localhost:5000"
echo ""
echo "To create a systemd service (optional):"
echo "  sudo ./create_service.sh"
echo ""
