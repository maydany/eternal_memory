"""
Consolidate Pipeline

Implements memory maintenance as specified in Section 5.5:
- Scan for rarely accessed items
- Summarize them into archived files
- Re-cluster categories if too large
- Apply forgetting curve
"""

from datetime import datetime
from typing import List

from eternal_memory.database.repository import MemoryRepository
from eternal_memory.llm.client import LLMClient
from eternal_memory.vault.markdown_vault import MarkdownVault


class ConsolidatePipeline:
    """
    Pipeline for memory consolidation and archival.
    
    Implements the "Self-Evolution" aspect of the memory system
    by managing memory lifecycle.
    
    Note: USER.md updates are handled by a separate profile_reflection job,
    not by this pipeline. This follows the Single Responsibility Principle.
    """
    
    def __init__(
        self,
        repository: MemoryRepository,
        llm_client: LLMClient,
        vault: MarkdownVault,
        stale_days_threshold: int = 30,
        max_category_items: int = 100,
    ):
        self.repository = repository
        self.llm = llm_client
        self.vault = vault
        self.stale_days_threshold = stale_days_threshold
        self.max_category_items = max_category_items
    
    async def execute(self) -> dict:
        """
        Execute the consolidation pipeline.
        
        Returns:
            Statistics about what was processed
        """
        stats = {
            "archived_items": 0,
            "updated_summaries": 0,
            "reorganized_categories": 0,
        }
        
        # 1. Archive stale items (DISABLED for Eternal Memory philosophy)
        # We do not move/delete items. Stale items remain in DB.
        # archived = await self._archive_stale_items()
        stats["archived_items"] = 0
        
        # 2. Update category summaries
        summaries = await self._update_category_summaries()
        stats["updated_summaries"] = summaries
        
        # 3. Check and reorganize large categories
        reorg = await self._reorganize_large_categories()
        stats["reorganized_categories"] = reorg
        
        # 4. Database Optimization
        try:
            await self.repository.optimize_database()
            stats["db_optimized"] = True
        except Exception:
            stats["db_optimized"] = False
        
        return stats
    
    async def _archive_stale_items(self) -> int:
        """
        Find and archive items not accessed recently.
        
        Items below a certain importance threshold that haven't
        been accessed are summarized and archived.
        """
        stale_items = await self.repository.get_stale_items(
            days_threshold=self.stale_days_threshold,
            limit=50,
        )
        
        if not stale_items:
            return 0
        
        # Group by category for summarization
        category_items = {}
        for item in stale_items:
            cat = item.category_path or "uncategorized"
            if cat not in category_items:
                category_items[cat] = []
            category_items[cat].append(item)
        
        archived_count = 0
        
        for category, items in category_items.items():
            # Only archive low-importance items
            low_importance_items = [i for i in items if i.importance < 0.3]
            
            if len(low_importance_items) >= 5:
                # Summarize and archive
                contents = [item.content for item in low_importance_items]
                summary = await self.llm.summarize_category(
                    category_path=f"archived/{category}",
                    items=contents,
                )
                
                # Write to archived markdown
                await self.vault.archive_items(
                    category_path=category,
                    summary=summary,
                    original_count=len(low_importance_items),
                )
                
                # Delete from active storage
                for item in low_importance_items:
                    await self.repository.delete_memory_item(item.id)
                    archived_count += 1
        
        return archived_count
    
    async def _update_category_summaries(self) -> int:
        """
        Update summaries for all categories based on current items.
        """
        categories = await self.repository.get_all_categories()
        updated_count = 0
        
        for category in categories:
            items = await self.repository.get_items_by_category(
                category_path=category.path,
                limit=20,
            )
            
            if not items:
                continue
            
            # Generate new summary
            contents = [item.content for item in items]
            summary = await self.llm.summarize_category(
                category_path=category.path,
                items=contents,
            )
            
            # Update in database
            await self.repository.update_category_summary(category.path, summary)
            
            # Update in markdown
            await self.vault.update_category_summary(category.path, summary)
            
            updated_count += 1
        
        return updated_count
    
    async def _reorganize_large_categories(self) -> int:
        """
        Split categories that have grown too large.
        """
        categories = await self.repository.get_all_categories()
        reorganized = 0
        
        for category in categories:
            items = await self.repository.get_items_by_category(
                category_path=category.path,
                limit=self.max_category_items + 1,
            )
            
            if len(items) <= self.max_category_items:
                continue
            
            # Category is too large, needs reorganization
            # For now, just log - full implementation would
            # create sub-categories based on semantic clustering
            await self.vault.append_to_category(
                category_path=category.path,
                content=f"[SYSTEM] Category has {len(items)} items, consider reorganizing",
                memory_type="fact",
                timestamp=datetime.now(),
            )
            reorganized += 1
        
        return reorganized
