# WriteWise Backend

This is the backend server for the WriteWise Chrome extension.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the server:
```bash
python server.py
```

The server will start on http://localhost:5000

## API Endpoints

### POST /analyze
Analyzes an email for tone, grammar, and clarity.

Request body:
```json
{
    "subject": "Email subject",
    "content": "Email content",
    "thread": ["Previous email content"],
    "is_reply": true
}
```

Response:
```json
{
    "tone": {
        "score": 0.8,
        "suggestions": ["Consider using a more formal tone", "Add a greeting"]
    },
    "grammar": {
        "score": 0.9,
        "suggestions": ["Fix punctuation in line 3", "Consider using active voice"]
    },
    "clarity": {
        "score": 0.85,
        "suggestions": ["Add more context to your request", "Break down complex sentences"]
    }
}
``` 