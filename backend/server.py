from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from datetime import datetime
from tone_analysis import extract_email_features

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
data_dir = os.path.join('backend', 'data')
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

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
        if not isinstance(user_id, str):
            user_id = 'anonymous'
        # Sanitize user_id for filesystem (replace @ and . with _)
        safe_user_id = user_id.replace('@', '_').replace('.', '_')
        user_dir = os.path.join(data_dir, safe_user_id)
        os.makedirs(user_dir, exist_ok=True)
        data_filename = os.path.join(user_dir, f'data_{timestamp}.json')
        tone_filename = os.path.join(user_dir, f'tone_{timestamp}.json')
        context_filename = os.path.join(user_dir, f'context_{timestamp}.json')
        
        # Save the raw data to a file
        with open(data_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # --- Tone analysis integration ---
        # Concatenate all email bodies for tone analysis
        emails = data.get('emails', [])
        email_text = '\n\n'.join(email.get('body', '') for email in emails)
        tone_features = extract_email_features(email_text)
        with open(tone_filename, 'w', encoding='utf-8') as f:
            json.dump(tone_features, f, indent=2, ensure_ascii=False)
        # --- End integration ---
        
        # Optionally, save context (example: save the list of subjects)
        context = {
            'subjects': [email.get('subject', '') for email in emails],
            'recipients': [email.get('to', '') for email in emails]
        }
        with open(context_filename, 'w', encoding='utf-8') as f:
            json.dump(context, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'status': 'success',
            'message': f'Data saved to {data_filename}, tone analysis saved to {tone_filename}, context saved to {context_filename}'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True) 