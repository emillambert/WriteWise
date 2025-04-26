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

# Function to extract features from a single email
def extract_email_features(email_text):
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