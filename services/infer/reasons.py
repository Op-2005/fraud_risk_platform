"""Reason code generation for fraud risk decisions."""

from typing import Dict, Any, List


def generate_reasons(user_features: Dict[str, Any], risk_score: float) -> List[str]:
    """
    Generate explainable reason codes based on behavioral features.
    
    Args:
        user_features: Dictionary of features from Redis
        risk_score: Model risk score [0, 1]
        
    Returns:
        List of reason code strings (top 2-3)
    """
    reasons = []
    
    # Helper to safely get float value
    def get_float(key: str, default: float = 0.0) -> float:
        try:
            return float(user_features.get(key, default))
        except (ValueError, TypeError):
            return default
    
    # High velocity checks
    txns_5m = get_float('txns_last_5m')
    if txns_5m > 5:
        reasons.append('high_velocity_5m')
    
    txns_1h = get_float('txns_last_1h')
    if txns_1h > 20:
        reasons.append('high_velocity_1h')
    
    # Unusual amount
    avg_amount_1h = get_float('avg_amount_1h')
    amount_zscore = get_float('amount_zscore')
    if avg_amount_1h > 0 and amount_zscore > 3.0:
        reasons.append('unusual_amount')
    
    # Device churn
    device_churn = get_float('device_churn_24h')
    if device_churn > 2:
        reasons.append('high_device_churn')
    
    # IP changes
    ip_changes = get_float('ip_changes_24h')
    if ip_changes > 3:
        reasons.append('frequent_ip_changes')
    
    # Merchant velocity
    merchant_velocity = get_float('merchant_velocity_1h')
    if merchant_velocity > 5:
        reasons.append('high_merchant_velocity')
    
    # Return top 2-3 reasons (prioritize by severity)
    priority_order = [
        'high_velocity_5m',
        'unusual_amount',
        'high_device_churn',
        'frequent_ip_changes',
        'high_merchant_velocity',
        'high_velocity_1h'
    ]
    
    # Sort reasons by priority
    sorted_reasons = sorted(
        reasons,
        key=lambda r: priority_order.index(r) if r in priority_order else len(priority_order)
    )
    
    return sorted_reasons[:3] if sorted_reasons else ['no_significant_indicators']

