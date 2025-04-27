#!/bin/bash

# Define paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
VENV_PATH="$SCRIPT_DIR/venv"
REAL_VENV_PATH="$(readlink "$VENV_PATH" || echo "$VENV_PATH")"

# Change to the script directory
cd "$SCRIPT_DIR"

echo "Installing dependencies for WriteWise backend..."
echo "Using virtual environment: $REAL_VENV_PATH"

# Activate the virtual environment
if [ -f "$REAL_VENV_PATH/bin/activate" ]; then
    source "$REAL_VENV_PATH/bin/activate"
elif [ -f "$VENV_PATH/bin/activate" ]; then
    source "$VENV_PATH/bin/activate"
else
    echo "Error: Virtual environment activation script not found."
    echo "Looked in: $REAL_VENV_PATH/bin/activate and $VENV_PATH/bin/activate"
    exit 1
fi

# Install dependencies
echo "Installing required packages..."
pip install -r requirements.txt

# Install additional packages that might be missing
echo "Installing additional potential dependencies..."
pip install pandas kneed bs4 email_reply_parser matplotlib scikit-learn

echo "Dependencies installed successfully!"
echo "You can now run './start.sh' to start the server." 