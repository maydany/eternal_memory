"""
Retrieve Pipeline

Implements the dual-mode retrieval as specified in Section 4 and 5.2:
- Fast Mode: Vector similarity search + Full-text search (RAG)
- Deep Mode: LLM reads summaries → Opens Markdown → Reasons answer
"""

from typing import List, Literal, Optional, Set

from eternal_memory.config import ScoringConfig
from eternal_memory.database.repository import MemoryRepository
from eternal_memory.llm.client import LLMClient
from eternal_memory.models.memory_item import MemoryItem
from eternal_memory.models.retrieval import RetrievalResult
from eternal_memory.vault.markdown_vault import MarkdownVault


class RetrievePipeline:
    """
    Pipeline for retrieving memories using hybrid search.
    
    Supports two modes:
    - 'fast': Vector + keyword search (low latency)
    - 'deep': LLM-powered reasoning (high accuracy)
    """
    
    def __init__(
        self,
        repository: MemoryRepository,
        llm_client: LLMClient,
        vault: MarkdownVault,
        scoring_config: Optional[ScoringConfig] = None,
    ):
        self.repository = repository
        self.llm = llm_client
        self.vault = vault
        self.scoring = scoring_config or ScoringConfig()
    
    async def execute(
        self,
        query: str,
        mode: Literal["fast", "deep"] = "fast",
        conversation_context: str = "",
    ) -> RetrievalResult:
        """
        Execute the retrieval pipeline.
        
        Args:
            query: Search query
            mode: 'fast' for RAG, 'deep' for LLM reasoning
            conversation_context: Recent conversation for query evolution
            
        Returns:
            RetrievalResult with items and context
        """
        # 1. Query Evolution - clarify vague queries
        evolved_query = await self.llm.evolve_query(query, conversation_context)
        
        if mode == "fast":
            return await self._fast_retrieval(query, evolved_query)
        else:
            return await self._deep_retrieval(query, evolved_query)
    
    async def _fast_retrieval(
        self,
        original_query: str,
        evolved_query: str,
    ) -> RetrievalResult:
        """
        Fast mode: Generative Agents-style search.
        
        Uses the scoring formula:
        Score = α_relevance × Relevance + α_recency × Recency + α_importance × Importance
        """
        # Generate query embedding
        query_embedding = await self.llm.generate_embedding(evolved_query)
        
        # Use Generative Agents-style search with configurable weights
        all_items = await self.repository.generative_agents_search(
            query_embedding=query_embedding,
            limit=10,
            alpha_relevance=self.scoring.alpha_relevance,
            alpha_recency=self.scoring.alpha_recency,
            alpha_importance=self.scoring.alpha_importance,
            recency_decay_factor=self.scoring.recency_decay_factor,
            min_relevance_threshold=self.scoring.min_relevance_threshold,
        )
        
        # Get related categories
        related_categories: Set[str] = set()
        for item in all_items:
            if item.category_path:
                related_categories.add(item.category_path)
        
        # Generate quick context suggestion
        suggested_context = self._generate_quick_context(all_items)
        
        return RetrievalResult(
            items=all_items,
            related_categories=list(related_categories),
            suggested_context=suggested_context,
            query_evolved=evolved_query if evolved_query != original_query else None,
            retrieval_mode="fast",
            confidence_score=self._calculate_confidence(all_items),
        )
    
    async def _deep_retrieval(
        self,
        original_query: str,
        evolved_query: str,
    ) -> RetrievalResult:
        """
        Deep mode: LLM reasoning over DB results.
        
        - Uses Generative Agents search for high-quality ranking
        - Uses LLM to reason and synthesize answer from DB chunks
        - STRICTLY DB-ONLY: No access to Markdown files
        """
        # 1. High-recall Generative Agents search
        query_embedding = await self.llm.generate_embedding(evolved_query)
        initial_results = await self.repository.generative_agents_search(
            query_embedding=query_embedding,
            limit=20,  # Higher limit for deep mode
            alpha_relevance=self.scoring.alpha_relevance,
            alpha_recency=self.scoring.alpha_recency,
            alpha_importance=self.scoring.alpha_importance,
            recency_decay_factor=self.scoring.recency_decay_factor,
            min_relevance_threshold=self.scoring.min_relevance_threshold * 0.8,  # Lower threshold for deep mode
        )
        
        # 2. Identify relevant categories from results
        relevant_categories: Set[str] = set()
        for item in initial_results:
            if item.category_path:
                relevant_categories.add(item.category_path)
        
        # 3. LLM reasoning to synthesize answer
        # We only use the content from the DB items
        item_contents = [item.content for item in initial_results]
        
        # We pass empty category summaries to focus strict attention on specific facts
        reasoned_answer = await self.llm.reason_from_context(
            query=evolved_query,
            context_items=item_contents,
            category_summaries=[], 
        )
        
        return RetrievalResult(
            items=initial_results,
            related_categories=list(relevant_categories),
            suggested_context=reasoned_answer,
            query_evolved=evolved_query if evolved_query != original_query else None,
            retrieval_mode="deep",
            confidence_score=0.8 if initial_results else 0.3,
        )
    
    def _merge_results(
        self,
        vector_results: List[MemoryItem],
        keyword_results: List[MemoryItem],
    ) -> List[MemoryItem]:
        """
        Merge vector and keyword search results, removing duplicates.
        """
        seen_ids = set()
        merged = []
        
        # Prioritize vector results
        for item in vector_results:
            if item.id not in seen_ids:
                seen_ids.add(item.id)
                merged.append(item)
        
        # Add keyword results not already present
        for item in keyword_results:
            if item.id not in seen_ids:
                seen_ids.add(item.id)
                merged.append(item)
        
        return merged
    
    def _generate_quick_context(self, items: List[MemoryItem]) -> str:
        """
        Generate a quick context summary from retrieved items.
        """
        if not items:
            return "No relevant memories found."
        
        # Take top 3 items for context
        top_items = items[:3]
        context_parts = [item.content for item in top_items]
        
        return "Relevant context: " + "; ".join(context_parts)
    
    def _calculate_confidence(self, items: List[MemoryItem]) -> float:
        """
        Calculate overall confidence score based on results.
        """
        if not items:
            return 0.0
        
        avg_confidence = sum(item.confidence for item in items) / len(items)
        return min(avg_confidence, 1.0)
