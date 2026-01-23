#!/bin/bash

# Create systemd service for Payday Budget
# This script must be run with sudo

if [ "$EUID" -ne 0 ]; then
    echo "Please run this script with sudo"
    exit 1
fi

INSTALL_DIR=$(pwd)
USER=$(logname)

echo "Creating systemd service for Payday Budget..."

# Generate a secure secret key
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')

# Create systemd service file
cat > /etc/systemd/system/payday-budget.service << EOF
[Unit]
Description=Payday Budget Application
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment="SECRET_KEY=$SECRET_KEY"
ExecStart=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

echo ""
echo "Service created successfully!"
echo ""
echo "To manage the service:"
echo "  Start:   sudo systemctl start payday-budget"
echo "  Stop:    sudo systemctl stop payday-budget"
echo "  Status:  sudo systemctl status payday-budget"
echo "  Enable on boot: sudo systemctl enable payday-budget"
echo ""
