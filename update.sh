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
echo "Checking database schema..."
if python3 -c "from app import app, db; from models import Transaction; app.app_context().push(); db.session.query(Transaction).first()" 2>&1 | grep -q "no such column"; then
    echo ""
    echo "⚠️  Database schema update required!"
    echo "This update includes breaking changes to the database schema."
    echo "A backup will be created automatically."
    echo ""
    read -p "Continue with migration? (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python3 migrate_db.py
    else
        echo "Migration cancelled. Application may not work correctly."
        exit 1
    fi
else
    python3 -c "from app import app, db; app.app_context().push(); db.create_all(); print('✓ Database schema is up to date')"
fi

echo ""
echo "=========================================="
echo "  Update Complete!"
echo "=========================================="
echo ""
echo "Restart the application for changes to take effect."
echo ""
