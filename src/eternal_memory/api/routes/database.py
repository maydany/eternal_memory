"""
Database API Routes

Endpoints for inspecting raw memory data.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import math

from eternal_memory.api.main import get_memory_system

router = APIRouter()

class MemoryItemResponse(BaseModel):
    id: str
    content: str
    category: str
    type: str
    importance: float
    recency: float
    mention_count: int
    is_active: bool
    last_accessed: datetime
    created_at: datetime

class PaginatedResponse(BaseModel):
    items: List[MemoryItemResponse]
    total: int
    page: int
    size: int
    pages: int

@router.get("/items", response_model=PaginatedResponse)
async def list_items(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100)
):
    """
    Get paginated list of memory items (Database Inspector).
    """
    try:
        system = await get_memory_system()
        
        offset = (page - 1) * size
        items = await system.repository.list_items(limit=size, offset=offset)
        total = await system.repository.count_items()
        
        # Calculate recency for each item using decay factor
        decay_factor = 0.995  # Per-hour decay
        now = datetime.now()
        
        return {
            "items": [
                {
                    "id": str(item.id),
                    "content": item.content,
                    "category": item.category_path,
                    "type": item.type.value if hasattr(item.type, "value") else str(item.type),
                    "importance": item.importance,
                    "recency": round(math.pow(decay_factor, max(0, (now - item.last_accessed.replace(tzinfo=None)).total_seconds() / 3600)), 3),
                    "mention_count": getattr(item, "mention_count", 1),
                    "is_active": getattr(item, "is_active", True),
                    "last_accessed": item.last_accessed,
                    "created_at": item.created_at,
                }
                for item in items
            ],
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset")
async def reset_database():
    """
    Completely wipe the database and markdown files.
    """
    try:
        system = await get_memory_system()
        await system.reset_system()
        return {"success": True, "message": "System reset successful. All data wiped."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
