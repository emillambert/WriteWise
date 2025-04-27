# WriteWise Backend

## Quick Start

### First Time Setup
First, install all required dependencies:

```bash
./install_dependencies.sh
```

This script will ensure all necessary packages are installed in the correct virtual environment.

### Setting Up Your OpenAI API Key

The email improvement feature requires an OpenAI API key. You can set it up in one of two ways:

#### Option 1: Create a .env file (recommended)
Create a file named `.env` in the backend directory with the following content:
```
OPENAI_API_KEY=your_api_key_here
```

**IMPORTANT**: The `.env` file must be located directly in the `backend` directory, not in any subdirectory. The server has been updated to automatically load this file at startup.

#### Option 2: Set environment variable
```bash
export OPENAI_API_KEY=your_api_key_here
```

You can get an API key from [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)

### Running the Server

#### macOS
Double-click the `start.command` file to launch the server in a new Terminal window.

#### All Platforms
Run the server from the command line:

```bash
cd /path/to/WriteWise/backend
./start.sh
```

## Development Notes

- The server runs on port 8000 by default
- API endpoints are documented in the code
- Data is stored in the `data/user/` directory
- The server automatically finds and uses the correct virtual environment
- Environment variables are now loaded automatically from the .env file

## Troubleshooting

If the server fails to start:

1. Run the dependency installer again: `./install_dependencies.sh`
2. Check the error messages in the terminal output
3. Verify that the virtual environment path is correct in both start scripts

If you see a 401 Unauthorized error when using the email improvement feature:

1. Your OpenAI API key is invalid or has expired
2. Set a valid API key using one of the methods described above
3. Verify that the .env file is located directly in the backend directory
4. Check that there are no spaces around the equals sign in the .env file 