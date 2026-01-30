"""
Memory Item Data Model

Defines the core MemoryItem structure as specified in the eternal_memory_spec.md
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """Type of memory item."""
    FACT = "fact"
    PREFERENCE = "preference"
    EVENT = "event"
    PLAN = "plan"


class MemoryItem(BaseModel):
    """
    A single memory item representing an extracted fact from resources.
    
    This corresponds to the 2nd layer (Item) in the hierarchical structure:
    - Resource (raw data) → Item (extracted fact) → Category (semantic cluster)
    """
    
    id: UUID = Field(default_factory=uuid4)
    content: str = Field(..., description="The actual fact/memory content")
    category_path: str = Field(
        ..., 
        description="Path to category, e.g., 'knowledge/coding/python'"
    )
    type: MemoryType = Field(
        default=MemoryType.FACT,
        description="Type of memory: fact, preference, event, or plan"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for this memory (0.0-1.0)"
    )
    importance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Salience/importance score (0.0-1.0)"
    )
    source_resource_id: Optional[UUID] = Field(
        default=None,
        description="Reference to the original resource"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    last_accessed: datetime = Field(default_factory=datetime.now)
    
    class Config:
        use_enum_values = True


class Resource(BaseModel):
    """
    Raw data source - the 1st layer in the hierarchical structure.
    
    Stores original text, file references, or conversation logs
    to ensure traceability of extracted facts.
    """
    
    id: UUID = Field(default_factory=uuid4)
    uri: str = Field(..., description="File path or URL of the resource")
    modality: str = Field(
        ...,
        description="Type of resource: 'text', 'image', 'conversation'"
    )
    content: Optional[str] = Field(
        default=None,
        description="Full text content of the resource"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: dict = Field(
        default_factory=dict,
        description="Extra info (sender, app context, etc.)"
    )


class Category(BaseModel):
    """
    Semantic cluster - the 3rd layer in the hierarchical structure.
    
    Categories organize memory items by topic and maintain
    summary information for quick context retrieval.
    """
    
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., description="Category name")
    description: Optional[str] = Field(
        default=None,
        description="Description of what this category contains"
    )
    parent_id: Optional[UUID] = Field(
        default=None,
        description="Parent category for hierarchical organization"
    )
    summary: Optional[str] = Field(
        default=None,
        description="High-level summary of contained items"
    )
    path: str = Field(
        ...,
        description="Full path like 'knowledge/coding/python'"
    )
    last_accessed: datetime = Field(default_factory=datetime.now)
