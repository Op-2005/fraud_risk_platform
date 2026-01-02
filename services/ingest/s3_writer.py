"""Parquet file writer with buffering for local filesystem storage."""

import asyncio
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import pyarrow as pa
import pyarrow.parquet as pq


class ParquetWriter:
    """Writes buffered events to Parquet files in partitioned format."""
    
    def __init__(
        self,
        base_path: str = "./data/local-s3",
        flush_interval: int = 10,
        batch_size: int = 100
    ):
        """
        Initialize Parquet writer.
        
        Args:
            base_path: Base directory for Parquet files (local filesystem)
            flush_interval: Seconds between flushes
            batch_size: Maximum buffer size before flush
        """
        self.base_path = Path(base_path)
        self.flush_interval = flush_interval
        self.batch_size = batch_size
        self.buffer: List[Dict[str, Any]] = []
        self.buffer_lock = asyncio.Lock()
        
        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Define Parquet schema (all fields from TransactionEvent)
        self.schema = pa.schema([
            ("event_id", pa.string()),
            ("ts", pa.string()),
            ("user_id", pa.string()),
            ("amount", pa.float64()),
            ("currency", pa.string()),
            ("country", pa.string()),
            ("device_id", pa.string()),
            ("ip", pa.string()),
            ("merchant_id", pa.string()),
            ("V1", pa.float64()),
            ("V2", pa.float64()),
            ("V3", pa.float64()),
            ("V4", pa.float64()),
            ("V5", pa.float64()),
            ("V6", pa.float64()),
            ("V7", pa.float64()),
            ("V8", pa.float64()),
            ("V9", pa.float64()),
            ("V10", pa.float64()),
            ("V11", pa.float64()),
            ("V12", pa.float64()),
            ("V13", pa.float64()),
            ("V14", pa.float64()),
            ("V15", pa.float64()),
            ("V16", pa.float64()),
            ("V17", pa.float64()),
            ("V18", pa.float64()),
            ("V19", pa.float64()),
            ("V20", pa.float64()),
            ("V21", pa.float64()),
            ("V22", pa.float64()),
            ("V23", pa.float64()),
            ("V24", pa.float64()),
            ("V25", pa.float64()),
            ("V26", pa.float64()),
            ("V27", pa.float64()),
            ("V28", pa.float64()),
            ("Amount_normalized", pa.float64()),
        ])
    
    async def add_event(self, event: Dict[str, Any]) -> None:
        """Add event to buffer."""
        async with self.buffer_lock:
            self.buffer.append(event)
    
    async def flush(self) -> int:
        """
        Flush buffer to Parquet file.
        
        Returns:
            Number of events flushed
        """
        async with self.buffer_lock:
            if not self.buffer:
                return 0
            
            events_to_flush = self.buffer.copy()
            self.buffer.clear()
        
        if not events_to_flush:
            return 0
        
        # Generate partition path: dt=YYYY-MM-DD/hour=HH/
        # Use timestamp from first event in batch
        first_event = events_to_flush[0]
        event_ts = datetime.fromisoformat(first_event["ts"].replace("Z", "+00:00"))
        
        date_str = event_ts.strftime("%Y-%m-%d")
        hour_str = event_ts.strftime("%H")
        
        partition_path = self.base_path / "events" / f"dt={date_str}" / f"hour={hour_str}"
        partition_path.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with UUID
        filename = f"events-{uuid.uuid4().hex[:8]}.parquet"
        file_path = partition_path / filename
        
        # Convert to PyArrow table and write
        try:
            table = pa.Table.from_pylist(events_to_flush, schema=self.schema)
            pq.write_table(table, file_path, compression='snappy')
            return len(events_to_flush)
        except Exception as e:
            # On error, put events back in buffer (simplified - in production would use dead letter queue)
            async with self.buffer_lock:
                self.buffer = events_to_flush + self.buffer
            raise e
    
    async def start_background_flusher(self) -> None:
        """Start background task that flushes buffer periodically."""
        while True:
            await asyncio.sleep(self.flush_interval)
            
            # Check if we should flush (time-based or size-based)
            async with self.buffer_lock:
                should_flush = len(self.buffer) > 0
            
            if should_flush:
                try:
                    await self.flush()
                except Exception as e:
                    # Log error but continue (in production would use proper logging)
                    print(f"Error flushing buffer: {e}")
    
    def get_buffer_size(self) -> int:
        """Get current buffer size (thread-safe)."""
        return len(self.buffer)

