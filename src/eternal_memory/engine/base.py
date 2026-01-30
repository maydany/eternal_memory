"""
Eternal Memory Engine - Abstract Base Class

Defines the core interface for the memory system as specified in
eternal_memory_spec.md Section 4.2.
"""

from abc import ABC, abstractmethod
from typing import Literal, Optional

from eternal_memory.models.memory_item import MemoryItem
from eternal_memory.models.retrieval import RetrievalResult


class EternalMemoryEngine(ABC):
    """
    Abstract Base Class for the Eternal Memory Engine.
    
    Implements the four core pipelines:
    1. memorize() - Store new memories
    2. retrieve() - Recall memories with fast/deep modes
    3. consolidate() - Maintenance and archival
    4. predict_context() - Proactive context generation
    """
    
    @abstractmethod
    async def memorize(
        self,
        text: str,
        metadata: Optional[dict] = None,
    ) -> MemoryItem:
        """
        Input Pipeline: Store new information as memory.
        
        Process:
        1. Extract salient facts from text via LLM
        2. Assign to existing or new category
        3. Save to Vector DB with embedding
        4. Append to corresponding Markdown file
        
        Args:
            text: Input text to memorize
            metadata: Optional metadata (sender, app context, etc.)
            
        Returns:
            The created MemoryItem
        """
        pass
    
    @abstractmethod
    async def retrieve(
        self,
        query: str,
        mode: Literal["fast", "deep"] = "fast",
    ) -> RetrievalResult:
        """
        Output Pipeline: Recall memories based on query.
        
        Modes:
        - 'fast': Vector similarity search + Keyword search (RAG mode)
        - 'deep': LLM reads category summaries → Opens Markdown files → Reasons answer
        
        Args:
            query: Search query
            mode: Retrieval mode ('fast' or 'deep')
            
        Returns:
            RetrievalResult with matching items and context
        """
        pass
    
    @abstractmethod
    async def consolidate(self) -> None:
        """
        Maintenance Pipeline: Optimize and archive memories.
        
        Process:
        1. Scan for rarely accessed items
        2. Summarize them into 'archived' files
        3. Re-cluster categories if they become too large
        
        This implements the "forgetting curve" and self-evolution
        aspects of the memory system.
        """
        pass
    
    @abstractmethod
    async def predict_context(
        self,
        current_context: dict,
    ) -> str:
        """
        Proactive Pipeline: Generate context string for system prompt.
        
        Based on:
        - Current time
        - Open apps/files
        - Recent interaction patterns
        
        Returns a context string to be injected into the System Prompt
        before the user makes their next request.
        
        Args:
            current_context: Dictionary with current state info
            
        Returns:
            Context string for proactive injection
        """
        pass
