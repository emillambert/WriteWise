import os
import json
# import base64
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError
import spacy
from textblob import TextBlob
# from email import message_from_bytes
# from email.policy import default
from collections import Counter
import re
from bs4 import BeautifulSoup
try:
    from email_reply_parser import EmailReplyParser
except ImportError:
    EmailReplyParser = None  # Will raise in function if not installed
import textstat  # For readability scores
import emoji     # For emoji detection (if not installed, user must install)

# Load the SpaCy NLP model
nlp = spacy.load("en_core_web_sm")

# Function to load token from JSON file
# def load_token():
#     with open("auth_token.json", "r") as f:
#         data = json.load(f)
#         return data.get("token")

# Function to connect to Gmail API using the token
# def gmail_authenticate(token):
#     service = build('gmail', 'v1', credentials=None)
#     headers = {'Authorization': f'Bearer {token}'}
#     return service, headers

# Function to fetch emails using the provided token
# def fetch_emails(service, headers, max_results=100):
#     try:
#         # Get the list of messages
#         results = service.users().messages().list(userId='me', maxResults=max_results).execute(headers=headers)
#         messages = results.get('messages', [])
#         
#         email_texts = []
#         for msg in messages:
#             msg_id = msg['id']
#             message = service.users().messages().get(userId='me', id=msg_id, format='raw').execute(headers=headers)
#             msg_str = base64.urlsafe_b64decode(message['raw'].encode('ASCII'))
#             mime_msg = message_from_bytes(msg_str, policy=default)
#
#             # Extract text content from the email
#             email_content = ""
#             if mime_msg.is_multipart():
#                 for part in mime_msg.iter_parts():
#                     if part.get_content_type() == "text/plain":
#                         email_content += part.get_payload(decode=True).decode('utf-8', errors="ignore")
#             else:
#                 email_content = mime_msg.get_payload(decode=True).decode('utf-8', errors="ignore")
#             
#             email_texts.append(email_content)
#         
#         return email_texts
#     except HttpError as error:
#         print(f'An error occurred: {error}')
#         return None

# Main function to perform email analysis
# def main():
#     # Load the token from the JSON file
#     token = load_token()
#     if not token:
#         print("Token not found. Please ensure auth_data.json is available and contains the token.")
#         return
#
#     # Authenticate using the token and fetch emails
#     service, headers = gmail_authenticate(token)
#     emails = fetch_emails(service, headers, max_results=100)
#     email_features = []
#
#     if emails:
#         for email in emails:
#             features = extract_email_features(email)
#             email_features.append(features)
#
#         # Save extracted features to JSON file in the user-data directory
#         os.makedirs("user-data", exist_ok=True)
#         with open("user-data/email_features.json", "w") as f:
#             json.dump(email_features, f, indent=4)
#
#         print("Feature extraction complete. Features saved to user-data/email_features.json.")
#     else:
#         print("No emails found or error occurred.")

# --- Email Preprocessing Function ---
def preprocess_email(text):
    """
    Clean email text by:
    - Removing HTML tags
    - Removing quoted replies/forwards
    - Removing signatures
    """
    # 1. Remove HTML tags
    soup = BeautifulSoup(text, "html.parser")
    text = soup.get_text()

    # 2. Remove quoted text (replies/forwards)
    if EmailReplyParser is not None:
        text = EmailReplyParser.parse_reply(text)
    else:
        # Fallback: crude regex to remove lines starting with '>'
        text = re.sub(r"^>.*$", "", text, flags=re.MULTILINE)

    # 3. Remove common signature blocks (crude)
    # Look for common signature delimiters
    signature_patterns = [
        r"(?i)(-- ?\n.*$)",  # -- \n signature
        r"(?i)(^Sent from my .*$)",
        r"(?i)(^Best regards,.*$)",
        r"(?i)(^Kind regards,.*$)",
        r"(?i)(^Sincerely,.*$)",
        r"(?i)(^Cheers,.*$)",
        r"(?i)(^Thanks,.*$)",
        r"(?i)(^Thank you,.*$)",
        r"(?i)(^Met vriendelijke groet,.*$)",
        r"(?i)(^Mit freundlichen Grüßen,.*$)",
    ]
    for pat in signature_patterns:
        text = re.split(pat, text, maxsplit=1, flags=re.MULTILINE)[0]
    # Remove trailing whitespace
    text = text.strip()
    return text

# Function to extract features from a single email
def extract_email_features(email_text):
    # Clean the email first
    email_text = preprocess_email(email_text)
    doc = nlp(email_text)
    word_count = len([token.text for token in doc])
    sentence_count = len(list(doc.sents))
    common_words = Counter([token.text.lower() for token in doc if token.is_alpha])
    common_phrases = [chunk.text for chunk in doc.noun_chunks]
    pos_counts = Counter([token.pos_ for token in doc])

    blob = TextBlob(email_text)
    sentiment = blob.sentiment.polarity
    subjectivity = blob.sentiment.subjectivity
    exclamation_count = email_text.count("!")
    question_count = email_text.count("?")
    avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
    paragraph_count = email_text.count("\n\n")

    # --- New Features ---
    # Politeness markers
    politeness_markers = ["please", "thank you", "thanks", "kind regards", "best regards"]
    politeness_counts = {marker: email_text.lower().count(marker) for marker in politeness_markers}
    total_politeness = sum(politeness_counts.values())

    # Contraction counts
    contractions_pattern = re.compile(r"\b(?:[A-Za-z]+n['']t|[A-Za-z]+[''](?:m|re|ve|ll|d|s))\b")
    contraction_count = len(contractions_pattern.findall(email_text))

    # Pronoun usage ratios
    pronouns = {"I": 0, "we": 0, "you": 0, "they": 0}
    for token in doc:
        if token.text.lower() in ["i", "we", "you", "they"]:
            pronouns[token.text.lower().capitalize()] += 1
    total_pronouns = sum(pronouns.values())
    pronoun_ratios = {k: v / word_count if word_count else 0 for k, v in pronouns.items()}

    # Hedges and certainty markers
    hedges = ["maybe", "perhaps", "possibly", "I think", "I guess", "I feel", "I believe", "somewhat", "sort of", "kind of"]
    certainty = ["definitely", "certainly", "clearly", "obviously", "undoubtedly", "absolutely"]
    hedge_count = sum(email_text.lower().count(h) for h in hedges)
    certainty_count = sum(email_text.lower().count(c) for c in certainty)

    # Modal verbs
    modal_verbs = ["can", "could", "may", "might", "must", "shall", "should", "will", "would"]
    modal_count = sum(1 for token in doc if token.lemma_ in modal_verbs and token.pos_ == "VERB")

    # Passive voice detection (SpaCy)
    passive_count = sum(1 for token in doc if token.dep_ == "auxpass")

    # Greeting/closing detection
    greetings = ["dear", "hello", "hi", "greetings"]
    closings = ["regards", "sincerely", "best", "yours", "cheers", "thanks", "thank you"]
    greeting_found = any(email_text.lower().startswith(g) for g in greetings)
    closing_found = any(closing in email_text.lower()[-100:] for closing in closings)  # last 100 chars

    # Readability scores
    try:
        flesch = textstat.flesch_reading_ease(email_text)
        flesch_kincaid = textstat.flesch_kincaid_grade(email_text)
    except Exception:
        flesch = flesch_kincaid = None

    # Emoticon/emoji detection
    emoticon_pattern = re.compile(r"[:;=8][\-o\*']?([\)\]\(\[dDpP/\\:}{@|])")
    emoticon_count = len(emoticon_pattern.findall(email_text))
    emoji_count = len([c for c in email_text if c in emoji.EMOJI_DATA])

    # Paragraph and formatting style
    bullet_points = len(re.findall(r"^\s*[-*•]\s+", email_text, re.MULTILINE))
    line_breaks = email_text.count("\n")

    # --- Tone Mapping ---
    tone_axes = {
        "formality": "formal" if contraction_count < 2 and politeness_counts["please"] > 0 else "informal",
        "politeness": "polite" if total_politeness > 0 else "blunt",
        "certainty": "certain" if certainty_count > hedge_count else "hedged",
        "greeting": "present" if greeting_found else "absent",
        "closing": "present" if closing_found else "absent",
        "readability": flesch_kincaid,
        "emoji_usage": "high" if emoji_count > 0 or emoticon_count > 0 else "none",
        "passive_voice": "present" if passive_count > 0 else "absent",
    }

    features = {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "common_words": common_words.most_common(10),
        "common_phrases": common_phrases[:10],
        "pos_counts": dict(pos_counts),
        "sentiment": sentiment,
        "subjectivity": subjectivity,
        "exclamation_count": exclamation_count,
        "question_count": question_count,
        "avg_sentence_length": avg_sentence_length,
        "paragraph_count": paragraph_count,
        # New features
        "politeness_counts": politeness_counts,
        "contraction_count": contraction_count,
        "pronoun_ratios": pronoun_ratios,
        "hedge_count": hedge_count,
        "certainty_count": certainty_count,
        "modal_count": modal_count,
        "passive_count": passive_count,
        "greeting_found": greeting_found,
        "closing_found": closing_found,
        "flesch_reading_ease": flesch,
        "flesch_kincaid_grade": flesch_kincaid,
        "emoticon_count": emoticon_count,
        "emoji_count": emoji_count,
        "bullet_points": bullet_points,
        "line_breaks": line_breaks,
        # Tone axes
        "tone_axes": tone_axes,
    }
    return features

def analyze_data_file(filepath):
    """
    Loads a data file (as written by the server), extracts the email content,
    and runs extract_email_features on it.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    email_text = data.get('content', '')
    return extract_email_features(email_text)

# if __name__ == "__main__":
#     main()