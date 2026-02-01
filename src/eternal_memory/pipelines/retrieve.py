"""
Retrieve Pipeline

Implements the dual-mode retrieval as specified in Section 4 and 5.2:
- Fast Mode: Vector similarity search + Full-text search (RAG)
- Deep Mode: LLM reads summaries → Opens Markdown → Reasons answer

Hierarchical Filtering (Hybrid MemGPT + Triple):
- When use_semantic_triples is enabled, search both MemoryItems and Triples
- Triples take precedence for entity-level precision
- MemoryItems without triples are used as fallback
"""

from typing import Dict, List, Literal, Optional, Set
from uuid import UUID

from eternal_memory.config import LLMConfig, ScoringConfig
from eternal_memory.database.repository import MemoryRepository
from eternal_memory.llm.client import LLMClient
from eternal_memory.models.memory_item import MemoryItem
from eternal_memory.models.semantic_triple import SemanticTriple
from eternal_memory.models.retrieval import RetrievalResult
from eternal_memory.vault.markdown_vault import MarkdownVault


class RetrievePipeline:
    """
    Pipeline for retrieving memories using hybrid search.
    
    Supports two modes:
    - 'fast': Vector + keyword search (low latency)
    - 'deep': LLM-powered reasoning (high accuracy)
    
    Hierarchical Filtering:
    When semantic triples are enabled, the pipeline performs:
    1. Search both MemoryItems and Triples
    2. Triple results take precedence (more precise, entity-level)
    3. MemoryItems without triples are used as fallback
    """
    
    def __init__(
        self,
        repository: MemoryRepository,
        llm_client: LLMClient,
        vault: MarkdownVault,
        scoring_config: Optional[ScoringConfig] = None,
        llm_config: Optional[LLMConfig] = None,
    ):
        self.repository = repository
        self.llm = llm_client
        self.vault = vault
        self.scoring = scoring_config or ScoringConfig()
        self.llm_config = llm_config or LLMConfig()
    
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
        Fast mode: Generative Agents-style search with Hierarchical Filtering.
        
        Uses the scoring formula:
        Score = α_relevance × Relevance + α_recency × Recency + α_importance × Importance
        
        Hierarchical Filtering (when use_semantic_triples is enabled):
        1. Search both MemoryItems and Triples
        2. Triple results take precedence (more precise, entity-level)
        3. MemoryItems without triples are used as fallback
        """
        # Generate query embedding
        query_embedding = await self.llm.generate_embedding(evolved_query)
        
        # Use Generative Agents-style search with configurable weights
        memory_items = await self.repository.generative_agents_search(
            query_embedding=query_embedding,
            limit=10,
            alpha_relevance=self.scoring.alpha_relevance,
            alpha_recency=self.scoring.alpha_recency,
            alpha_importance=self.scoring.alpha_importance,
            recency_decay_factor=self.scoring.recency_decay_factor,
            min_relevance_threshold=self.scoring.min_relevance_threshold,
        )
        
        # Apply Hierarchical Filtering if semantic triples are enabled
        if self.llm_config.use_semantic_triples:
            filtered_items, triple_context = await self._apply_hierarchical_filter(
                memory_items=memory_items,
                query_embedding=query_embedding,
            )
            all_items = filtered_items
            context_prefix = triple_context
        else:
            all_items = memory_items
            context_prefix = ""
        
        # Get related categories
        related_categories: Set[str] = set()
        for item in all_items:
            if item.category_path:
                related_categories.add(item.category_path)
        
        # Generate quick context suggestion with triple context prefix
        suggested_context = self._generate_quick_context(all_items, context_prefix)
        
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
        Deep mode: LLM reasoning over DB results with Hierarchical Filtering.
        
        - Uses Generative Agents search for high-quality ranking
        - Uses LLM to reason and synthesize answer from DB chunks
        - When semantic triples enabled: includes precise triple facts
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
        
        # 2. Apply Hierarchical Filtering if semantic triples are enabled
        if self.llm_config.use_semantic_triples:
            filtered_results, triple_context = await self._apply_hierarchical_filter(
                memory_items=initial_results,
                query_embedding=query_embedding,
            )
        else:
            filtered_results = initial_results
            triple_context = ""
        
        # 3. Identify relevant categories from results
        relevant_categories: Set[str] = set()
        for item in filtered_results:
            if item.category_path:
                relevant_categories.add(item.category_path)
        
        # 4. LLM reasoning to synthesize answer
        # Include triple context as high-precision facts
        item_contents = []
        if triple_context:
            item_contents.append(f"[High-precision entity facts]: {triple_context}")
        item_contents.extend([item.content for item in filtered_results])
        
        # We pass empty category summaries to focus strict attention on specific facts
        reasoned_answer = await self.llm.reason_from_context(
            query=evolved_query,
            context_items=item_contents,
            category_summaries=[], 
        )
        
        return RetrievalResult(
            items=filtered_results,
            related_categories=list(relevant_categories),
            suggested_context=reasoned_answer,
            query_evolved=evolved_query if evolved_query != original_query else None,
            retrieval_mode="deep",
            confidence_score=0.85 if triple_context else (0.8 if filtered_results else 0.3),
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
    
    def _generate_quick_context(
        self, 
        items: List[MemoryItem], 
        triple_context: str = ""
    ) -> str:
        """
        Generate a quick context summary from retrieved items.
        
        Args:
            items: Retrieved memory items
            triple_context: Prefix context from triple-based filtering
        """
        parts = []
        
        # Add triple context first (higher precision)
        if triple_context:
            parts.append(f"[Precise facts] {triple_context}")
        
        if not items and not triple_context:
            return "No relevant memories found."
        
        # Take top 3 items for context
        if items:
            top_items = items[:3]
            memory_parts = [item.content for item in top_items]
            if memory_parts:
                parts.append("Relevant context: " + "; ".join(memory_parts))
        
        return " | ".join(parts) if parts else "No relevant memories found."
    
    def _calculate_confidence(self, items: List[MemoryItem]) -> float:
        """
        Calculate overall confidence score based on results.
        """
        if not items:
            return 0.0
        
        avg_confidence = sum(item.confidence for item in items) / len(items)
        return min(avg_confidence, 1.0)
    
    async def _apply_hierarchical_filter(
        self,
        memory_items: List[MemoryItem],
        query_embedding: List[float],
    ) -> tuple[List[MemoryItem], str]:
        """
        Apply Hierarchical Filtering for hybrid MemGPT + Triple architecture.
        
        Strategy:
        1. Search for relevant triples semantically
        2. For MemoryItems with ALL triples inactive: EXCLUDE (outdated by supersede)
        3. For MemoryItems with active triples: include (triple context provides precision)
        4. For MemoryItems without any triples: use original content (fallback - not yet atomized)
        5. Triple context is prefixed for higher precision
        
        Args:
            memory_items: Retrieved memory items from generative_agents_search
            query_embedding: Query embedding for triple search
            
        Returns:
            Tuple of (filtered_items, triple_context_string)
        """
        # Search for relevant triples (active only for context building)
        triples = await self.repository.search_triples_semantic(
            query_embedding=query_embedding,
            limit=15,
            threshold=0.4,
            active_only=True,
        )
        
        # Build triple context from active triples (high precision facts)
        triple_statements = []
        for triple in triples:
            triple_statements.append(triple.to_natural_language())
        
        # Deduplicate and limit
        unique_statements = list(dict.fromkeys(triple_statements))[:5]
        triple_context = "; ".join(unique_statements)
        
        # CRITICAL FIX: Check ALL triples for each memory item (not just search results)
        # This catches MemoryItems that HAD triples but ALL are now inactive (superseded)
        all_triples_by_memory: Dict[UUID, List[SemanticTriple]] = {}
        for item in memory_items:
            # Fetch ALL triples for this memory item (including inactive)
            item_all_triples = await self.repository.get_triples_for_memory_item(
                item.id, 
                active_only=False  # Get all to check if ANY exist
            )
            if item_all_triples:
                all_triples_by_memory[item.id] = item_all_triples
        
        # Filter memory items based on triple status
        filtered_items = []
        for item in memory_items:
            all_item_triples = all_triples_by_memory.get(item.id, [])
            
            if all_item_triples:
                # Memory HAS triples (was atomized)
                if any(t.is_active for t in all_item_triples):
                    # Has at least one active triple - include for metadata
                    # (triple context already provides precision for active facts)
                    filtered_items.append(item)
                # else: ALL triples are inactive → EXCLUDE
                # This memory's facts have been superseded at the triple level
            else:
                # No triples for this memory - use original content (fallback)
                # This is acceptable as the memory hasn't been atomized yet
                filtered_items.append(item)
        
        return filtered_items, triple_context

