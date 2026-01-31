"""
Metrics and monitoring API endpoints.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from eternal_memory.monitoring import get_monitor

router = APIRouter()


@router.get("/summary")
async def get_metrics_summary() -> Dict[str, Any]:
    """Get aggregated metrics summary."""
    monitor = get_monitor()
    return monitor.get_summary()


@router.get("/recent")
async def get_recent_metrics(limit: Optional[int] = 50) -> List[Dict[str, Any]]:
    """Get recent metrics from memory."""
    monitor = get_monitor()
    return monitor.get_recent_metrics(limit=limit)


@router.get("/logs")
async def list_log_files() -> Dict[str, List[str]]:
    """List available log files."""
    monitor = get_monitor()
    return {"files": monitor.get_log_files()}


@router.get("/logs/{filename}")
async def get_log_file(filename: str, limit: Optional[int] = 100) -> List[Dict[str, Any]]:
    """Get metrics from a specific log file."""
    monitor = get_monitor()
    
    # Security: validate filename
    if "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    try:
        return monitor.read_log_file(filename, limit=limit)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Log file not found")
