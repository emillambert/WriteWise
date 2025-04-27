from collections import Counter, defaultdict
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler, OneHotEncoder
import json
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from kneed import KneeLocator
import matplotlib.pyplot as plt
import os
import statistics

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

def find_optimal_clusters(X, max_clusters=5):
    """
    Automatically determine the optimal number of clusters using the elbow method
    
    Args:
        X: Feature matrix for clustering
        max_clusters: Maximum number of clusters to consider
        
    Returns:
        Optimal number of clusters
    """
    # Ensure we have enough data points
    max_clusters = min(max_clusters, len(X) - 1)
    if max_clusters <= 1:
        return 2  # Default to at least 2 clusters
    
    distortions = []
    K_range = range(1, max_clusters + 1)
    
    for k in K_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(X)
        distortions.append(kmeans.inertia_)
    
    # Try to find the elbow point
    try:
        knee = KneeLocator(
            list(K_range), 
            distortions, 
            curve='convex', 
            direction='decreasing'
        )
        optimal_k = knee.elbow
        
        # If no clear elbow is found, default to 3
        if optimal_k is None:
            optimal_k = 3
    except Exception:
        optimal_k = 3  # Default to 3 clusters
    
    return optimal_k

def name_cluster(cluster_profile):
    """
    Name a cluster based on its characteristics
    
    Args:
        cluster_profile: Aggregated profile for the cluster
        
    Returns:
        Tuple of (name, description)
    """
    readability = cluster_profile.get('readability', 0)
    formality = cluster_profile.get('formality', 'unknown')
    emoji_usage = cluster_profile.get('emoji_usage', 'unknown')
    greeting = cluster_profile.get('greeting', 'unknown')
    passive_voice = cluster_profile.get('passive_voice', 'unknown')
    
    # Assign names based on distinctive characteristics
    if readability > 300:  # Ultra high readability
        return (
            "Ultra High Readability Informal",
            "Extremely high readability informal communication. No greetings, includes emojis, and uses neutral, objective language. Stands out for exceptionally high readability scores."
        )
    elif readability > 90:  # High readability
        return (
            "High Readability Informal",
            "Highly readable informal style with emoji usage. No greetings, avoids passive voice, and maintains an objective, neutral tone. Features higher than average readability."
        )
    elif formality == 'formal' or passive_voice == 'present':  # Formal business style
        return (
            "Formal Business Style",
            "Professional, structured writing with formal tone. Almost always includes greetings, often uses passive voice, and avoids emoji use. Suitable for business and official communications."
        )
    else:  # Default casual style
        return (
            "Informal Direct Style",
            "Casual, conversational tone without formalities. Typically doesn't use passive voice and may skip greetings. Prefers direct communication with normal readability."
        )

def extract_cluster_features(cluster_tone_axes):
    """
    Extract detailed linguistic features for a cluster
    
    Args:
        cluster_tone_axes: List of tone_axes dictionaries in the cluster
        
    Returns:
        Dictionary with extracted features
    """
    if not cluster_tone_axes:
        return {}
        
    # Create DataFrame for easier analysis
    df = pd.DataFrame(cluster_tone_axes)
    
    # Extract features
    features = {}
    
    # 1. Readability statistics
    if 'readability' in df.columns:
        readability_values = df['readability'].dropna()
        if not readability_values.empty:
            features['readability_stats'] = {
                'mean': float(readability_values.mean()),
                'median': float(readability_values.median()),
                'std_dev': float(readability_values.std()) if len(readability_values) > 1 else 0,
                'variance': float(readability_values.var()) if len(readability_values) > 1 else 0,
                'range': float(readability_values.max() - readability_values.min()) if len(readability_values) > 1 else 0,
                'quartiles': [
                    float(readability_values.quantile(0.25)),
                    float(readability_values.quantile(0.5)),
                    float(readability_values.quantile(0.75))
                ]
            }
            
    # 2. Formality patterns
    for col in ['formality', 'politeness', 'greeting', 'closing', 'emoji_usage', 'passive_voice']:
        if col in df.columns:
            col_counts = df[col].value_counts(normalize=True)
            if not col_counts.empty:
                features[f'{col}_pattern'] = {
                    'most_common': col_counts.index[0],
                    'frequency': float(col_counts.iloc[0]),
                    'distribution': {str(k): float(v) for k, v in col_counts.items()}
                }
    
    # 3. Emotion & directness correlations
    if all(col in df.columns for col in ['emotion', 'directness']):
        emotion_by_directness = pd.crosstab(
            df['emotion'], 
            df['directness'], 
            normalize='index'
        )
        
        emotion_directness = {}
        for emotion in emotion_by_directness.index:
            emotion_directness[emotion] = {
                direct: float(pct) 
                for direct, pct in emotion_by_directness.loc[emotion].items()
            }
        
        if emotion_directness:
            features['emotion_directness_correlation'] = emotion_directness
    
    # 4. Feature distinctiveness scores (how distinctive each feature is for this cluster)
    # This would require comparing to other clusters, which we can't do here.
    # Would need to be calculated after all clusters are processed.
    
    return features

def advanced_cluster_tone_axes(tone_axes_list):
    """
    Advanced clustering of tone_axes data with automatic cluster detection and naming
    
    Args:
        tone_axes_list: List of tone_axes dictionaries
        
    Returns:
        Dictionary with cluster information
    """
    if not tone_axes_list or len(tone_axes_list) < 2:
        return {"clusters": []}
    
    # Convert to pandas DataFrame for better handling of mixed data types
    df = pd.DataFrame(tone_axes_list)
    
    # Identify numeric and categorical columns
    numeric_features = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
    categorical_features = df.select_dtypes(include=['object']).columns.tolist()
    
    # Create preprocessing pipeline
    numeric_transformer = Pipeline(steps=[
        ('scaler', StandardScaler())
    ])
    
    categorical_transformer = Pipeline(steps=[
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, numeric_features),
            ('cat', categorical_transformer, categorical_features)
        ])
    
    # Fit and transform the data
    X_transformed = preprocessor.fit_transform(df)
    
    # Find optimal number of clusters
    n_clusters = find_optimal_clusters(X_transformed)
    
    # Perform clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(X_transformed)
    
    # Analyze each cluster
    clusters = []
    for i in range(n_clusters):
        # Get indices of tone_axes in this cluster
        cluster_indices = np.where(cluster_labels == i)[0]
        cluster_tone_axes = [tone_axes_list[idx] for idx in cluster_indices]
        
        # Calculate aggregate profile for this cluster
        cluster_profile = aggregate_tone_axes(cluster_tone_axes)
        
        # Name the cluster
        cluster_name, cluster_description = name_cluster(cluster_profile)
        
        # Extract detailed features for this cluster
        cluster_features = extract_cluster_features(cluster_tone_axes)
        
        # Add to results
        clusters.append({
            "id": i,
            "size": len(cluster_indices),
            "percentage": round(len(cluster_indices) / len(tone_axes_list) * 100, 1),
            "profile": cluster_profile,
            "name": cluster_name,
            "description": cluster_description,
            "features": cluster_features
        })
    
    # Sort clusters by size (descending)
    clusters.sort(key=lambda x: x["size"], reverse=True)
    
    return {"clusters": clusters}

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
    
    # Add advanced clustering information with automatic naming
    clusters_info = advanced_cluster_tone_axes(tone_axes_list)
    
    # Combine both into the final profile
    profile = {
        "main_profile": main_profile,
        "style_clusters": clusters_info["clusters"],
        "email_count": len(tone_axes_list)
    }
    
    return profile 