#!/bin/bash

# Payday Budget Update Script
# This script updates the application dependencies

set -e

echo "=========================================="
echo "  Payday Budget Update"
echo "=========================================="
echo ""

# Check if virtual environment exists
if [ ! -f "venv/bin/activate" ]; then
    echo "Error: Virtual environment not found."
    echo "Please run ./install.sh first"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Update pip
echo "Updating pip..."
pip install --upgrade pip

# Update dependencies
echo "Updating dependencies..."
pip install --upgrade -r requirements.txt

# Run database migrations if needed
echo "Checking database..."
python3 -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database updated successfully')"

echo ""
echo "=========================================="
echo "  Update Complete!"
echo "=========================================="
echo ""
echo "Restart the application for changes to take effect."
echo ""
