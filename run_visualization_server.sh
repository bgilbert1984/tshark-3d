#!/bin/bash

# Script to run the network visualization server with proper environment setup
PROJECT_DIR="/home/ashben/www/html/Archology-WebXR"
VENV_DIR="$PROJECT_DIR/venv"
SCRIPT="$PROJECT_DIR/serve_visualization.py"

# Check if we're running as root/sudo
if [ "$EUID" -eq 0 ]; then
    echo "Running with elevated privileges (required for real network capture)..."
    
    # When running as root with sudo, we need to use the user's virtual environment
    # Get the actual username of the user who ran sudo
    if [ -n "$SUDO_USER" ]; then
        ACTUAL_USER="$SUDO_USER"
    else
        ACTUAL_USER="$(whoami)"
    fi
    
    # Get the user's home directory
    USER_HOME=$(eval echo ~$ACTUAL_USER)
    
    echo "Activating virtual environment..."
    
    # Load the virtual environment but run Python with root privileges
    # This avoids the need to ask for the password again
    source "$VENV_DIR/bin/activate"
    python "$SCRIPT"
else
    echo "Running without elevated privileges (test traffic only)..."
    echo "For real network capture, run with: sudo $0"
    
    # Simply activate the virtual environment and run the script
    cd "$PROJECT_DIR"
    source "$VENV_DIR/bin/activate"
    python "$SCRIPT"
fi