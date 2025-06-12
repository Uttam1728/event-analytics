from fastapi import APIRouter, HTTPException, status, Query
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from app.services.redis_client import redis_client
from app.services.event_service import EventService
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/page_views_per_minute")
async def get_page_views_per_minute() -> List[Dict[str, Any]]:
    """
    Retrieve page view counts per minute for the last 5 minutes.
    
    Returns:
        List of dictionaries with minute_timestamp and count for each minute
        in the last 5 minutes. Timestamp represents the start of the minute.
    """
    try:
        await redis_client.connect()
        
        result = []
        
        # Get data for last 5 minutes
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(minutes=5)
        
        # Generate all minute keys in the range
        current_time = start_dt.replace(second=0, microsecond=0)
        while current_time <= end_dt:
            minute_key = EventService.get_minute_bucket_key(current_time)
            count = await redis_client.get_minute_bucket_count(minute_key)
            
            # Format timestamp as ISO string representing start of minute
            minute_timestamp = current_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            
            result.append({
                "minute_timestamp": minute_timestamp,
                "count": count
            })
            
            current_time += timedelta(minutes=1)
        
        logger.info(f"Retrieved page views per minute for last 5 minutes: {len(result)} entries")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving minute buckets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics data"
        )

@router.get("/minute-buckets/{minute_key}")
async def get_minute_bucket(minute_key: str) -> Dict[str, int]:
    """
    Get count for a specific minute bucket.
    
    Args:
        minute_key: The minute bucket key (format: page_view_YYYY-MM-DD_HH:MM)
        
    Returns:
        Dictionary with the bucket key and count
    """
    try:
        await redis_client.connect()
        count = await redis_client.get_minute_bucket_count(minute_key)
        
        logger.info(f"Retrieved count {count} for bucket {minute_key}")
        return {minute_key: count}
        
    except Exception as e:
        logger.error(f"Error retrieving minute bucket {minute_key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve bucket {minute_key}"
        ) 