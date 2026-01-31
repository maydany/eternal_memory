"""
Semantic Triple Data Model

Implements Subject-Predicate-Object memory structure for entity-level updates.
Reference: LangMem (LangChain, 2024)
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class SemanticTriple(BaseModel):
    """
    Subject-Predicate-Object semantic memory unit.
    
    Enables entity-level memory updates by decomposing facts into atomic triples.
    Example: "User likes apples" → Triple(User, likes, apples)
    """
    
    id: UUID = Field(default_factory=uuid4)
    memory_item_id: Optional[UUID] = Field(
        default=None,
        description="Reference to originating MemoryItem"
    )
    
    # Triple components
    subject: str = Field(..., description="Entity performing/being described: 'User', 'Alice'")
    predicate: str = Field(..., description="Relationship or action: 'likes', 'knows', 'is_born_on'")
    object: str = Field(..., description="Target entity: 'apples', 'Python', '1990-01-01'")
    context: Optional[str] = Field(
        default=None,
        description="Optional context: 'since 2020', 'very much'"
    )
    
    # Metadata
    importance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Importance score (0.0-1.0)"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0-1.0)"
    )
    is_active: bool = Field(
        default=True,
        description="Whether this triple is active (not superseded)"
    )
    
    created_at: datetime = Field(default_factory=datetime.now)
    last_accessed: datetime = Field(default_factory=datetime.now)
    
    def to_natural_language(self) -> str:
        """Convert triple to natural language sentence."""
        base = f"{self.subject} {self.predicate.replace('_', ' ')} {self.object}"
        if self.context:
            base += f" ({self.context})"
        return base
    
    def is_opposite_of(self, other: "SemanticTriple") -> bool:
        """Check if this triple contradicts another (e.g., likes vs dislikes)."""
        if self.subject != other.subject or self.object != other.object:
            return False
        
        opposite_pairs = {
            ("likes", "dislikes"),
            ("loves", "hates"),
            ("wants", "avoids"),
            ("prefers", "dislikes"),
            ("is", "is_not"),
            ("can", "cannot"),
        }
        
        pred_pair = (self.predicate.lower(), other.predicate.lower())
        rev_pair = (other.predicate.lower(), self.predicate.lower())
        
        return pred_pair in opposite_pairs or rev_pair in opposite_pairs
    
    class Config:
        use_enum_values = True


# Predicate normalization mapping
PREDICATE_ALIASES = {
    "loves": "likes",
    "enjoys": "likes",
    "adores": "likes",
    "prefers": "likes",
    "hates": "dislikes",
    "despises": "dislikes",
    "understands": "knows",
    "is_called": "is_named",
    "named": "is_named",
    "works_at": "employed_by",
    "lives_in": "resides_in",
}


def normalize_predicate(predicate: str) -> str:
    """Normalize predicate to canonical form."""
    normalized = predicate.lower().strip().replace(" ", "_")
    return PREDICATE_ALIASES.get(normalized, normalized)
