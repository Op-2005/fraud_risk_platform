"""Pydantic schemas for transaction events."""

from pydantic import BaseModel, Field


class TransactionEvent(BaseModel):
    """Transaction event schema with all required fields for model inference."""
    
    # Event metadata
    event_id: str = Field(..., description="Unique event identifier")
    ts: str = Field(..., description="ISO 8601 timestamp")
    
    # User and transaction details
    user_id: str = Field(..., description="User identifier")
    amount: float = Field(..., ge=0, description="Transaction amount")
    currency: str = Field(..., description="Currency code (e.g., EUR, USD)")
    country: str = Field(..., description="Country code (e.g., FR, DE)")
    device_id: str = Field(..., description="Device identifier")
    ip: str = Field(..., description="IP address")
    merchant_id: str = Field(..., description="Merchant identifier")
    
    # Original model features (for inference)
    V1: float = Field(..., description="PCA feature V1")
    V2: float = Field(..., description="PCA feature V2")
    V3: float = Field(..., description="PCA feature V3")
    V4: float = Field(..., description="PCA feature V4")
    V5: float = Field(..., description="PCA feature V5")
    V6: float = Field(..., description="PCA feature V6")
    V7: float = Field(..., description="PCA feature V7")
    V8: float = Field(..., description="PCA feature V8")
    V9: float = Field(..., description="PCA feature V9")
    V10: float = Field(..., description="PCA feature V10")
    V11: float = Field(..., description="PCA feature V11")
    V12: float = Field(..., description="PCA feature V12")
    V13: float = Field(..., description="PCA feature V13")
    V14: float = Field(..., description="PCA feature V14")
    V15: float = Field(..., description="PCA feature V15")
    V16: float = Field(..., description="PCA feature V16")
    V17: float = Field(..., description="PCA feature V17")
    V18: float = Field(..., description="PCA feature V18")
    V19: float = Field(..., description="PCA feature V19")
    V20: float = Field(..., description="PCA feature V20")
    V21: float = Field(..., description="PCA feature V21")
    V22: float = Field(..., description="PCA feature V22")
    V23: float = Field(..., description="PCA feature V23")
    V24: float = Field(..., description="PCA feature V24")
    V25: float = Field(..., description="PCA feature V25")
    V26: float = Field(..., description="PCA feature V26")
    V27: float = Field(..., description="PCA feature V27")
    V28: float = Field(..., description="PCA feature V28")
    Amount_normalized: float = Field(..., description="Pre-normalized amount (log1p + StandardScaler)")

