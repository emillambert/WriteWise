import os
import re
import json
import requests
from datetime import datetime
from style_validator import validate_style_match, improve_style_match

# Get API key from environment variable without a fallback 
# so it's clear when it's not set properly
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Helper to find the latest file with a given prefix in a directory
def get_latest_file(user_dir, prefix):
    """
    Gets the latest file with a prefix from the appropriate directory.
    Different file types are stored in different subdirectories.
    
    Args:
        user_dir: Base user directory
        prefix: File prefix (e.g., 'context_', 'improved_', 'tone_')
        
    Returns:
        str: Path to the latest file or None if not found
    """
    # Define which directory to search based on prefix
    if prefix.startswith('context_'):
        search_dir = os.path.join(user_dir, "context")
    elif prefix.startswith('improved_'):
        search_dir = os.path.join(user_dir, "improved")
    elif prefix.startswith('data_') or prefix.startswith('tone_') or prefix.startswith('features_') or prefix.startswith('tone_axes_'):
        search_dir = os.path.join(user_dir, "analysis")
    else:
        search_dir = user_dir  # Default to base user directory
    
    # If the directory doesn't exist, check the base user directory as fallback
    if not os.path.exists(search_dir):
        search_dir = user_dir
        
    files = [f for f in os.listdir(search_dir) if f.startswith(prefix) and f.endswith('.json')]
    if not files:
        # If no files in the specific directory, check base directory as fallback
        if search_dir != user_dir:
            files = [f for f in os.listdir(user_dir) if f.startswith(prefix) and f.endswith('.json')]
            if files:
                search_dir = user_dir  # Use base directory for the file path
            else:
                return None
        else:
            return None
            
    # Extract timestamp from filename using regex
    def extract_timestamp(f):
        m = re.search(r'_(\d{8}_\d{6})', f)
        return m.group(1) if m else ''
    files.sort(key=extract_timestamp, reverse=True)
    return os.path.join(search_dir, files[0])

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_prompt(recipients, profile, content, feedback=None):
    """
    Builds a prompt for GPT to improve an email based on the user's profile
    
    Args:
        recipients: Email recipients
        profile: User's writing profile derived from aggregated analysis
        content: Draft email content
        feedback: Optional style feedback if a previous generation didn't match
        
    Returns:
        str: Formatted prompt for the GPT model
    """
    # Extract main profile for natural language summary
    main_profile = profile.get("main_profile", {})
    
    # Create a natural language summary of the user's writing style
    style_summary = (
        f"The user's writing style is predominantly {main_profile.get('formality', 'informal')} "
        f"and {main_profile.get('politeness', 'neutral')}. "
        f"They use a {main_profile.get('certainty', 'balanced')} tone "
        f"and their emails are generally {main_profile.get('emotion', 'neutral')} in sentiment. "
    )
    
    # Add more specific style details
    if main_profile.get('greeting') == 'present':
        style_summary += "They typically include greetings. "
    else:
        style_summary += "They often omit greetings. "
        
    if main_profile.get('closing') == 'present':
        style_summary += "They usually include a closing. "
    else:
        style_summary += "They often omit closings. "
    
    if main_profile.get('emoji_usage') == 'high':
        style_summary += "They frequently use emojis. "
    elif main_profile.get('emoji_usage') == 'some':
        style_summary += "They occasionally use emojis. "
    else:
        style_summary += "They rarely or never use emojis. "
    
    if main_profile.get('directness') == 'direct':
        style_summary += "Their communication style is direct and to the point. "
    else:
        style_summary += "Their communication style tends to be indirect. "
        
    if main_profile.get('subjectivity_level') == 'personal':
        style_summary += "They write in a personal, subjective manner. "
    else:
        style_summary += "They write in an objective, fact-based manner. "
    
    # Build specific style instructions
    style_instructions = [
        f"- Keep the {main_profile.get('formality', 'informal')} tone",
        f"- Use {main_profile.get('politeness', 'neutral')} language",
        f"- Maintain {main_profile.get('certainty', 'balanced')} language (avoid being too {'definitive' if main_profile.get('certainty') == 'hedged' else 'hesitant'})",
        f"- Preserve the {main_profile.get('emotion', 'neutral')} emotional tone",
    ]
    
    # Add conditional instructions based on profile
    if main_profile.get('greeting') == 'present':
        style_instructions.append("- Include a greeting")
    else:
        style_instructions.append("- Skip the greeting")
        
    if main_profile.get('closing') == 'present':
        style_instructions.append("- Include a closing")
    else:
        style_instructions.append("- Skip the closing")
    
    if main_profile.get('emoji_usage') == 'high':
        style_instructions.append("- Include some emojis where appropriate")
    elif main_profile.get('emoji_usage') == 'none':
        style_instructions.append("- Do not use any emojis")
    
    # Add specific feedback if provided
    if feedback:
        style_instructions.append("\nAdditional style guidance:")
        style_instructions.append(feedback)
    
    prompt = (
        "You are an expert email assistant. "
        "Your task is to take a draft email and:\n"
        "  1. Rewrite it to be clearer, more engaging, and match the user's writing style.\n"
        "  2. Suggest a concise, compelling subject line.\n\n"
        f"Recipients: {recipients}\n\n"
        f"User Style Summary: {style_summary}\n\n"
        f"Draft Content:\n{content}\n\n"
        "Please maintain the user's natural writing style. Specifically:\n"
        f"{chr(10).join(style_instructions)}\n\n"
        "Please output **only** a JSON object with two keys:\n"
        '  • "subject": the new subject line (string)\n'
        '  • "email": the full revised email body (string)\n'
        "No extra commentary."
    )
    return prompt

def query_chatgpt(prompt, recipients, profile, content, subject=""):
    """
    Query ChatGPT with the enhanced prompt structure using GPT-4
    
    Args:
        prompt: (Deprecated, kept for backward compatibility)
        recipients: Email recipients
        profile: User's writing profile with style clusters
        content: Draft email content
        subject: Email subject

    Returns:
        dict: Improved email with subject line
    """
    # Check if API key is available
    if not OPENAI_API_KEY:
        error_message = (
            "OpenAI API key is not set. Please set the OPENAI_API_KEY environment variable.\n\n"
            "Two ways to fix this:\n"
            "1. Create a .env file in the backend directory with this content:\n"
            "   OPENAI_API_KEY=your_api_key_here\n\n"
            "2. Or set the environment variable in your terminal:\n"
            "   export OPENAI_API_KEY=your_api_key_here\n\n"
            "You can get an API key from https://platform.openai.com/api-keys\n\n"
            "After setting the API key, restart the server."
        )
        print("\n" + "!" * 80)
        print(error_message)
        print("!" * 80 + "\n")
        return {
            "subject": "API Key Error",
            "email": "The OpenAI API key is missing. Please check the server console for instructions.",
            "cluster": "Error",
            "error": "Missing API key"
        }
    
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Extract main profile and style clusters
    main_profile = profile.get("main_profile", {})
    style_clusters = profile.get("style_clusters", [])
    
    # If no style clusters exist, create a default one based on main profile
    if not style_clusters:
        style_clusters = [{
            "name": "Default Style",
            "description": "User's default writing style based on analyzed emails",
            "profile": main_profile
        }]
    
    # Format recipient information
    if isinstance(recipients, list):
        to_recipients = ", ".join(recipients)
        cc_recipients = ""
    elif isinstance(recipients, str):
        to_recipients = recipients
        cc_recipients = ""
    else:
        to_recipients = ""
        cc_recipients = ""
        
    # Create the structured messages for the conversation
    messages = [
        # System message to set the role
        {
            "role": "system",
            "content": (
                "You are an expert email assistant. "
                "Given a user's global style profile plus a set of scenario‐specific style clusters, "
                "you will: 1) choose the cluster whose profile best matches the current email context "
                "(based on subject, recipients, and conversation tone), "
                "2) rewrite the user's draft to match that cluster's register, "
                "3) preserve the user's intent and key details."
            )
        },
        
        # Context message with email details
        {
            "role": "user",
            "content": (
                "**Context** (email to be written):\n"
                f"Subject: {subject}\n"
                f"Original draft: {content}\n"
                f"Recipients: To={to_recipients}, CC={cc_recipients}\n"
                "————\n"
                "**User's Global Style Profile:**\n" +
                json.dumps(main_profile, indent=2)
            )
        },
        
        # Style clusters message
        {
            "role": "user",
            "content": (
                "**Available Style Clusters:**\n" +
                "\n\n".join(
                    f"- **{c.get('name', f'Cluster {i}')}**: {c.get('description', 'No description')}"
                    for i, c in enumerate(style_clusters)
                )
            )
        },
        
        # Final instruction
        {
            "role": "user",
            "content": (
                "Step 1: Based on the email context above (subject and recipients), "
                "pick **one** of the style clusters by name and tell me which you chose and why. make sure to use the context to make the best choice.\n"
                "Step 2: Rewrite the draft email to match that cluster's tone, register, "
                "and stylistic preferences. Preserve all necessary details.\n"
                "Step 3: Output a JSON object with three keys:\n"
                '  • "subject": the new subject line (string)\n'
                '  • "email": the full revised email body (string)\n'
                '  • "cluster": the name of the cluster you selected (string)\n'
                "No extra commentary."
            )
        }
    ]
    
    # API request data
    data = {
        "model": "gpt-4",  # Use GPT-4 for better style matching and context understanding
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 800  # Increased max tokens to accommodate longer emails
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        
        # Check for authorization issues specifically
        if response.status_code == 401:
            error_message = (
                "OpenAI API Authorization Error (401):\n\n"
                "Your API key is invalid or expired. Please update it using one of these methods:\n\n"
                "1. Update the .env file in the backend directory with:\n"
                "   OPENAI_API_KEY=your_new_api_key_here\n\n"
                "2. Or set the environment variable in your terminal:\n"
                "   export OPENAI_API_KEY=your_new_api_key_here\n\n"
                "You can get a new API key from https://platform.openai.com/api-keys\n\n"
                "After updating the API key, restart the server."
            )
            print("\n" + "!" * 80)
            print(error_message) 
            print("!" * 80 + "\n")
            return {
                "subject": "API Authorization Error",
                "email": "There was an authorization error when connecting to OpenAI's API. Your API key may be invalid or expired. Please check the server console for instructions.",
                "cluster": "Error",
                "error": f"API Authorization Error: {response.text}"
            }
        
        # Handle other error codes
        response.raise_for_status()
        
        reply = response.json()["choices"][0]["message"]["content"]
        
        # Try to extract the JSON portion if mixed with text
        json_start = reply.find('{')
        json_end = reply.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = reply[json_start:json_end]
            try:
                result = json.loads(json_str)
                # Ensure the required fields are present
                if "subject" not in result or "email" not in result:
                    # Add missing fields with defaults if needed
                    if "subject" not in result:
                        result["subject"] = subject or "No Subject"
                    if "email" not in result:
                        result["email"] = content
                return result
            except json.JSONDecodeError:
                # If JSON parsing fails, return the full reply 
                return {
                    "subject": subject or "No Subject",
                    "email": reply,
                    "cluster": "Unknown",
                    "parsing_error": "Could not parse JSON from response"
                }
        else:
            # No JSON found, use the full reply as the email content
            return {
                "subject": subject or "No Subject",
                "email": reply,
                "cluster": "Unknown",
                "parsing_error": "No JSON found in response"
            }
    except requests.exceptions.RequestException as e:
        error_message = f"API request error: {str(e)}"
        print("\n" + "!" * 50)
        print(error_message)
        print("!" * 50 + "\n")
        return {
            "subject": "Error: API request failed",
            "email": f"An error occurred when connecting to OpenAI's API: {str(e)}",
            "cluster": "Error",
            "error": str(e)
        }

def save_improved_result(improved, validation_report, user_dir, user_id):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Add validation report to the improved result
    improved["validation"] = validation_report
    
    # Create improved directory if it doesn't exist
    improved_dir = os.path.join(user_dir, "improved")
    os.makedirs(improved_dir, exist_ok=True)
    
    improved_filename = f"improved_{timestamp}_{user_id}.json"
    improved_path = os.path.join(improved_dir, improved_filename)
    with open(improved_path, "w", encoding="utf-8") as f:
        json.dump(improved, f, indent=2, ensure_ascii=False)
    print(f"Saved improved result to {improved_path}")
    return improved_path

def main(user_id, max_attempts=2):
    # Fix the path to not include redundant 'backend' directory
    user_dir = os.path.join("data", "user", user_id)
    if not os.path.isdir(user_dir):
        print(f"User directory not found: {user_dir}")
        return
    
    # Always use profile.json and the latest context file
    profile_path = os.path.join(user_dir, "profile.json")
    latest_context = get_latest_file(user_dir, "context_")
    
    if not os.path.exists(profile_path):
        print("Profile file not found.")
        return
        
    if not latest_context:
        print("No context file found.")
        return
    
    print(f"Using latest context: {latest_context}\nUsing profile: {profile_path}")
    
    try:
        context = load_json(latest_context)
        profile = load_json(profile_path)
    except Exception as e:
        print(f"Error loading files: {e}")
        return
    
    # Extract recipients, subject, and content from context
    def get_first(val, default=""):
        if isinstance(val, list):
            return val[0] if val else default
        elif isinstance(val, str):
            return val
        return default
    
    # Handle recipients in various formats
    recipients_data = context.get("recipients", {})
    
    if isinstance(recipients_data, dict):
        # Format with to/cc fields
        to_recipients = recipients_data.get("to", [])
        cc_recipients = recipients_data.get("cc", [])
        
        # Convert to lists if they're strings
        if isinstance(to_recipients, str):
            to_recipients = [to_recipients] if to_recipients else []
        if isinstance(cc_recipients, str):
            cc_recipients = [cc_recipients] if cc_recipients else []
            
        recipients = to_recipients + cc_recipients
    elif isinstance(recipients_data, list):
        # Simple list format
        recipients = recipients_data
    else:
        # String or other format
        recipients = get_first(recipients_data, "")
    
    content = context.get("content", "")
    subject = context.get("subject", "")
    
    print(f"Extracted subject: '{subject}'")
    print(f"Extracted recipients: {recipients}")
    print(f"Content length: {len(content)} characters")
    
    # Add style clusters if they don't exist yet
    if "style_clusters" not in profile:
        # Create default style clusters based on the main profile
        main_profile = profile.get("main_profile", {})
        
        # Generate some example clusters based on the main profile
        formal_cluster = {
            "name": "Professional/Formal",
            "description": "Formal tone for professional or official communications",
            "profile": {k: v for k, v in main_profile.items()}
        }
        formal_cluster["profile"].update({
            "formality": "formal",
            "politeness": "polite",
            "greeting": "present",
            "closing": "present",
            "emoji_usage": "none"
        })
        
        casual_cluster = {
            "name": "Casual/Friendly",
            "description": "Relaxed tone for friends, family and casual acquaintances",
            "profile": {k: v for k, v in main_profile.items()}
        }
        casual_cluster["profile"].update({
            "formality": "informal",
            "politeness": "neutral",
            "emoji_usage": "some"
        })
        
        # Create a cluster using only the main profile as-is
        default_cluster = {
            "name": "Default Style",
            "description": "The user's typical writing style based on analyzed emails",
            "profile": {k: v for k, v in main_profile.items()} 
        }
        
        # Add the clusters to the profile
        profile["style_clusters"] = [default_cluster, formal_cluster, casual_cluster]
        
        # Save the updated profile with clusters
        try:
            with open(profile_path, "w", encoding="utf-8") as f:
                json.dump(profile, f, indent=2, ensure_ascii=False)
            print("Added style clusters to profile")
        except Exception as e:
            print(f"Warning: Could not save updated profile with clusters: {e}")
    
    # Initial email improvement
    improved = None
    
    try:
        # Use the updated query_chatgpt function with all parameters
        improved = query_chatgpt("", recipients, profile, content, subject)
        
        # Validate if the style matches the user's profile
        validation_report = validate_style_match(profile, improved["email"])
        match_score = validation_report.get("overall_match", 0)
        
        print(f"Style match score: {match_score:.2f}")
        print(f"Selected cluster: {improved.get('cluster', 'Unknown')}")
        
        # Save the result
        save_improved_result(improved, validation_report, user_dir, user_id)
        return improved
    except Exception as e:
        print(f"Error during email improvement: {e}")
        if improved:
            save_improved_result(improved, {"error": str(e)}, user_dir, user_id)
        return improved

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python improve_email.py <user_id>")
        exit(1)
    main(sys.argv[1]) 