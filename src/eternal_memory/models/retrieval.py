"""
Retrieval Result Data Model

Defines the structure returned by the retrieve() method.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from eternal_memory.models.memory_item import MemoryItem


class RetrievalResult(BaseModel):
    """
    Result of a memory retrieval operation.
    
    Contains matching memory items along with related context
    and proactive suggestions.
    """
    
    items: List[MemoryItem] = Field(
        default_factory=list,
        description="List of retrieved memory items"
    )
    related_categories: List[str] = Field(
        default_factory=list,
        description="Paths of related categories that were searched"
    )
    suggested_context: str = Field(
        default="",
        description="Proactive suggestion string for system prompt injection"
    )
    query_evolved: Optional[str] = Field(
        default=None,
        description="If query was evolved/rewritten, this contains the new query"
    )
    retrieval_mode: str = Field(
        default="fast",
        description="Mode used for retrieval: 'fast' or 'deep'"
    )
    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall confidence in the retrieval results"
    )
