"""Unit tests for ingest API."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from schemas import TransactionEvent
from s3_writer import ParquetWriter


def test_transaction_event_schema_valid():
    """Test valid transaction event schema."""
    event = TransactionEvent(
        event_id="evt_123",
        ts="2025-01-15T10:30:00Z",
        user_id="user_456",
        amount=99.99,
        currency="USD",
        country="US",
        device_id="dev_789",
        ip="192.168.1.1",
        merchant_id="merch_101",
        V1=-1.23,
        V2=0.45,
        V3=1.67,
        V4=-0.89,
        V5=2.34,
        V6=-1.56,
        V7=0.78,
        V8=-0.12,
        V9=1.90,
        V10=-2.34,
        V11=0.56,
        V12=-1.78,
        V13=3.45,
        V14=-0.67,
        V15=1.23,
        V16=-2.56,
        V17=0.89,
        V18=-1.34,
        V19=2.67,
        V20=-0.45,
        V21=1.12,
        V22=-3.45,
        V23=0.67,
        V24=-1.89,
        V25=2.34,
        V26=-0.56,
        V27=1.78,
        V28=-2.12,
        Amount_normalized=0.5
    )
    
    assert event.event_id == "evt_123"
    assert event.amount == 99.99


def test_transaction_event_schema_invalid_missing_field():
    """Test invalid transaction event with missing required field."""
    with pytest.raises(ValidationError):
        TransactionEvent(
            event_id="evt_123",
            ts="2025-01-15T10:30:00Z",
            user_id="user_456",
            amount=99.99,
            currency="USD",
            country="US",
            device_id="dev_789",
            ip="192.168.1.1",
            merchant_id="merch_101",
            # Missing V1-V28 and Amount_normalized
        )


def test_transaction_event_schema_invalid_negative_amount():
    """Test invalid transaction event with negative amount."""
    with pytest.raises(ValidationError):
        TransactionEvent(
            event_id="evt_123",
            ts="2025-01-15T10:30:00Z",
            user_id="user_456",
            amount=-10.0,  # Invalid: negative amount
            currency="USD",
            country="US",
            device_id="dev_789",
            ip="192.168.1.1",
            merchant_id="merch_101",
            V1=0.0, V2=0.0, V3=0.0, V4=0.0, V5=0.0,
            V6=0.0, V7=0.0, V8=0.0, V9=0.0, V10=0.0,
            V11=0.0, V12=0.0, V13=0.0, V14=0.0, V15=0.0,
            V16=0.0, V17=0.0, V18=0.0, V19=0.0, V20=0.0,
            V21=0.0, V22=0.0, V23=0.0, V24=0.0, V25=0.0,
            V26=0.0, V27=0.0, V28=0.0,
            Amount_normalized=0.0
        )


def test_parquet_writer_partition_path():
    """Test partition path generation."""
    writer = ParquetWriter(base_path="./test_data")
    
    # Test partition path generation logic
    test_event = {
        "ts": "2025-01-15T14:30:00Z",
        "event_id": "test",
        "user_id": "user1",
        "amount": 100.0,
        "currency": "USD",
        "country": "US",
        "device_id": "dev1",
        "ip": "1.2.3.4",
        "merchant_id": "m1",
        "V1": 0.0, "V2": 0.0, "V3": 0.0, "V4": 0.0, "V5": 0.0,
        "V6": 0.0, "V7": 0.0, "V8": 0.0, "V9": 0.0, "V10": 0.0,
        "V11": 0.0, "V12": 0.0, "V13": 0.0, "V14": 0.0, "V15": 0.0,
        "V16": 0.0, "V17": 0.0, "V18": 0.0, "V19": 0.0, "V20": 0.0,
        "V21": 0.0, "V22": 0.0, "V23": 0.0, "V24": 0.0, "V25": 0.0,
        "V26": 0.0, "V27": 0.0, "V28": 0.0,
        "Amount_normalized": 0.0
    }
    
    # Add event and flush
    import asyncio
    async def test_flush():
        await writer.add_event(test_event)
        count = await writer.flush()
        assert count == 1
        
        # Check file was created in correct partition
        partition_path = writer.base_path / "events" / "dt=2025-01-15" / "hour=14"
        assert partition_path.exists()
        parquet_files = list(partition_path.glob("*.parquet"))
        assert len(parquet_files) == 1
    
    asyncio.run(test_flush())
    
    # Cleanup
    import shutil
    shutil.rmtree("./test_data", ignore_errors=True)


def test_parquet_writer_buffer_size():
    """Test buffer size tracking."""
    writer = ParquetWriter()
    
    assert writer.get_buffer_size() == 0
    
    test_event = {
        "ts": "2025-01-15T14:30:00Z",
        "event_id": "test",
        "user_id": "user1",
        "amount": 100.0,
        "currency": "USD",
        "country": "US",
        "device_id": "dev1",
        "ip": "1.2.3.4",
        "merchant_id": "m1",
        "V1": 0.0, "V2": 0.0, "V3": 0.0, "V4": 0.0, "V5": 0.0,
        "V6": 0.0, "V7": 0.0, "V8": 0.0, "V9": 0.0, "V10": 0.0,
        "V11": 0.0, "V12": 0.0, "V13": 0.0, "V14": 0.0, "V15": 0.0,
        "V16": 0.0, "V17": 0.0, "V18": 0.0, "V19": 0.0, "V20": 0.0,
        "V21": 0.0, "V22": 0.0, "V23": 0.0, "V24": 0.0, "V25": 0.0,
        "V26": 0.0, "V27": 0.0, "V28": 0.0,
        "Amount_normalized": 0.0
    }
    
    import asyncio
    async def test_buffer():
        await writer.add_event(test_event)
        assert writer.get_buffer_size() == 1
        
        await writer.flush()
        assert writer.get_buffer_size() == 0
    
    asyncio.run(test_buffer())

