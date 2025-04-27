#!/bin/bash

# Define paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
VENV_PATH="$SCRIPT_DIR/venv"
REAL_VENV_PATH="$(readlink "$VENV_PATH" || echo "$VENV_PATH")"

# Change to the script directory
cd "$SCRIPT_DIR"

echo "Starting WriteWise backend server..."
echo "Using virtual environment: $REAL_VENV_PATH"

# Activate the virtual environment
if [ -f "$REAL_VENV_PATH/bin/activate" ]; then
    source "$REAL_VENV_PATH/bin/activate"
elif [ -f "$VENV_PATH/bin/activate" ]; then
    source "$VENV_PATH/bin/activate"
else
    echo "Error: Virtual environment activation script not found."
    echo "Looked in: $REAL_VENV_PATH/bin/activate and $VENV_PATH/bin/activate"
    read -p "Press Enter to exit."
    exit 1
fi

# Verify Python version
echo "Using Python: $(which python)"
echo "Python version: $(python --version)"

# Check for API key in environment
if [ -z "$OPENAI_API_KEY" ]; then
    # Load from .env file if it exists
    if [ -f "$SCRIPT_DIR/.env" ]; then
        echo "Loading OpenAI API key from .env file..."
        export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
        
        # Double-check that the key is now set
        if [ -z "$OPENAI_API_KEY" ]; then
            echo ""
            echo "WARNING: Could not load OpenAI API key from .env file."
            echo "Please check that the file is formatted correctly:"
            echo "OPENAI_API_KEY=your_api_key_here"
            echo "Make sure there are no spaces around the equals sign."
            echo ""
        else
            echo "Successfully loaded OpenAI API key from .env file."
        fi
    else
        echo ""
        echo "WARNING: OpenAI API key not found in environment."
        echo "The email improvement feature may not work properly."
        echo "To set your API key, create a .env file in the backend directory with:"
        echo "OPENAI_API_KEY=your_api_key_here"
        echo ""
    fi
else
    echo "OpenAI API key found in environment."
fi

# Print an important note about API key handling
echo ""
echo "NOTE: The server will now automatically try to load the API key from .env file"
echo "      even if it wasn't loaded here. This is handled by the Python dotenv package."
echo ""

# Start the Flask server
python "$SCRIPT_DIR/server.py"

# Keep the terminal open if there's an error
if [ $? -ne 0 ]; then
    echo "Server failed to start."
    read -p "Press Enter to exit."
fi 