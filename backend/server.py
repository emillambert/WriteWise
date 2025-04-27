from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from datetime import datetime
from feature_extraction import extract_email_features
from tone_classification import classify_tone_axes
from profile_aggregation import aggregate_user_profile
import subprocess
import re
import logging

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
data_dir = os.path.join('backend', 'data', 'user')
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

@app.route('/analyze', methods=['POST', 'OPTIONS'])
def analyze():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json()
        if not data or 'emails' not in data or not isinstance(data['emails'], list):
            logging.warning("Invalid input: 'emails' field missing or not a list.")
            return jsonify({'status': 'error', 'message': "Invalid input: 'emails' field missing or not a list."}), 400
        # --- Filtering logic ---
        def should_include(email):
            subject = email.get('subject', '')
            body = email.get('body', '')
            to_field = email.get('to', '')
            
            if not isinstance(subject, str):
                subject = ''
            if not isinstance(body, str):
                body = ''
            if not isinstance(to_field, str):
                to_field = ''
            
            # Exclude if subject contains 'unsubscribe' (case-insensitive)
            if 'unsubscribe' in subject.lower():
                return False
            
            # Exclude if body contains 'unsubscribe' (case-insensitive)
            if 'unsubscribe' in body.lower():
                return False
            
            # Exclude if 'to' field contains 'unsubscribe' (case-insensitive)
            if 'unsubscribe' in to_field.lower():
                return False
            
            # Exclude if body is blank or only whitespace
            if body.strip() == '':
                return False
            
            # Exclude if body starts with any whitespace or '>' followed by a line break
            if re.match(r'^[\s>]*(\r\n|\n|\r)', body):
                return False
                
            # Exclude replies by checking for common reply indicators
            if subject.lower().startswith('re:'):
                return False
                
            # Exclude forwarded messages
            if subject.lower().startswith('fwd:') or subject.lower().startswith('fw:'):
                return False
                
            # Check for quoted text patterns in the body
            if '>' in body and re.search(r'\n>[^\n]*\n', body):
                return False
                
            # Check for common forwarded message markers
            forwarded_patterns = [
                r'[-]+ ?forwarded message ?[-]+',
                r'begin forwarded message',
                r'original message',
                r'from:.*wrote:',
                r'on .* wrote:',
                r'on .* at .* wrote:'
            ]
            
            for pattern in forwarded_patterns:
                if re.search(pattern, body.lower()):
                    return False
            
            return True
        all_emails = data['emails']
        filtered_emails = []
        batch_size = 50
        i = 0
        while i < len(all_emails) and len(filtered_emails) < 100:
            batch = all_emails[i:i+batch_size]
            filtered_emails = [email for email in (filtered_emails + batch) if should_include(email)]
            if len(filtered_emails) > 100:
                filtered_emails = filtered_emails[:100]
            i += batch_size
        # Always output exactly 100 emails
        if len(filtered_emails) == 0:
            empty_email = {"subject": "", "body": "", "to": "", "from": "", "date": "", "id": ""}
            data['emails'] = [empty_email.copy() for _ in range(100)]
            logging.info("No emails passed filtering; filled with empty emails.")
        else:
            repeated = (filtered_emails * ((100 // len(filtered_emails)) + 1))[:100]
            data['emails'] = repeated
            logging.info(f"Filtered {len(filtered_emails)} emails, repeated to 100.")
        # --- End filtering logic ---
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        user_id = data.get('user_id', 'anonymous')
        if not isinstance(user_id, str):
            user_id = 'anonymous'
        safe_user_id = user_id.replace('@', '_').replace('.', '_')
        user_dir = os.path.join(data_dir, safe_user_id)
        os.makedirs(user_dir, exist_ok=True)
        data_filename = os.path.join(user_dir, f'data_{timestamp}.json')
        tone_filename = os.path.join(user_dir, f'tone_{timestamp}.json')
        # Save the raw data to a file
        try:
            with open(data_filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as file_err:
            logging.error(f"Failed to save data file: {file_err}")
            return jsonify({'status': 'error', 'message': 'Failed to save data file.'}), 500
        # --- Modular Tone Analysis Pipeline ---
        emails = data.get('emails', [])
        features_list = []
        tone_axes_list = []
        error_count = 0
        
        for idx, email in enumerate(emails):
            email_id = email.get('id', f'email_{idx}')
            short_id = str(email_id)[:8]  # Only log a short part of the ID for privacy
            body = email.get('body', '')
            
            # Don't log the full body, just log a length for debugging
            body_length = len(body) if body else 0
            
            try:
                features = extract_email_features(body)
                features_list.append(features)
                tone_axes = classify_tone_axes(features)
                tone_axes_list.append(tone_axes)
                logging.debug(f"Successfully analyzed email {short_id}, length={body_length}")
            except Exception as analysis_err:
                error_count += 1
                logging.error(f"Error analyzing email {short_id}, length={body_length}: {analysis_err}")
                # Add empty results to maintain index alignment
                features_list.append({})
                tone_axes_list.append({})
        
        if error_count > 0:
            logging.warning(f"{error_count} out of {len(emails)} emails failed analysis")

        features_filename = os.path.join(user_dir, f'features_{timestamp}.json')
        try:
            with open(features_filename, 'w', encoding='utf-8') as f:
                json.dump(features_list, f, indent=2, ensure_ascii=False)
        except Exception as file_err:
            logging.error(f"Failed to save features file: {file_err}")
        tone_axes_filename = os.path.join(user_dir, f'tone_axes_{timestamp}.json')
        try:
            with open(tone_axes_filename, 'w', encoding='utf-8') as f:
                json.dump(tone_axes_list, f, indent=2, ensure_ascii=False)
        except Exception as file_err:
            logging.error(f"Failed to save tone axes file: {file_err}")
        # Aggregate user profile
        try:
            user_profile = aggregate_user_profile(tone_axes_list)
            profile_filename = os.path.join(user_dir, 'profile.json')
            with open(profile_filename, 'w', encoding='utf-8') as f:
                json.dump(user_profile, f, indent=2, ensure_ascii=False)
        except Exception as agg_err:
            logging.error(f"Failed to aggregate or save user profile: {agg_err}")
            user_profile = {}
        # For backward compatibility, save the last tone axes as tone_features
        if tone_axes_list:
            try:
                with open(tone_filename, 'w', encoding='utf-8') as f:
                    json.dump(tone_axes_list[-1], f, indent=2, ensure_ascii=False)
            except Exception as file_err:
                logging.error(f"Failed to save tone file: {file_err}")
        logging.info(f"Analysis complete for user_id={user_id}, timestamp={timestamp}")
        return jsonify({
            'status': 'success',
            'message': 'Analysis complete and data saved.',
            'profile': user_profile
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logging.error(f'Exception in /analyze endpoint: {e}')
        logging.debug(f'Traceback: {error_trace}')
        return jsonify({
            'status': 'error',
            'message': 'An internal error occurred. Please try again later.'
        }), 500

@app.route('/profile', methods=['GET'])
def get_profile():
    user_id = request.args.get('user_id', 'anonymous')
    safe_user_id = user_id.replace('@', '_').replace('.', '_')
    user_dir = os.path.join(data_dir, safe_user_id)
    profile_filename = os.path.join(user_dir, 'profile.json')
    if not os.path.exists(profile_filename):
        return jsonify({'status': 'error', 'message': 'Profile not found'}), 404
    with open(profile_filename, 'r', encoding='utf-8') as f:
        profile = json.load(f)
    return jsonify({'status': 'success', 'profile': profile})

@app.route('/context', methods=['POST'])
def context_and_improve():
    try:
        data = request.get_json()
        if not data:
            logging.warning("Invalid input: request body is empty or not valid JSON")
            return jsonify({'status': 'error', 'message': 'Invalid input: Empty or invalid JSON'}), 400
            
        user_id = data.get('user_id', 'anonymous')
        if not isinstance(user_id, str):
            user_id = 'anonymous'
            
        safe_user_id = user_id.replace('@', '_').replace('.', '_')
        user_dir = os.path.join(data_dir, safe_user_id)
        os.makedirs(user_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        context_filename = os.path.join(user_dir, f'context_{timestamp}.json')
        
        try:
            with open(context_filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as file_err:
            logging.error(f"Failed to save context file: {file_err}")
            # Continue processing even if file save fails
            
        # Load the user's profile
        profile_filename = os.path.join(user_dir, 'profile.json')
        user_profile = {}
        
        if os.path.exists(profile_filename):
            try:
                with open(profile_filename, 'r', encoding='utf-8') as f:
                    user_profile = json.load(f)
                logging.info(f"Loaded user profile for {safe_user_id}")
            except Exception as profile_err:
                logging.error(f"Failed to read profile file: {profile_err}")
                
        # If profile doesn't exist or is empty, fall back to the latest tone file
        if not user_profile:
            logging.info("No profile found, using latest tone data as fallback")
            tone_files = [f for f in os.listdir(user_dir) if f.startswith('tone_') and f.endswith('.json')]
            
            if not tone_files:
                # Create a tone file from the provided content
                content = data.get("content", "")
                content_length = len(content) if content else 0
                logging.info(f"No tone file found, creating new one from content (length={content_length})")
                
                try:
                    features = extract_email_features(content)
                    tone_axes = classify_tone_axes(features)
                    tone_filename = os.path.join(user_dir, f'tone_{timestamp}.json')
                    with open(tone_filename, 'w', encoding='utf-8') as f:
                        json.dump(tone_axes, f, indent=2, ensure_ascii=False)
                    user_profile = tone_axes  # Use tone axes as profile fallback
                    logging.info("Created new tone data to use as profile fallback")
                except Exception as analysis_err:
                    logging.error(f"Error creating tone file: {analysis_err}")
                    return jsonify({'status': 'error', 'message': 'Failed to analyze content'}), 500
            else:
                latest_tone_file = os.path.join(user_dir, sorted(tone_files)[-1])
                logging.info(f"Using existing tone file as profile fallback: {os.path.basename(latest_tone_file)}")
                
                try:
                    with open(latest_tone_file, 'r', encoding='utf-8') as f:
                        user_profile = json.load(f)
                except Exception as file_err:
                    logging.error(f"Failed to read tone file: {file_err}")
                    return jsonify({'status': 'error', 'message': 'Failed to read tone data'}), 500
                    
        # Build prompt and get improved email
        import sys
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from improve_email import build_prompt, query_chatgpt, save_improved_result
        
        def get_first(val, default=""):
            if isinstance(val, list):
                return val[0] if val else default
            elif isinstance(val, str):
                return val
            return default
            
        recipients = get_first(data.get("recipients", ""))
        content = data.get("content", "")
        content_length = len(content) if content else 0
        
        try:
            # Use the user's profile instead of tone data
            prompt = build_prompt(recipients, user_profile, content)
            logging.info(f"Built prompt for improvement using user profile (length={len(prompt)})")
            # Don't log the full prompt as it contains the email content
            
            improved = query_chatgpt(prompt)
            logging.info(f"Received improved email from OpenAI (length={len(improved)})")
            # Don't log the entire improved email content
            
            improved_path = save_improved_result(improved, user_dir, safe_user_id)
            logging.info(f"Saved improved email to {os.path.basename(improved_path)}")
            
            return jsonify({'status': 'success', 'improved': improved})
        except Exception as improvement_err:
            logging.error(f"Error improving email: {improvement_err}")
            return jsonify({'status': 'error', 'message': 'Failed to improve the email'}), 500
            
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logging.error(f'Exception in /context endpoint: {e}')
        logging.debug(f'Traceback: {error_trace}')
        return jsonify({'status': 'error', 'message': 'An internal error occurred. Please try again later.'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True) 