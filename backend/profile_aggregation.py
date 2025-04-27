from collections import Counter, defaultdict
import numpy as np
from sklearn.cluster import KMeans
import json

def convert_categorical_to_numeric(value, category_map):
    """Convert categorical values to numeric for clustering"""
    return category_map.get(value, 0)

def convert_tone_axes_to_features(tone_axes, category_maps):
    """Convert a tone_axes dict to a numeric feature vector for clustering"""
    features = []
    
    # Add categorical features
    for axis, category_map in category_maps.items():
        if axis in tone_axes and tone_axes[axis] is not None:
            features.append(convert_categorical_to_numeric(tone_axes[axis], category_map))
        else:
            features.append(0)  # Default value for missing data
    
    # Add numeric features directly
    if "readability" in tone_axes and tone_axes["readability"] is not None:
        features.append(float(tone_axes["readability"]))
    else:
        features.append(0.0)
        
    return features

def cluster_tone_axes(tone_axes_list, n_clusters=3):
    """
    Cluster tone_axes data to identify different writing styles
    
    Args:
        tone_axes_list: List of tone_axes dictionaries
        n_clusters: Number of clusters to identify
        
    Returns:
        Dictionary with cluster information
    """
    if not tone_axes_list or len(tone_axes_list) < n_clusters:
        return {"clusters": []}
    
    # Define mappings for categorical values to numeric
    category_maps = {
        "formality": {"formal": 1, "informal": 0},
        "politeness": {"polite": 1, "blunt": 0},
        "certainty": {"certain": 1, "hedged": 0},
        "greeting": {"present": 1, "absent": 0},
        "closing": {"present": 1, "absent": 0},
        "emoji_usage": {"high": 2, "some": 1, "none": 0},
        "passive_voice": {"present": 1, "absent": 0},
        "emotion": {"positive": 2, "neutral": 1, "negative": 0, "frustrated": -1},
        "directness": {"direct": 1, "indirect": 0},
        "subjectivity_level": {"personal": 1, "objective": 0}
    }
    
    # Convert tone_axes to feature vectors
    features = [convert_tone_axes_to_features(ta, category_maps) for ta in tone_axes_list]
    
    # Adjust n_clusters if we don't have enough data
    actual_n_clusters = min(n_clusters, len(tone_axes_list) - 1)
    if actual_n_clusters <= 1:
        actual_n_clusters = 2  # Minimum 2 clusters
        
    # Perform clustering
    kmeans = KMeans(n_clusters=actual_n_clusters, random_state=42)
    cluster_labels = kmeans.fit_predict(features)
    
    # Analyze each cluster
    clusters = []
    for i in range(actual_n_clusters):
        # Get indices of tone_axes in this cluster
        cluster_indices = np.where(cluster_labels == i)[0]
        cluster_tone_axes = [tone_axes_list[idx] for idx in cluster_indices]
        
        # Calculate aggregate profile for this cluster
        cluster_profile = aggregate_tone_axes(cluster_tone_axes)
        
        # Add to results
        clusters.append({
            "id": i,
            "size": len(cluster_indices),
            "percentage": round(len(cluster_indices) / len(tone_axes_list) * 100, 1),
            "profile": cluster_profile
        })
    
    # Sort clusters by size (descending)
    clusters.sort(key=lambda x: x["size"], reverse=True)
    
    return {"clusters": clusters}

def aggregate_tone_axes(tone_axes_list):
    """Aggregate a list of tone_axes into a single profile"""
    if not tone_axes_list:
        return {}
        
    # For categorical axes, use majority vote; for readability, use average
    axes = tone_axes_list[0].keys()
    categorical_axes = [
        "formality", "politeness", "certainty", "greeting", "closing", 
        "emoji_usage", "passive_voice", "emotion", "directness", "subjectivity_level"
    ]
    numeric_axes = ["readability"]
    profile = {}
    
    for axis in axes:
        values = [ta[axis] for ta in tone_axes_list if axis in ta and ta[axis] is not None]
        if not values:
            profile[axis] = None
            continue
            
        if axis in categorical_axes:
            # Majority vote
            counter = Counter(values)
            profile[axis] = counter.most_common(1)[0][0]
            
            # Add distribution information
            total = sum(counter.values())
            distribution = {value: round(count/total * 100, 1) for value, count in counter.items()}
            profile[f"{axis}_distribution"] = distribution
            
        elif axis in numeric_axes:
            # Average, ignoring None
            nums = [v for v in values if isinstance(v, (int, float))]
            if nums:
                profile[axis] = round(sum(nums) / len(nums), 2)
                profile[f"{axis}_min"] = round(min(nums), 2)
                profile[f"{axis}_max"] = round(max(nums), 2)
            else:
                profile[axis] = None
        else:
            profile[axis] = values[0]
            
    return profile

def aggregate_user_profile(tone_axes_list):
    """
    Aggregate tone_axes into a comprehensive user profile with clusters
    
    Args:
        tone_axes_list: List of tone_axes dictionaries from analyzed emails
        
    Returns:
        Dictionary with aggregated profile and clusters
    """
    if not tone_axes_list:
        return {}
        
    # Create the main aggregated profile
    main_profile = aggregate_tone_axes(tone_axes_list)
    
    # Add clustering information
    clusters_info = cluster_tone_axes(tone_axes_list)
    
    # Combine both into the final profile
    profile = {
        "main_profile": main_profile,
        "style_clusters": clusters_info["clusters"],
        "email_count": len(tone_axes_list)
    }
    
    return profile 