from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from contextlib import asynccontextmanager
import uvicorn
import logging

# Import routers
from app.routers import health, events, analytics, persist_event
from app.services.redis_client import redis_client
from app.services.stream_persistent_event_service import stream_persistent_event_service

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management for startup and shutdown events."""
    # Startup
    try:
        await redis_client.connect()
        logger.info("Application started with Redis connection")
    except Exception as e:
        logger.warning(f"Failed to connect to Redis on startup: {e}")
        # Don't fail startup if Redis is unavailable
    
    # Start persistent event saving processor in background
    import asyncio
    persistent_event_task = asyncio.create_task(stream_persistent_event_service.start_processor())
    logger.info("Started persistent event saving processor")
    
    yield
    
    # Shutdown
    try:
        await stream_persistent_event_service.stop_processor()
        persistent_event_task.cancel()
        logger.info("Stopped persistent event saving processor")
    except Exception as e:
        logger.warning(f"Error stopping persistent event saving processor: {e}")
        
    try:
        await redis_client.disconnect()
        logger.info("Application shutdown, Redis connection closed")
    except Exception as e:
        logger.warning(f"Error closing Redis connection: {e}")

# Create FastAPI app with metadata
app = FastAPI(
    title="Event Analytics API",
    description="A modular FastAPI application for collecting and processing page_view events with Redis minute bucket counting",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add global exception handler for validation errors
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Global exception handler for Pydantic validation errors."""
    return JSONResponse(
        status_code=400,
        content={
            "error": "Invalid request data", 
            "details": exc.errors()
        }
    )

# Include routers
app.include_router(health.router)
app.include_router(events.router)
app.include_router(analytics.router)
app.include_router(persist_event.router)

@app.get("/")
async def root():
    """Root endpoint that returns API information."""
    return {
        "message": "Welcome to Event Analytics API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
        "events": "/events",
        "analytics": "/analytics"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 