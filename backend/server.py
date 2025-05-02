from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from feature_extraction import extract_email_features
from tone_classification import classify_tone_axes
from profile_aggregation import aggregate_user_profile
import subprocess
import re
import logging
import numpy as np
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server environment

app = Flask(__name__)

# Enable CORS for all routes with specific origins
CORS(app, resources={r"/*": {
    "origins": [
        "https://mail.google.com",
        "http://localhost:27481",
        "chrome-extension://*"
    ],
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type"],
    "supports_credentials": True
}})

# Ensure data directory exists
data_dir = os.path.join('data', 'user')
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

def generate_cluster_visualization(user_dir, tone_axes_list, user_id, timestamp):
    """
    Generates a visualization of tone clusters reduced to 2 principal components.
    
    Args:
        user_dir: Directory to save the visualization
        tone_axes_list: List of tone classification results
        user_id: User identifier
        timestamp: Current timestamp string
    
    Returns:
        str: Path to the generated visualization file
    """
    # Skip if we don't have at least 2 data points
    if not tone_axes_list or len(tone_axes_list) < 2:
        logging.warning("Not enough data points for clustering visualization")
        return None
    
    try:
        # Extract features for clustering
        features = []
        
        # Define which tone axes to use for clustering
        tone_dimensions = [
            'formality', 'politeness', 'certainty', 'emotion', 
            'greeting_score', 'closing_score', 'emoji_score', 
            'directness', 'subjectivity'
        ]
        
        # Collect numeric values
        for tone in tone_axes_list:
            if not tone:  # Skip empty entries
                continue
                
            # Extract numeric values for each dimension
            # Convert categorical dimensions to numeric values
            tone_features = []
            
            # Formality: formal=2, neutral=1, informal=0
            formality = tone.get('formality', 'neutral')
            if formality == 'formal':
                tone_features.append(2)
            elif formality == 'neutral':
                tone_features.append(1)
            else:
                tone_features.append(0)
                
            # Politeness: polite=2, neutral=1, impolite=0
            politeness = tone.get('politeness', 'neutral')
            if politeness == 'polite':
                tone_features.append(2)
            elif politeness == 'neutral':
                tone_features.append(1)
            else:
                tone_features.append(0)
                
            # Certainty: confident=2, balanced=1, hedged=0
            certainty = tone.get('certainty', 'balanced')
            if certainty == 'confident':
                tone_features.append(2)
            elif certainty == 'balanced':
                tone_features.append(1)
            else:
                tone_features.append(0)
                
            # Emotion: positive=2, neutral=1, negative=0
            emotion = tone.get('emotion', 'neutral')
            if emotion == 'positive':
                tone_features.append(2)
            elif emotion == 'neutral':
                tone_features.append(1)
            else:
                tone_features.append(0)
                
            # Presence dimensions: map present=1, absent=0
            greeting = tone.get('greeting', 'absent')
            tone_features.append(1 if greeting == 'present' else 0)
            
            closing = tone.get('closing', 'absent')
            tone_features.append(1 if closing == 'present' else 0)
            
            # Emoji usage: high=2, some=1, none=0
            emoji_usage = tone.get('emoji_usage', 'none')
            if emoji_usage == 'high':
                tone_features.append(2)
            elif emoji_usage == 'some':
                tone_features.append(1)
            else:
                tone_features.append(0)
                
            # Directness: direct=1, indirect=0
            directness = tone.get('directness', 'direct')
            tone_features.append(1 if directness == 'direct' else 0)
            
            # Subjectivity: personal=1, objective=0
            subjectivity = tone.get('subjectivity_level', 'objective')
            tone_features.append(1 if subjectivity == 'personal' else 0)
            
            features.append(tone_features)
        
        # Skip if not enough valid entries
        if len(features) < 2:
            logging.warning("Not enough valid entries for clustering visualization")
            return None
            
        # Convert to numpy array
        X = np.array(features)
        
        # Standardize features
        X_scaled = StandardScaler().fit_transform(X)
        
        # Apply PCA to reduce to 2 dimensions
        pca = PCA(n_components=2)
        principal_components = pca.fit_transform(X_scaled)
        
        # Determine number of clusters (between 2 and 5)
        max_clusters = min(5, len(X))
        min_clusters = 2
        
        # Use KMeans to identify clusters
        optimal_k = 3  # Default to 3 clusters
        
        # Try to find optimal number of clusters using elbow method
        try:
            distortions = []
            K_range = range(min_clusters, max_clusters + 1)
            for k in K_range:
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                kmeans.fit(X_scaled)
                distortions.append(kmeans.inertia_)
                
            # Simple elbow method: look for the "elbow" in the curve
            deltas = np.diff(distortions)
            # If the second derivative is at maximum, it's likely the elbow point
            if len(deltas) > 1:
                acceleration = np.diff(deltas)
                optimal_idx = np.argmax(acceleration) + 1
                optimal_k = K_range[optimal_idx]
        except Exception as e:
            logging.error(f"Error determining optimal clusters: {e}")
        
        # Apply KMeans with the determined number of clusters
        kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(X_scaled)
        
        # Create the visualization
        plt.figure(figsize=(10, 8))
        scatter = plt.scatter(principal_components[:, 0], principal_components[:, 1], 
                   c=clusters, cmap='viridis', s=100, alpha=0.8)
        
        # Add centroids
        centroids_pca = pca.transform(kmeans.cluster_centers_)
        plt.scatter(centroids_pca[:, 0], centroids_pca[:, 1], 
                   marker='X', s=200, color='red', label='Centroids')
        
        # Add styling and information
        plt.title(f'Email Style Clusters ({optimal_k} Clusters Identified)', fontsize=16)
        plt.xlabel(f'Principal Component 1 ({pca.explained_variance_ratio_[0]:.2%} variance)', fontsize=14)
        plt.ylabel(f'Principal Component 2 ({pca.explained_variance_ratio_[1]:.2%} variance)', fontsize=14)
        plt.colorbar(scatter, label='Cluster')
        plt.legend()
        plt.grid(alpha=0.3)
        
        # Add feature contribution arrows
        if pca.components_.shape[1] == len(tone_dimensions):
            # Scale the feature arrows to fit nicely on the plot
            scale = 2  
            for i, feature in enumerate(tone_dimensions):
                plt.arrow(0, 0, 
                        pca.components_[0, i] * scale, 
                        pca.components_[1, i] * scale,
                        head_width=0.1, head_length=0.1, fc='blue', ec='blue', alpha=0.5)
                plt.text(pca.components_[0, i] * scale * 1.15, 
                       pca.components_[1, i] * scale * 1.15,
                       feature, fontsize=12)
        
        # Save the figure
        viz_dir = os.path.join(user_dir, 'analysis', 'visualizations')
        os.makedirs(viz_dir, exist_ok=True)
        viz_file = os.path.join(viz_dir, f'clusters_{timestamp}.png')
        plt.tight_layout()
        plt.savefig(viz_file, dpi=300)
        plt.close()
        
        logging.info(f"Generated cluster visualization with {optimal_k} clusters")
        
        return viz_file
        
    except Exception as e:
        logging.error(f"Error generating cluster visualization: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return None

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
        
        # Create analysis directory if it doesn't exist
        analysis_dir = os.path.join(user_dir, "analysis")
        os.makedirs(analysis_dir, exist_ok=True)
        
        data_filename = os.path.join(analysis_dir, f'data_{timestamp}.json')
        tone_filename = os.path.join(analysis_dir, f'tone_{timestamp}.json')
        
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

        features_filename = os.path.join(analysis_dir, f'features_{timestamp}.json')
        try:
            with open(features_filename, 'w', encoding='utf-8') as f:
                json.dump(features_list, f, indent=2, ensure_ascii=False)
        except Exception as file_err:
            logging.error(f"Failed to save features file: {file_err}")
            
        tone_axes_filename = os.path.join(analysis_dir, f'tone_axes_{timestamp}.json')
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
        
        # Generate and save cluster visualization
        try:
            viz_file = generate_cluster_visualization(user_dir, tone_axes_list, safe_user_id, timestamp)
            if viz_file:
                logging.info(f"Saved cluster visualization to {os.path.basename(viz_file)}")
                # Add visualization path to response
                response_data = {
                    'status': 'success',
                    'message': 'Analysis complete and data saved.',
                    'profile': user_profile,
                    'visualization': os.path.basename(viz_file)
                }
            else:
                response_data = {
                    'status': 'success',
                    'message': 'Analysis complete and data saved.',
                    'profile': user_profile
                }
        except Exception as viz_err:
            logging.error(f"Error with visualization: {viz_err}")
            response_data = {
                'status': 'success',
                'message': 'Analysis complete and data saved.',
                'profile': user_profile
            }
        
        return jsonify(response_data)
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
        
        # Create context directory if it doesn't exist
        context_dir = os.path.join(user_dir, "context")
        os.makedirs(context_dir, exist_ok=True)
        
        context_filename = os.path.join(context_dir, f'context_{timestamp}.json')
        
        # Save current context data
        try:
            with open(context_filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logging.info(f"Saved context file: {os.path.basename(context_filename)}")
        except Exception as file_err:
            logging.error(f"Failed to save context file: {file_err}")
            # Continue processing even if file save fails
            
        # Import improve_email module and its helper functions
        import sys
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from improve_email import build_prompt, query_chatgpt, save_improved_result, get_latest_file
        
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
            
            # Check in analysis folder if no files found in user_dir
            if not tone_files and os.path.exists(os.path.join(user_dir, 'analysis')):
                analysis_dir = os.path.join(user_dir, 'analysis')
                tone_files = [f for f in os.listdir(analysis_dir) if f.startswith('tone_') and f.endswith('.json')]
                if tone_files:
                    latest_tone_file = os.path.join(analysis_dir, sorted(tone_files)[-1])
                    logging.info(f"Using existing tone file from analysis folder: {os.path.basename(latest_tone_file)}")
                    
                    try:
                        with open(latest_tone_file, 'r', encoding='utf-8') as f:
                            user_profile = json.load(f)
                    except Exception as file_err:
                        logging.error(f"Failed to read tone file: {file_err}")
                        return jsonify({'status': 'error', 'message': 'Failed to read tone data'}), 500
                    
            elif not tone_files:
                # Create tone file from the provided content
                content = data.get("content", "")
                content_length = len(content) if content else 0
                logging.info(f"No tone file found, creating new one from content (length={content_length})")
                
                try:
                    features = extract_email_features(content)
                    tone_axes = classify_tone_axes(features)
                    
                    # Create analysis directory if it doesn't exist
                    analysis_dir = os.path.join(user_dir, "analysis")
                    os.makedirs(analysis_dir, exist_ok=True)
                    
                    tone_filename = os.path.join(analysis_dir, f'tone_{timestamp}.json')
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
        
        # Always use current context data for improvement
        def get_first(val, default=""):
            if isinstance(val, list):
                return val[0] if val else default
            elif isinstance(val, str):
                return val
            return default
            
        # Extract all necessary data from the context
        recipients_data = data.get("recipients", {})
        content = data.get("content", "")
        subject = data.get("subject", "")
        content_length = len(content) if content else 0
        
        logging.info(f"Processing improvement request - Subject: '{subject}', Content length: {content_length}")
        
        try:
            # Use the enhanced query_chatgpt function that selects style clusters
            improved = query_chatgpt("", recipients_data, user_profile, content, subject)
            
            # Log the selected cluster for analytics
            selected_cluster = improved.get("cluster", "Unknown")
            logging.info(f"Improved email using cluster: {selected_cluster}")
            
            # Create validation report (not actively used in server mode)
            validation_report = {}
            
            # Save the improved email
            improved_path = save_improved_result(improved, validation_report, user_dir, safe_user_id)
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
    app.run(host='0.0.0.0', port=27481, debug=True) 