import spacy
from textblob import TextBlob
from collections import Counter
import re
import textstat
import emoji
from preprocessing import preprocess_email

nlp = spacy.load("en_core_web_sm")

# Lexicons for emotional tone detection
POSITIVE_WORDS = ["happy", "great", "excellent", "good", "pleased", "delighted", "excited", 
                 "wonderful", "fantastic", "appreciate", "thrilled", "glad", "grateful"]
NEGATIVE_WORDS = ["disappointed", "unfortunate", "sorry", "unhappy", "bad", "trouble", 
                 "problem", "issue", "concerned", "worried", "regret", "failed", "frustrated"]
FRUSTRATION_WORDS = ["disappointed", "frustrated", "annoying", "waste", "ridiculous", 
                    "unacceptable", "failure", "terrible", "awful", "absurd", "incompetent"]

def extract_email_features(email_text):
    # Input validation
    if not isinstance(email_text, str):
        raise ValueError(f"Input to extract_email_features must be a string, got {type(email_text).__name__}")
    if not email_text.strip():
        raise ValueError("Input to extract_email_features is an empty string.")
    
    try:
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

        politeness_markers = ["please", "thank you", "thanks", "kind regards", "best regards"]
        politeness_counts = {marker: email_text.lower().count(marker) for marker in politeness_markers}
        total_politeness = sum(politeness_counts.values())

        contractions_pattern = re.compile(r"\b(?:[A-Za-z]+n['']t|[A-Za-z]+[''](?:m|re|ve|ll|d|s))\b")
        contraction_count = len(contractions_pattern.findall(email_text))

        # Fix the pronoun counting logic
        pronouns = {"I": 0, "we": 0, "you": 0, "they": 0}
        for token in doc:
            token_lower = token.text.lower()
            if token_lower == "i":
                pronouns["I"] += 1
            elif token_lower in pronouns:
                pronouns[token_lower] += 1
        
        total_pronouns = sum(pronouns.values())
        pronoun_ratios = {k: v / word_count if word_count else 0 for k, v in pronouns.items()}

        hedges = ["maybe", "perhaps", "possibly", "I think", "I guess", "I feel", "I believe", "somewhat", "sort of", "kind of"]
        certainty = ["definitely", "certainly", "clearly", "obviously", "undoubtedly", "absolutely"]
        hedge_count = sum(email_text.lower().count(h) for h in hedges)
        certainty_count = sum(email_text.lower().count(c) for c in certainty)

        modal_verbs = ["can", "could", "may", "might", "must", "shall", "should", "will", "would"]
        modal_count = sum(1 for token in doc if token.lemma_ in modal_verbs and token.pos_ == "VERB")

        passive_count = sum(1 for token in doc if token.dep_ == "auxpass")

        greetings = ["dear", "hello", "hi", "greetings"]
        closings = ["regards", "sincerely", "best", "yours", "cheers", "thanks", "thank you"]
        greeting_found = any(email_text.lower().startswith(g) for g in greetings)
        closing_found = any(closing in email_text.lower()[-100:] for closing in closings)

        try:
            flesch = textstat.flesch_reading_ease(email_text)
            flesch_kincaid = textstat.flesch_kincaid_grade(email_text)
        except Exception:
            flesch = flesch_kincaid = None

        emoticon_pattern = re.compile(r"[:;=8][\-o\*']?([\)\]\(\[dDpP/\\:}{@|])")
        emoticon_count = len(emoticon_pattern.findall(email_text))
        emoji_count = len([c for c in email_text if c in emoji.EMOJI_DATA])

        bullet_points = len(re.findall(r"^\s*[-*•]\s+", email_text, re.MULTILINE))
        line_breaks = email_text.count("\n")
        
        # Enhanced emotion detection
        email_lower = email_text.lower()
        positive_word_count = sum(email_lower.count(word) for word in POSITIVE_WORDS)
        negative_word_count = sum(email_lower.count(word) for word in NEGATIVE_WORDS)
        frustration_word_count = sum(email_lower.count(word) for word in FRUSTRATION_WORDS)
        
        # Calculate a frustration score
        frustration_score = (frustration_word_count * 2) + (exclamation_count * 0.5) 
        frustration_score += -sentiment * 2 if sentiment < 0 else 0  # Negative sentiment increases score
        
        # Calculate emotional tone
        if frustration_score > 3:
            emotional_tone = "frustrated"
        elif sentiment > 0.2 and positive_word_count > 0:
            emotional_tone = "positive"
        elif sentiment < -0.2 and negative_word_count > 0:
            emotional_tone = "negative"
        else:
            emotional_tone = "neutral"

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
            "positive_word_count": positive_word_count,
            "negative_word_count": negative_word_count,
            "frustration_word_count": frustration_word_count,
            "frustration_score": frustration_score,
            "emotional_tone": emotional_tone
        }
        return features
    except Exception as e:
        # Wrap any unexpected error with context
        raise ValueError(f"Error in feature extraction: {str(e)}") from e