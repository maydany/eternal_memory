"""
Timeline API Routes

Endpoints for viewing hierarchical memory summaries (Daily, Weekly, Monthly).
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

router = APIRouter()


class TimelineEntry(BaseModel):
    """A timeline entry (reflection or summary)."""
    id: str
    type: str  # daily_reflection, weekly_summary, monthly_summary
    content: str
    date_label: str  # e.g., "2026-01-31", "2026-W05", "2026-01"
    created_at: str
    memory_count: Optional[int] = None


class TimelineResponse(BaseModel):
    """Response containing timeline entries."""
    entries: List[TimelineEntry]
    total: int


# Dependency to get the memory system
async def get_memory_system():
    from eternal_memory.api.main import get_system
    return get_system()


@router.get("/", response_model=TimelineResponse)
async def get_timeline(
    type: Optional[str] = Query(None, description="Filter by type: daily, weekly, monthly"),
    days: int = Query(30, description="Number of days to look back"),
    limit: int = Query(50, description="Maximum entries to return"),
    system=Depends(get_memory_system),
):
    """
    Get timeline entries (reflections and summaries).
    
    Returns a list of Daily Reflections, Weekly Summaries, and Monthly Summaries
    within the specified time range.
    """
    since = datetime.now() - timedelta(days=days)
    entries = []
    
    # Map type filter to category prefix
    type_map = {
        "daily": "timeline/daily",
        "weekly": "timeline/weekly",
        "monthly": "timeline/monthly",
    }
    
    if type and type in type_map:
        # Filter by specific type
        items = await system.repository.get_reflections_by_type(
            reflection_type=type_map[type],
            since=since,
            limit=limit,
        )
    else:
        # Get all types
        all_items = []
        for prefix in type_map.values():
            items = await system.repository.get_reflections_by_type(
                reflection_type=prefix,
                since=since,
                limit=limit // 3,
            )
            all_items.extend(items)
        
        # Sort by creation date
        items = sorted(all_items, key=lambda x: x.created_at, reverse=True)[:limit]
    
    # Convert to response format
    for item in items:
        # Extract type from category path
        entry_type = "daily_reflection"
        if "weekly" in item.category_path:
            entry_type = "weekly_summary"
        elif "monthly" in item.category_path:
            entry_type = "monthly_summary"
        
        # Extract date label from content (first line usually has it)
        first_line = item.content.split("\n")[0] if item.content else ""
        date_label = ""
        if "[Daily Reflection -" in first_line:
            date_label = first_line.split("-")[1].strip().rstrip("]")
        elif "[Weekly Summary -" in first_line:
            date_label = first_line.split("-")[1].strip().rstrip("]")
        elif "[Monthly Summary -" in first_line:
            date_label = first_line.split("-")[1].strip().rstrip("]")
        else:
            date_label = item.created_at.strftime("%Y-%m-%d") if item.created_at else ""
        
        entries.append(TimelineEntry(
            id=str(item.id),
            type=entry_type,
            content=item.content,
            date_label=date_label,
            created_at=item.created_at.isoformat() if item.created_at else "",
            memory_count=item.mention_count,
        ))
    
    return TimelineResponse(
        entries=entries,
        total=len(entries),
    )


@router.get("/stats")
async def get_timeline_stats(
    system=Depends(get_memory_system),
):
    """
    Get statistics about timeline entries.
    """
    since_30d = datetime.now() - timedelta(days=30)
    since_90d = datetime.now() - timedelta(days=90)
    since_365d = datetime.now() - timedelta(days=365)
    
    daily_30d = await system.repository.get_reflections_by_type("timeline/daily", since_30d, 100)
    weekly_90d = await system.repository.get_reflections_by_type("timeline/weekly", since_90d, 20)
    monthly_365d = await system.repository.get_reflections_by_type("timeline/monthly", since_365d, 12)
    
    return {
        "daily_count_30d": len(daily_30d),
        "weekly_count_90d": len(weekly_90d),
        "monthly_count_365d": len(monthly_365d),
        "latest_daily": daily_30d[0].created_at.isoformat() if daily_30d else None,
        "latest_weekly": weekly_90d[0].created_at.isoformat() if weekly_90d else None,
        "latest_monthly": monthly_365d[0].created_at.isoformat() if monthly_365d else None,
    }
