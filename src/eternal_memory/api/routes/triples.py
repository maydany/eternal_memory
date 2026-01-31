"""
Triples API Routes

REST endpoints for managing semantic triples (Subject-Predicate-Object memory).
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from eternal_memory.api.main import get_memory_system

router = APIRouter(prefix="/api/triples", tags=["triples"])


# Response Models
class TripleResponse(BaseModel):
    id: str
    memory_item_id: Optional[str]
    subject: str
    predicate: str
    object: str
    context: Optional[str]
    importance: float
    confidence: float
    is_active: bool
    created_at: datetime
    last_accessed: datetime


class TriplesListResponse(BaseModel):
    items: list[TripleResponse]
    total: int
    page: int
    page_size: int


@router.get("", response_model=TriplesListResponse)
async def list_triples(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    active_only: bool = Query(False),
):
    """List all semantic triples with pagination."""
    try:
        system = await get_memory_system()
        repository = system.repository
        
        offset = (page - 1) * page_size
        triples = await repository.list_triples(
            limit=page_size,
            offset=offset,
            active_only=active_only,
        )
        total = await repository.count_triples(active_only=active_only)
        
        return {
            "items": [
                {
                    "id": str(t.id),
                    "memory_item_id": str(t.memory_item_id) if t.memory_item_id else None,
                    "subject": t.subject,
                    "predicate": t.predicate,
                    "object": t.object,
                    "context": t.context,
                    "importance": t.importance,
                    "confidence": t.confidence,
                    "is_active": t.is_active,
                    "created_at": t.created_at,
                    "last_accessed": t.last_accessed,
                }
                for t in triples
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_triples_by_entity(
    entity: str = Query(..., description="Entity name to search for"),
    search_subject: bool = Query(True),
    search_object: bool = Query(True),
    active_only: bool = Query(True),
    limit: int = Query(20, ge=1, le=100),
):
    """Search triples by subject or object entity name."""
    try:
        system = await get_memory_system()
        repository = system.repository
        
        triples = await repository.search_triples_by_entity(
            entity=entity,
            search_subject=search_subject,
            search_object=search_object,
            active_only=active_only,
            limit=limit,
        )
        
        return {
            "items": [
                {
                    "id": str(t.id),
                    "subject": t.subject,
                    "predicate": t.predicate,
                    "object": t.object,
                    "context": t.context,
                    "importance": t.importance,
                    "is_active": t.is_active,
                }
                for t in triples
            ],
            "count": len(triples),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{triple_id}")
async def get_triple(triple_id: str):
    """Get a single triple by ID."""
    try:
        system = await get_memory_system()
        repository = system.repository
        
        # Note: Would need to add get_triple method to repository
        # For now, search through list
        triples = await repository.list_triples(limit=1000, active_only=False)
        for t in triples:
            if str(t.id) == triple_id:
                return {
                    "id": str(t.id),
                    "memory_item_id": str(t.memory_item_id) if t.memory_item_id else None,
                    "subject": t.subject,
                    "predicate": t.predicate,
                    "object": t.object,
                    "context": t.context,
                    "importance": t.importance,
                    "confidence": t.confidence,
                    "is_active": t.is_active,
                    "created_at": t.created_at,
                    "last_accessed": t.last_accessed,
                }
        
        raise HTTPException(status_code=404, detail="Triple not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/{memory_item_id}")
async def get_triples_for_memory(
    memory_item_id: str,
    active_only: bool = Query(False),
):
    """Get all triples associated with a memory item."""
    try:
        system = await get_memory_system()
        repository = system.repository
        
        triples = await repository.get_triples_for_memory_item(
            memory_item_id=UUID(memory_item_id),
            active_only=active_only,
        )
        
        return {
            "items": [
                {
                    "id": str(t.id),
                    "subject": t.subject,
                    "predicate": t.predicate,
                    "object": t.object,
                    "context": t.context,
                    "importance": t.importance,
                    "is_active": t.is_active,
                }
                for t in triples
            ],
            "count": len(triples),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
