import os
import re
import json
import requests
from datetime import datetime
from style_validator import validate_style_match, improve_style_match

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "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")

# Helper to find the latest file with a given prefix in a directory
def get_latest_file(user_dir, prefix):
    files = [f for f in os.listdir(user_dir) if f.startswith(prefix) and f.endswith('.json')]
    if not files:
        return None
    # Extract timestamp from filename using regex
    def extract_timestamp(f):
        m = re.search(r'_(\d{8}_\d{6})', f)
        return m.group(1) if m else ''
    files.sort(key=extract_timestamp, reverse=True)
    return os.path.join(user_dir, files[0])

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

def query_chatgpt(prompt):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are an expert email assistant."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 500,
        "temperature": 0.7
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    reply = response.json()["choices"][0]["message"]["content"]
    try:
        result = json.loads(reply)
    except Exception:
        result = {"subject": "Error: Could not parse response", "email": reply}
    return result

def save_improved_result(improved, validation_report, user_dir, user_id):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Add validation report to the improved result
    improved["validation"] = validation_report
    
    improved_filename = f"improved_{timestamp}_{user_id}.json"
    improved_path = os.path.join(user_dir, improved_filename)
    with open(improved_path, "w", encoding="utf-8") as f:
        json.dump(improved, f, indent=2, ensure_ascii=False)
    print(f"Saved improved result to {improved_path}")
    return improved_path

def main(user_id, max_attempts=2):
    user_dir = os.path.join("backend", "data", user_id)
    if not os.path.isdir(user_dir):
        print(f"User directory not found: {user_dir}")
        return
    
    # Use profile.json instead of tone file
    profile_path = os.path.join(user_dir, "profile.json")
    latest_context = get_latest_file(user_dir, "context_")
    
    if not os.path.exists(profile_path) or not latest_context:
        print("Could not find both profile and context files.")
        return
    
    print(f"Using context: {latest_context}\nUsing profile: {profile_path}")
    context = load_json(latest_context)
    profile = load_json(profile_path)
    
    # Extract recipients and content robustly
    def get_first(val, default=""):
        if isinstance(val, list):
            return val[0] if val else default
        elif isinstance(val, str):
            return val
        return default
    
    recipients = get_first(context.get("recipients", ""))
    content = context.get("content", "")
    
    # Initial email improvement
    feedback = None
    improved = None
    
    for attempt in range(max_attempts):
        # Build prompt with any feedback from previous attempts
        prompt = build_prompt(recipients, profile, content, feedback)
        
        # Query ChatGPT
        improved = query_chatgpt(prompt)
        
        # Validate if the style matches the user's profile
        validation_report = validate_style_match(profile, improved["email"])
        match_score = validation_report.get("overall_match", 0)
        
        print(f"Style match score: {match_score:.2f}")
        
        # If we have a good match or this is our last attempt, save and return
        if match_score >= 0.8 or attempt == max_attempts - 1:
            save_improved_result(improved, validation_report, user_dir, user_id)
            return improved
        
        # Otherwise, generate feedback for the next attempt
        feedback = improve_style_match(profile, improved["email"])
        print(f"Attempt {attempt+1}/{max_attempts} - Getting better match with feedback")
    
    # We should never reach here, but just in case
    if improved:
        save_improved_result(improved, validation_report, user_dir, user_id)
    
    return improved

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python improve_email.py <user_id>")
        exit(1)
    main(sys.argv[1]) 