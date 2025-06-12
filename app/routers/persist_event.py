from fastapi import APIRouter, HTTPException, status, Query
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.services.stream_persistent_event_service import stream_persistent_event_service
from app.models.common import PersistentEventStatusResponse, PersistentEventFilesResponse, PersistentEventFileInfo
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/persistent", tags=["persistent"])

@router.get("/status", response_model=PersistentEventStatusResponse)
async def get_persistant_event_status() -> PersistentEventStatusResponse:
    """
    Get current  status and statistics.
    
    Returns:
        Dict containing  system health and metrics
    """
    try:
        stats = await stream_persistent_event_service.get_stats()
        return PersistentEventStatusResponse(
            status="healthy" if stats.get("is_processor_running") else "stopped",
            stats=stats,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error getting  status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve status"
        )

@router.get("/files", response_model=PersistentEventFilesResponse)
async def list_persistent_event_files() -> PersistentEventFilesResponse:
    """
    List all files with their metadata.
    
    Returns:
        Dict containing file listing and stats
    """
    try:
        from pathlib import Path
        dir = Path(stream_persistent_event_service.PERSISTENT_DIR)
        
        if not dir.exists():
            return PersistentEventFilesResponse(files=[], total_files=0, total_size_mb=0)
        
        files_info = []
        total_size = 0
        
        for file_path in dir.rglob("*.jsonl"):
            stat = file_path.stat()
            total_size += stat.st_size
            
            # Count lines in file
            line_count = 0
            try:
                with open(file_path, 'r') as f:
                    line_count = sum(1 for _ in f)
            except Exception:
                line_count = -1  # Error reading file
            
            files_info.append(PersistentEventFileInfo(
                path=str(file_path.relative_to(dir)),
                size_mb=round(stat.st_size / (1024 * 1024), 2),
                modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                event_count=line_count
            ))
        
        # Sort by path
        files_info.sort(key=lambda x: x.path)
        
        return PersistentEventFilesResponse(
            files=files_info,
            total_files=len(files_info),
            total_size_mb=round(total_size / (1024 * 1024), 2)
        )
        
    except Exception as e:
        logger.error(f"Error listing  files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list  files"
        ) 