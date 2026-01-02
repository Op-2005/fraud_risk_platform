"""Feature vector assembly for model inference."""

from typing import Dict, Any
import torch


def build_feature_vector(user_features: Dict[str, Any]) -> torch.Tensor:
    """
    Build feature vector matching training order.
    
    Expected order: V1, V2, ..., V28, Amount_normalized (29 features total)
    
    Args:
        user_features: Dictionary of features from Redis
        
    Returns:
        torch.Tensor of shape (1, 29) ready for model inference
    """
    feature_order = [
        'V1', 'V2', 'V3', 'V4', 'V5', 'V6', 'V7', 'V8', 'V9', 'V10',
        'V11', 'V12', 'V13', 'V14', 'V15', 'V16', 'V17', 'V18', 'V19', 'V20',
        'V21', 'V22', 'V23', 'V24', 'V25', 'V26', 'V27', 'V28',
        'Amount_normalized'
    ]
    
    vector = []
    for feature_name in feature_order:
        value = user_features.get(feature_name, 0.0)
        try:
            vector.append(float(value))
        except (ValueError, TypeError):
            vector.append(0.0)  # Default to 0 if conversion fails
    
    return torch.tensor([vector], dtype=torch.float32)

