import json
from feature_extraction import extract_email_features
from tone_classification import classify_tone_axes

def validate_style_match(original_profile, generated_email):
    """
    Validates that a generated email matches the user's style profile
    
    Args:
        original_profile: User's aggregated writing profile
        generated_email: Text of the generated email
        
    Returns:
        dict: Validation report with match scores and suggestions
    """
    # Extract features and classify tone of the generated email
    try:
        features = extract_email_features(generated_email)
        tone_axes = classify_tone_axes(features)
    except Exception as e:
        return {
            "error": f"Error analyzing generated email: {str(e)}",
            "overall_match": 0.0
        }
    
    # Get the original profile's main characteristics
    main_profile = original_profile.get("main_profile", {})
    
    # Compare categorical axes
    categorical_axes = ["formality", "politeness", "certainty", "greeting", 
                        "closing", "emoji_usage", "passive_voice", 
                        "emotion", "directness", "subjectivity_level"]
    
    matches = []
    mismatches = []
    
    for axis in categorical_axes:
        if axis in main_profile and axis in tone_axes:
            if main_profile[axis] == tone_axes[axis]:
                matches.append(axis)
            else:
                mismatches.append({
                    "axis": axis,
                    "expected": main_profile[axis],
                    "actual": tone_axes[axis]
                })
    
    # Check readability level if available
    readability_match = True
    readability_diff = 0
    
    if "readability" in main_profile and "readability" in tone_axes and main_profile["readability"] is not None and tone_axes["readability"] is not None:
        original_readability = float(main_profile["readability"])
        generated_readability = float(tone_axes["readability"])
        readability_diff = abs(original_readability - generated_readability)
        
        # Consider it a match if within 2 grade levels
        readability_match = readability_diff <= 2.0
        
        if readability_match:
            matches.append("readability")
        else:
            mismatches.append({
                "axis": "readability",
                "expected": original_readability,
                "actual": generated_readability,
                "difference": readability_diff
            })
    
    # Calculate overall match score (0.0 to 1.0)
    total_axes = len(matches) + len(mismatches)
    match_score = len(matches) / total_axes if total_axes > 0 else 0.0
    
    # Generate suggestions for improvement
    suggestions = []
    
    for mismatch in mismatches:
        axis = mismatch["axis"]
        expected = mismatch["expected"]
        actual = mismatch["actual"]
        
        if axis == "formality":
            if expected == "formal" and actual == "informal":
                suggestions.append("Use more formal language with fewer contractions and more complex sentence structures")
            else:
                suggestions.append("Use more conversational language with contractions and simpler sentences")
        
        elif axis == "politeness":
            if expected == "polite" and actual == "blunt":
                suggestions.append("Add polite markers like 'please' and 'thank you'")
            else:
                suggestions.append("Be more direct and reduce excessive politeness markers")
        
        elif axis == "certainty":
            if expected == "hedged" and actual == "certain":
                suggestions.append("Use more hedging language (e.g., 'perhaps', 'might', 'I think')")
            else:
                suggestions.append("Be more definitive and reduce hedging language")
        
        elif axis == "greeting" or axis == "closing":
            if expected == "present" and actual == "absent":
                suggestions.append(f"Add a {axis}")
            else:
                suggestions.append(f"Remove the {axis}")
        
        elif axis == "emoji_usage":
            if expected == "high" or expected == "some":
                suggestions.append("Include some emojis where appropriate")
            else:
                suggestions.append("Remove emojis")
        
        elif axis == "emotion":
            suggestions.append(f"Adjust the emotional tone to be more {expected}")
        
        elif axis == "directness":
            if expected == "direct" and actual == "indirect":
                suggestions.append("Be more direct and straightforward")
            else:
                suggestions.append("Use more indirect language and soften requests")
        
        elif axis == "readability":
            expected_val = mismatch.get("expected", 0)
            actual_val = mismatch.get("actual", 0)
            if expected_val > actual_val:
                suggestions.append("Use more complex sentence structures and vocabulary")
            else:
                suggestions.append("Simplify sentence structures and vocabulary")
    
    # Prepare the validation report
    report = {
        "overall_match": round(match_score, 2),
        "matched_axes": matches,
        "mismatched_axes": mismatches,
        "suggestions": suggestions,
        "generated_tone_axes": tone_axes,
        "validation_date": None  # Can add timestamp here if needed
    }
    
    return report

def improve_style_match(original_profile, generated_email):
    """
    Suggests prompt revisions if the generated email doesn't match the user's style
    
    Args:
        original_profile: User's aggregated writing profile
        generated_email: Text of the generated email
        
    Returns:
        str: Revised prompt instructions focusing on mismatched style aspects
    """
    validation = validate_style_match(original_profile, generated_email)
    
    if validation.get("error"):
        return "Please try again with more attention to the user's writing style."
    
    match_score = validation.get("overall_match", 0)
    
    # If the match is good enough, no need for revision
    if match_score >= 0.8:
        return None
    
    # Create focused instructions based on mismatches
    instruction_parts = ["Please revise the email with specific attention to these style aspects:"]
    
    for suggestion in validation.get("suggestions", []):
        instruction_parts.append(f"- {suggestion}")
    
    return "\n".join(instruction_parts)

def main():
    """Test function"""
    # Sample test data
    with open("data/user/sample_profile.json", "r") as f:
        profile = json.load(f)
    
    sample_email = """
    Hi team,
    
    I wanted to follow up on our discussion from yesterday. I think we might need to reconsider 
    the timeline for the project. Let me know what you think.
    
    Thanks,
    User
    """
    
    report = validate_style_match(profile, sample_email)
    print(json.dumps(report, indent=2))
    
    suggestions = improve_style_match(profile, sample_email)
    if suggestions:
        print("\nSuggested improvements:")
        print(suggestions)
    else:
        print("\nNo style improvements needed.")

if __name__ == "__main__":
    main() 