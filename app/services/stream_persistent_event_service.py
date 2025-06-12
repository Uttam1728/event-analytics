import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from uuid import UUID

from app.models.events import PageViewEvent
from app.services.redis_client import redis_client

logger = logging.getLogger(__name__)

class StreamPersistentEventService:
    """High-performance  service using Redis Streams and batch file processing."""
    
    STREAM_NAME = "events_persistent_stream"
    CONSUMER_GROUP = "persistent_processors"
    CONSUMER_NAME = "persistent_consumer_1"
    PERSISTENT_DIR = "persistent_events"
    BATCH_SIZE = 1000  # Process 1000 events at once
    MAX_WAIT_TIME = 5000  # Max 5 seconds wait for batch
    
    def __init__(self):
        self.is_running = False
        self.dir = Path(self.PERSISTENT_DIR)
        self.dir.mkdir(exist_ok=True)
    
    async def queue_event(self, event: PageViewEvent) -> bool:
        """
        Queue event in Redis Stream for processing.
        This is extremely fast - just adds to stream.
        
        Args:
            event: event
            
        Returns:
            bool: Success status
        """
        try:
            await redis_client.connect()
            
            # Convert event to dict for JSON serialization
            # Redis streams only accept scalar values, so serialize payload to JSON string
            event_data = {
                "event_id": str(event.event_id),
                "user_id": event.user_id,
                "timestamp": event.timestamp.isoformat(),
                "event_type": event.event_type,
                "payload": json.dumps(event.payload.dict()) if event.payload else "",
                "queued_at": datetime.now().isoformat()
            }
            
            # Add to Redis Stream (very fast operation)
            message_id = await redis_client.redis.xadd(
                self.STREAM_NAME,
                event_data
            )
            
            logger.debug(f"Queued event {event.event_id}: {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to queue event : {e}")
            return False
    
    async def start_processor(self):
        """
        Start the background  processor.
        This runs continuously, processing batches of events.
        """
        if self.is_running:
            logger.warning(" processor already running")
            return
        
        self.is_running = True
        logger.info("Starting  processor...")
        
        try:
            await redis_client.connect()
            
            # Create consumer group if it doesn't exist
            try:
                await redis_client.redis.xgroup_create(
                    self.STREAM_NAME,
                    self.CONSUMER_GROUP,
                    id='0',
                    mkstream=True
                )
                logger.info(f"Created consumer group: {self.CONSUMER_GROUP}")
            except Exception as e:
                if "BUSYGROUP" not in str(e):
                    logger.error(f"Failed to create consumer group: {e}")
                    return
            
            # Start processing loop
            await self._process_stream_batches()
            
        except Exception as e:
            logger.error(f"processor failed: {e}")
        finally:
            self.is_running = False
            logger.info(" processor stopped")
    
    async def _process_stream_batches(self):
        """Main processing loop for batch file writing."""
        logger.info("Starting batch processing loop...")
        
        while self.is_running:
            try:
                # Read batch of messages from stream
                messages = await redis_client.redis.xreadgroup(
                    self.CONSUMER_GROUP,
                    self.CONSUMER_NAME,
                    {self.STREAM_NAME: '>'},
                    count=self.BATCH_SIZE,
                    block=self.MAX_WAIT_TIME
                )
                
                if messages:
                    # Process the batch
                    stream_messages = messages[0][1]  # [(stream_name, [(id, data), ...]), ...]
                    await self._write_batch_to_file(stream_messages)
                    
                    # Acknowledge processed messages
                    message_ids = [msg_id for msg_id, _ in stream_messages]
                    await redis_client.redis.xack(
                        self.STREAM_NAME,
                        self.CONSUMER_GROUP,
                        *message_ids
                    )
                    
                    logger.info(f"Processed batch of {len(stream_messages)} events")
                
            except Exception as e:
                logger.error(f"Error in batch processing: {e}")
                await asyncio.sleep(1)  # Brief pause on error
    
    async def _write_batch_to_file(self, messages: List[tuple]):
        """
        Write a batch of events to partitioned files.
        Files are organized by date/hour for easy management.
        """
        if not messages:
            return
        
        # Group messages by hour for partitioning
        hourly_batches = {}
        
        for message_id, data in messages:
            try:
                # Parse timestamp to determine file partition
                timestamp_str = data.get('timestamp', data.get('queued_at'))
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                
                # Create hourly partition key
                partition_key = timestamp.strftime('%Y-%m-%d-%H')
                
                if partition_key not in hourly_batches:
                    hourly_batches[partition_key] = []
                
                # Add metadata for tracking and deserialize payload
                payload = data.get("payload", "")
                if payload:
                    try:
                        payload = json.loads(payload)
                    except json.JSONDecodeError:
                        payload = None
                
                event_record = {
                    "stream_id": message_id,
                    "processed_at": datetime.now().isoformat(),
                    **{k: v for k, v in data.items() if k != "payload"},
                    "payload": payload
                }
                
                hourly_batches[partition_key].append(event_record)
                
            except Exception as e:
                logger.error(f"Error processing message {message_id}: {e}")
        
        # Write each hourly batch to its own file
        for partition_key, events in hourly_batches.items():
            await self._write_events_to_partition(partition_key, events)
    
    async def _write_events_to_partition(self, partition_key: str, events: List[Dict]):
        """Write events to a specific partition file."""
        try:
            # Create partition directory structure: persistent_events/2024/01/15/
            year, month, day, hour = partition_key.split('-')
            partition_dir = self.dir / year / month / day
            partition_dir.mkdir(parents=True, exist_ok=True)
            
            # File name: events_2024-01-15-14.jsonl
            filename = f"events_{partition_key}.jsonl"
            file_path = partition_dir / filename
            
            # Append to file (JSONL format - one JSON object per line)
            with open(file_path, 'a', encoding='utf-8') as f:
                for event in events:
                    f.write(json.dumps(event, default=str) + '\n')
            
            logger.debug(f"Wrote {len(events)} events to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to write partition {partition_key}: {e}")
    
    async def stop_processor(self):
        """Stop the  processor gracefully."""
        logger.info("Stopping  processor...")
        self.is_running = False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the  system."""
        try:
            await redis_client.connect()
            
            # Stream info
            stream_info = await redis_client.redis.xinfo_stream(self.STREAM_NAME)
            
            # Consumer group info
            groups_info = await redis_client.redis.xinfo_groups(self.STREAM_NAME)
            
            # File system stats
            total_files = 0
            total_size = 0
            
            for file_path in self.dir.rglob("*.jsonl"):
                total_files += 1
                total_size += file_path.stat().st_size
            
            return {
                "stream_length": stream_info.get('length', 0),
                "pending_messages": sum(g.get('pending', 0) for g in groups_info),
                "files_count": total_files,
                "files_size_mb": round(total_size / (1024 * 1024), 2),
                "is_processor_running": self.is_running
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}

# Global instance
stream_persistent_event_service = StreamPersistentEventService()