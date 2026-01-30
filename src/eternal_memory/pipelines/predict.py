"""
Predict Pipeline

Implements proactive context prediction as specified in Section 5.3 and 5.4:
- Analyze current context and past patterns
- Predict user's next intent
- Generate context for system prompt injection
"""

from datetime import datetime
from typing import List

from eternal_memory.database.repository import MemoryRepository
from eternal_memory.llm.client import LLMClient
from eternal_memory.vault.markdown_vault import MarkdownVault


class PredictPipeline:
    """
    Pipeline for proactive context prediction.
    
    Analyzes current situation and past patterns to predict
    what context the user might need next.
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
    
    async def execute(self, current_context: dict) -> str:
        """
        Execute the prediction pipeline.
        
        Args:
            current_context: Dictionary containing:
                - time: Current time
                - open_apps: List of open applications
                - recent_files: Recently accessed files
                - location: Optional location info
                
        Returns:
            Context string for system prompt injection
        """
        # 1. Get recent memory access patterns
        recent_items = await self.repository.get_recent_items(limit=10)
        
        # 2. Extract patterns from recent accesses
        patterns = self._extract_patterns(recent_items, current_context)
        
        # 3. Get relevant category summaries
        categories = await self.repository.get_all_categories()
        active_categories = [
            c for c in categories
            if c.path in [item.category_path for item in recent_items]
        ]
        
        # 4. Predict next intent using LLM
        predicted_context = await self.llm.predict_next_intent(
            current_context=current_context,
            recent_patterns=patterns,
        )
        
        # 5. Preload relevant memories
        preloaded_context = await self._preload_relevant_memories(
            predicted_context,
            active_categories,
        )
        
        # 6. Format final context string
        return self._format_injection_context(
            predicted_context,
            preloaded_context,
            current_context,
        )
    
    def _extract_patterns(
        self,
        recent_items: List,
        current_context: dict,
    ) -> List[str]:
        """
        Extract behavioral patterns from recent memory accesses.
        """
        patterns = []
        
        # Time-based patterns
        current_hour = datetime.now().hour
        if 6 <= current_hour < 12:
            patterns.append("Morning work session")
        elif 12 <= current_hour < 18:
            patterns.append("Afternoon work session")
        elif 18 <= current_hour < 22:
            patterns.append("Evening session")
        else:
            patterns.append("Late night session")
        
        # Category patterns
        category_counts = {}
        for item in recent_items:
            cat = item.category_path.split("/")[0] if item.category_path else "other"
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        if category_counts:
            dominant_category = max(category_counts, key=category_counts.get)
            patterns.append(f"Currently focused on: {dominant_category}")
        
        # Memory type patterns
        type_counts = {}
        for item in recent_items:
            type_counts[item.type] = type_counts.get(item.type, 0) + 1
        
        if type_counts:
            dominant_type = max(type_counts, key=type_counts.get)
            patterns.append(f"Recent activity type: {dominant_type}")
        
        # App context if available
        if "open_apps" in current_context:
            apps = current_context["open_apps"]
            if "code" in str(apps).lower() or "vscode" in str(apps).lower():
                patterns.append("User appears to be coding")
            if "browser" in str(apps).lower():
                patterns.append("User is browsing")
        
        return patterns
    
    async def _preload_relevant_memories(
        self,
        predicted_context: str,
        active_categories: List,
    ) -> List[str]:
        """
        Preload memories that might be relevant based on predictions.
        """
        preloaded = []
        
        # Get items from active categories
        for category in active_categories[:3]:  # Limit to 3 categories
            items = await self.repository.get_items_by_category(
                category_path=category.path,
                limit=3,
            )
            for item in items:
                preloaded.append(item.content)
        
        return preloaded
    
    def _format_injection_context(
        self,
        predicted_context: str,
        preloaded_memories: List[str],
        current_context: dict,
    ) -> str:
        """
        Format the final context string for system prompt injection.
        """
        parts = []
        
        # Add prediction
        parts.append(f"[Predicted Intent] {predicted_context}")
        
        # Add time context
        now = datetime.now()
        parts.append(f"[Current Time] {now.strftime('%Y-%m-%d %H:%M')}")
        
        # Add preloaded memories
        if preloaded_memories:
            parts.append("[Relevant Memories]")
            for mem in preloaded_memories[:5]:  # Limit to 5
                parts.append(f"  - {mem[:100]}..." if len(mem) > 100 else f"  - {mem}")
        
        return "\n".join(parts)
