import logging
from uuid import UUID
from datetime import datetime
from app.models.events import PageViewEvent, EventResponse
from app.services.redis_client import redis_client
from app.services.stream_persistent_event_service import stream_persistent_event_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EventService:
    """Service class to handle event processing logic."""
    
    @staticmethod
    def get_minute_bucket_key(timestamp: datetime) -> str:
        """
        Generate minute bucket key from timestamp.
        Events between 10:00:00 and 10:00:59 belong to "10:00" bucket.
        
        Args:
            timestamp: Event timestamp
            
        Returns:
            Redis key for the minute bucket
        """
        # Format: page_view_YYYY-MM-DD_HH:MM
        print(f"page_view_{timestamp.strftime('%Y-%m-%d_%H:%M')}")
        return f"page_view_{timestamp.strftime('%Y-%m-%d_%H:%M')}"

    @staticmethod
    async def process_page_view_event(event: PageViewEvent) -> EventResponse:
        """
        Process a page_view event with Redis minute bucket counting.

        Args:
            event: The page_view event to process

        Returns:
            EventResponse indicating success or failure
        """
        try:
            # Log the received event
            logger.info(f"Processing page_view event: {event.event_id} for user: {event.user_id}")

            # Generate minute bucket key
            minute_key = EventService.get_minute_bucket_key(event.timestamp)

            # Ensure Redis connection
            try:
                await redis_client.connect()
            except Exception as redis_error:
                logger.warning(f"Redis connection failed: {redis_error}. Proceeding without minute bucket counting.")
                # Continue processing even if Redis fails

            # Update minute bucket count in Redis (non-blocking for fast response)
            try:
                count = await redis_client.increment_minute_bucket(minute_key)
                logger.info(f"Updated minute bucket {minute_key} to count: {count}")
            except Exception as redis_error:
                logger.warning(f"Failed to update minute bucket: {redis_error}. Event still processed.")
                # Don't fail the entire request if Redis operation fails

            # Queue event for (ultra-fast stream write)
            try:
                await stream_persistent_event_service.queue_event(event)
            except Exception as error:
                logger.warning(f"Failed to queue event : {error}. Event still processed.")
                # Don't fail the entire request if queueing fails

            # Log event details
            if event.payload:
                logger.info(f"Page URL: {event.payload.page_url}")

            logger.info(f"Event timestamp: {event.timestamp}")

            # Return success response quickly
            return EventResponse(
                success=True,
                message="Page view event processed successfully",
                event_id=event.event_id
            )

        except Exception as e:
            logger.error(f"Error processing event {event.event_id}: {str(e)}")
            return EventResponse(
                success=False,
                message=f"Failed to process event: {str(e)}",
                event_id=event.event_id
            )