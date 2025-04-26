from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from datetime import datetime

app = Flask(__name__)

# Enable CORS for all routes with specific origins
CORS(app, resources={r"/*": {
    "origins": [
        "https://mail.google.com",
        "http://localhost:8000",
        "chrome-extension://*"
    ],
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type"],
    "supports_credentials": True
}})

# Ensure data directory exists
if not os.path.exists('data'):
    os.makedirs('data')

@app.route('/analyze', methods=['POST', 'OPTIONS'])
def analyze():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        # Get the raw data from the request
        data = request.get_json()
        
        # Generate filename with timestamp and user_id
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        user_id = data.get('user_id', 'anonymous')
        # Sanitize user_id for filesystem (replace @ and . with _)
        safe_user_id = user_id.replace('@', '_').replace('.', '_')
        filename = f'data/context_{timestamp}_{safe_user_id}.json'
        
        # Save the raw data to a file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'status': 'success',
            'message': f'Data saved to {filename}'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True) 