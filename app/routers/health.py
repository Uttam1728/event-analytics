from datetime import datetime

from fastapi import APIRouter

from app.models.common import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", response_model=HealthResponse)
async def health_check():
    """Detailed health check endpoint to verify the service is running."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        service="event-analytics"
    )
