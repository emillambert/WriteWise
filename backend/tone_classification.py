def classify_tone_axes(features):
    """
    Classify email tone along various axes based on feature set.
    
    Args:
        features (dict): Dictionary of features extracted from an email
        
    Returns:
        dict: Dictionary of tone classifications along different axes
        
    Raises:
        ValueError: If features is not a dictionary or is missing required keys
    """
    try:
        if not isinstance(features, dict):
            raise ValueError(f"Features must be a dictionary, got {type(features).__name__}")
            
        # Get features with defaults to avoid KeyErrors
        contraction_count = features.get("contraction_count", 0)
        politeness_counts = features.get("politeness_counts", {})
        total_politeness = sum(politeness_counts.values())
        hedge_count = features.get("hedge_count", 0)
        certainty_count = features.get("certainty_count", 0)
        greeting_found = features.get("greeting_found", False)
        closing_found = features.get("closing_found", False)
        flesch_kincaid = features.get("flesch_kincaid_grade", None)
        avg_sentence_length = features.get("avg_sentence_length", 0)
        emoji_count = features.get("emoji_count", 0)
        emoticon_count = features.get("emoticon_count", 0)
        passive_count = features.get("passive_count", 0)
        sentiment = features.get("sentiment", 0)
        subjectivity = features.get("subjectivity", 0.5)
        exclamation_count = features.get("exclamation_count", 0)
        pronoun_ratios = features.get("pronoun_ratios", {})
        modal_count = features.get("modal_count", 0)

        # Create emotion category from sentiment
        sentiment_tone = "positive" if sentiment > 0.2 else "negative" if sentiment < -0.2 else "neutral"
        
        # Check for frustration markers
        frustration_markers = exclamation_count > 1 and sentiment < -0.1
        
        # Improved formality detection with multiple signals
        formality_score = 0
        formality_score += 1 if contraction_count < 2 else -1
        formality_score += 1 if avg_sentence_length > 15 else -1
        formality_score += 1 if flesch_kincaid and flesch_kincaid > 10 else -1
        formality_score += 1 if passive_count > 0 else -1
        formality_score += 1 if greeting_found and closing_found else -1
        formality_score -= 1 if emoji_count > 0 or emoticon_count > 0 else 0
        
        # Measure directness based on pronoun usage and modal verbs
        you_ratio = pronoun_ratios.get("you", 0)
        directness_score = 1 if you_ratio > 0.05 else 0
        directness_score -= 1 if modal_count > 3 else 0
        directness_score -= 1 if hedge_count > 1 else 0

        tone_axes = {
            "formality": "formal" if formality_score > 0 else "informal",
            "politeness": "polite" if total_politeness > 0 else "blunt",
            "certainty": "certain" if certainty_count > hedge_count else "hedged",
            "greeting": "present" if greeting_found else "absent",
            "closing": "present" if closing_found else "absent",
            "readability": flesch_kincaid,
            "emoji_usage": "high" if emoji_count > 3 else "some" if emoji_count > 0 or emoticon_count > 0 else "none",
            "passive_voice": "present" if passive_count > 0 else "absent",
            "emotion": "frustrated" if frustration_markers else sentiment_tone,
            "directness": "direct" if directness_score > 0 else "indirect",
            "subjectivity_level": "personal" if subjectivity > 0.5 else "objective"
        }
        return tone_axes
    except Exception as e:
        # Provide context when encountering unexpected errors
        raise ValueError(f"Error in tone classification: {str(e)}") from e 