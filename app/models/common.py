from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    service: str

class PersistentEventStatusResponse(BaseModel):
    status: str
    stats: dict
    timestamp: str

class PersistentEventFileInfo(BaseModel):
    path: str
    size_mb: float
    modified: str
    event_count: int

class PersistentEventFilesResponse(BaseModel):
    files: list[PersistentEventFileInfo]
    total_files: int
    total_size_mb: float

class PageViewsPerMinuteEntry(BaseModel):
    minute_timestamp: str
    count: int

class PageViewsPerMinuteResponse(BaseModel):
    page_views_per_minute: list[PageViewsPerMinuteEntry]

class MinuteBucketResponse(BaseModel):
    bucket_key: str
    count: int
