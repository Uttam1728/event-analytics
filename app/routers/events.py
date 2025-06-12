from fastapi import APIRouter, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from app.models.events import PageViewEvent, EventResponse
import logging

from app.services.event_service import EventService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["events"])

@router.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def ingest_event(event: PageViewEvent, background_tasks: BackgroundTasks):
    """
    HTTP POST endpoint to receive new page_view events.
    
    Accepts JSON body conforming to the Event Structure and responds immediately.
    Event processing (Redis operations, detailed logging) happens in the background.
    Gracefully handles invalid event structures with 400 Bad Request.
    
    Args:
        event: The page_view event data conforming to Event Structure
        background_tasks: FastAPI background tasks for async processing
        
    Returns:
        EventResponse: Immediate confirmation of successful event acceptance
        
    Raises:
        HTTPException: 400 for validation errors
    """
    try:
        # Validate the event (this is fast and happens synchronously)
        # The Pydantic model validation already happened during request parsing
        
        # Queue the event for background processing
        background_tasks.add_task(
            EventService.process_page_view_event,
            event
        )
        
        # Return immediate response to client
        logger.info(f"Event {event.event_id} accepted and queued for background processing")
        
        return EventResponse(
            success=True,
            message="Page view event accepted and queued for processing",
            event_id=event.event_id
        )
        
    except ValidationError as e:
        # Handle Pydantic validation errors with 400 Bad Request
        logger.warning(f"Invalid event structure: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid event structure",
                "details": e.errors()
            }
        )
    except Exception as e:
        # Handle unexpected errors during event acceptance
        logger.error(f"Unexpected error accepting event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while accepting event"
        )

 