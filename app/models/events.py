from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, validator, AnyHttpUrl
from uuid import UUID
import re

class PageViewPayload(BaseModel):
    """Payload structure for page_view events."""
    page_url: str = Field(..., description="URL of the page viewed", min_length=1, max_length=2048)
    
    @validator('page_url')
    def validate_page_url(cls, v):
        """Validate that page_url is a valid URL format."""
        if not v.strip():
            raise ValueError('page_url cannot be empty or whitespace only')
        
        # Basic URL pattern validation
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(v):
            raise ValueError('page_url must be a valid HTTP or HTTPS URL')
        
        return v.strip()

class PageViewEvent(BaseModel):
    """Model for page_view events with comprehensive validation."""
    event_id: UUID = Field(..., description="Unique identifier for the event (UUID v4)")
    user_id: str = Field(..., description="Unique identifier for the user", min_length=1, max_length=255)
    timestamp: datetime = Field(..., description="ISO 8601 timestamp in UTC")
    event_type: Literal["page_view"] = Field(..., description="Event type, must be 'page_view'")
    payload: Optional[PageViewPayload] = Field(None, description="Optional payload specific to page_view")
    
    @validator('user_id')
    def validate_user_id(cls, v):
        """Validate user_id is not empty and contains valid characters."""
        if not v.strip():
            raise ValueError('user_id cannot be empty or whitespace only')
        
        # Allow alphanumeric, underscore, hyphen, and dot
        if not re.match(r'^[a-zA-Z0-9_.-]+$', v.strip()):
            raise ValueError('user_id can only contain alphanumeric characters, underscore, hyphen, and dot')
        
        return v.strip()
    
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z' if v.tzinfo is None else v.isoformat()
        }

class EventResponse(BaseModel):
    """Response model for event submission."""
    success: bool = Field(..., description="Whether the event was processed successfully")
    message: str = Field(..., description="Response message")
    event_id: UUID = Field(..., description="ID of the processed event") 