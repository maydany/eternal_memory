"""
Retrieve Pipeline

Implements the dual-mode retrieval as specified in Section 4 and 5.2:
- Fast Mode: Vector similarity search + Full-text search (RAG)
- Deep Mode: LLM reads summaries → Opens Markdown → Reasons answer
"""

from typing import List, Literal, Set

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
    ):
        self.repository = repository
        self.llm = llm_client
        self.vault = vault
    
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
        Fast mode: Vector similarity + Full-text search.
        
        - pgvector cosine similarity (threshold 0.8, top 5)
        - Combined with keyword search
        - Returns quickly without LLM reasoning
        """
        # Generate query embedding
        query_embedding = await self.llm.generate_embedding(evolved_query)
        
        # Vector similarity search
        vector_results = await self.repository.vector_search(
            query_embedding=query_embedding,
            limit=5,
            threshold=0.3,  # More permissive for better recall
        )
        
        # Full-text search for keyword matches
        keyword_results = await self.repository.fulltext_search(
            query=evolved_query,
            limit=5,
        )
        
        # Merge and deduplicate results
        all_items = self._merge_results(vector_results, keyword_results)
        
        # Get related categories
        related_categories: Set[str] = set()
        for item in all_items:
            if item.category_path:
                related_categories.add(item.category_path)
        
        # Generate quick context suggestion
        suggested_context = self._generate_quick_context(all_items)
        
        return RetrievalResult(
            items=all_items[:10],  # Limit to top 10
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
        Deep mode: LLM reads category summaries and Markdown files.
        
        - Scans category summaries to identify relevant areas
        - Reads actual Markdown files for detailed context
        - Uses LLM to reason and synthesize answer
        """
        # 1. Get all categories with summaries
        categories = await self.repository.get_all_categories()
        category_summaries = [
            f"{c.path}: {c.summary or 'No summary'}"
            for c in categories
        ]
        
        # 2. First pass: vector search for initial candidates
        query_embedding = await self.llm.generate_embedding(evolved_query)
        initial_results = await self.repository.vector_search(
            query_embedding=query_embedding,
            limit=10,
            threshold=0.2,
        )
        
        # 3. Identify relevant categories from results
        relevant_categories: Set[str] = set()
        for item in initial_results:
            if item.category_path:
                relevant_categories.add(item.category_path)
                # Also add parent categories
                parts = item.category_path.split("/")
                for i in range(len(parts)):
                    relevant_categories.add("/".join(parts[:i+1]))
        
        # 4. Read Markdown files for deeper context
        markdown_context: List[str] = []
        for cat_path in list(relevant_categories)[:5]:  # Limit to 5 categories
            content = await self.vault.read_category_file(cat_path)
            if content:
                markdown_context.append(f"[{cat_path}]\n{content[:500]}...")
        
        # 5. LLM reasoning to synthesize answer
        item_contents = [item.content for item in initial_results]
        reasoned_answer = await self.llm.reason_from_context(
            query=evolved_query,
            context_items=item_contents,
            category_summaries=category_summaries[:10],
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
