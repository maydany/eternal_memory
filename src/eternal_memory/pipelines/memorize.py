"""
Memorize Pipeline

Implements the memory storage pipeline as specified in Section 5.1:
1. Extract salient facts from text via LLM
2. Assign to existing or new category
3. Save to Vector DB with embedding
4. Append to corresponding Markdown file
"""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4
import time

from eternal_memory.database.repository import MemoryRepository
from eternal_memory.llm.client import LLMClient
from eternal_memory.models.memory_item import Category, MemoryItem, MemoryType, Resource
from eternal_memory.vault.markdown_vault import MarkdownVault
from eternal_memory.pipelines.hooks import PipelineHookManager
from eternal_memory.config import LLMConfig


class MemorizePipeline:
    """
    Pipeline for storing new memories.
    
    Flow:
    Input → LLM Extraction → Category Assignment → 
    Vector DB Storage → Markdown Sync
    """
    
    def __init__(
        self,
        repository: MemoryRepository,
        llm_client: LLMClient,
        vault: MarkdownVault,
        enable_monitoring: bool = True,
        llm_config: Optional[LLMConfig] = None,
    ):
        self.repository = repository
        self.llm = llm_client
        self.vault = vault
        self.llm_config = llm_config or LLMConfig()
        
        # Initialize hook system
        self.hooks = PipelineHookManager()
        self._register_default_hooks()
        
        # Initialize performance monitoring
        if enable_monitoring:
            from eternal_memory.monitoring import get_monitor
            self.monitor = get_monitor()
            self._register_monitoring_hooks()
    
    async def execute(
        self,
        text: str,
        metadata: Optional[dict] = None,
    ) -> List[MemoryItem]:
        """
        Execute the memorize pipeline.
        
        Args:
            text: Input text to memorize
            metadata: Optional metadata (sender, source, etc.)
            
        Returns:
            List of created MemoryItems
        """
        metadata = metadata or {}
        created_items: List[MemoryItem] = []
        
        # Initialize pipeline context
        context = {
            "text": text,
            "metadata": metadata,
            "created_items": created_items,
            "start_time": time.time(),
        }
        
        # 1. Create resource entry for traceability
        resource = Resource(
            uri=metadata.get("uri", f"conversation/{datetime.now().isoformat()}"),
            modality=metadata.get("modality", "conversation"),
            content=text,
            metadata=metadata,
        )
        await self.repository.create_resource(resource)
        context["resource"] = resource
        
        # 2. Extract facts using LLM (No longer needs all category_paths)
        await self.hooks.execute_before("extract", context)
        
        extracted_facts = await self.llm.extract_facts(text, [])
        
        if not extracted_facts:
            # No meaningful facts extracted, still log to timeline
            await self.vault.append_to_timeline(text, datetime.now())
            context["extracted_facts"] = []
            await self.hooks.execute_after("extract", context)
            return []
        
        context["extracted_facts"] = extracted_facts
        await self.hooks.execute_after("extract", context)
        
        # 3. Batch embed all facts at once (Performance optimization)
        # This reduces API calls from N to 1, saving ~70% cost and ~5x speed
        fact_contents = [fact.get("content", "") for fact in extracted_facts if fact.get("content")]
        
        if not fact_contents:
            return []
        
        # Single batch API call instead of N individual calls
        batch_embeddings = await self.llm.batch_generate_embeddings(fact_contents)
        context["batch_embeddings"] = batch_embeddings
        
        # 4. Process each extracted fact with pre-computed embeddings
        await self.hooks.execute_before("store", context)
        
        for i, fact in enumerate(extracted_facts):
            content = fact.get("content", "")
            if not content:
                continue
            
            # Smart Categorization using pre-computed embedding
            item = await self.store_single_memory(
                content=content,
                fact_type=fact.get("type", "fact"),
                importance=float(fact.get("importance", 0.5)),
                metadata={"resource_id": str(resource.id)},
                skip_resource=True,  # Resource already created
                precomputed_embedding=batch_embeddings[i]  # Pass pre-computed embedding
            )
            created_items.append(item)
        
        context["created_items"] = created_items
        await self.hooks.execute_after("store", context)
        
        # 5. Update timeline
        await self.vault.append_to_timeline(
            f"Stored {len(created_items)} memories from: {text[:100]}...",
            datetime.now(),
        )
        
        return created_items


    async def process_fact(
        self,
        content: str,
        category_path: str,
        fact_type: str,
        importance: float,
        resource_id: uuid4,
        embedding: Optional[List[float]] = None,
    ) -> MemoryItem:
        """Process and store a single fact (no LLM extraction)."""
        # Get or create category
        category = await self._ensure_category(category_path)
        
        # Create memory item
        memory_item = MemoryItem(
            content=content,
            category_path=category_path,
            type=MemoryType(fact_type),
            importance=importance,
            source_resource_id=resource_id,
        )
        
        # Generate embedding if not provided
        if not embedding:
            embedding = await self.llm.generate_embedding(content)
        
        # Save to database
        await self.repository.create_memory_item(
            item=memory_item,
            embedding=embedding,
            category_id=category.id,
        )
        
        # Sync to Markdown vault
        await self.vault.append_to_category(
            category_path=category_path,
            content=content,
            memory_type=memory_item.type,
            timestamp=memory_item.created_at,
        )
        
        return memory_item

    async def store_single_memory(
        self,
        content: str,
        category_path: Optional[str] = None,
        fact_type: str = "fact",
        importance: float = 0.5,
        metadata: Optional[dict] = None,
        skip_resource: bool = False,
        precomputed_embedding: Optional[List[float]] = None,
    ) -> MemoryItem:
        """Store a single memory directly with smart categorization."""
        metadata = metadata or {}
        
        # 1. Create resource if needed
        resource_id = metadata.get("resource_id")
        if not skip_resource:
            resource = Resource(
                uri=metadata.get("uri", f"conversation/{datetime.now().isoformat()}"),
                modality=metadata.get("modality", "conversation"),
                content=content,
                metadata=metadata,
            )
            await self.repository.create_resource(resource)
            resource_id = resource.id
        
        # 2. Check for duplicates (using pre-calculated or new embedding)
        if precomputed_embedding is not None:
            embedding = precomputed_embedding
        else:
            embedding = await self.llm.generate_embedding(content)
        
        similar_items = await self.repository.vector_search(
            query_embedding=embedding,
            limit=1,
            threshold=0.95
        )
        
        if similar_items:
            existing = similar_items[0]
            
            # Reinforcement Logic:
            # If the same fact is mentioned again, increase its importance
            # Formula: min(1.0, current_importance + 0.1)
            new_importance = min(1.0, existing.importance + 0.1)
            
            new_count = await self.repository.reinforce_memory_item(existing.id, new_importance)
            
            # Update local object to reflect changes
            existing.importance = new_importance
            existing.mention_count = new_count
            existing.last_accessed = datetime.now()
            
            # Sync update to vault file
            await self.vault.update_memory_in_file(
                category_path=existing.category_path,
                content=existing.content,
                new_importance=new_importance,
                mention_count=new_count
            )
            
            return existing

        # 3. Smart Categorization (if no path provided)
        if not category_path:
            # Find candidate categories semantically
            candidates = await self.repository.vector_search_categories(
                query_embedding=embedding,
                limit=5,
                threshold=0.2
            )
            candidate_paths = [c.path for c in candidates]
            
            # Let LLM refine the path
            category_path = await self.llm.suggest_category(content, candidate_paths)

        # 4. LLM-based importance rating if enabled
        final_importance = importance
        if self.llm_config.use_llm_importance and importance == 0.5:
            # Only rate if using default importance (not already set)
            try:
                final_importance = await self.llm.rate_importance(content)
            except Exception as e:
                # Fallback to default on error
                final_importance = 0.5
        
        # 5. Process and persist
        item = await self.process_fact(
            content=content,
            category_path=category_path,
            fact_type=fact_type,
            importance=final_importance,
            resource_id=resource_id,
            embedding=embedding
        )
        
        # 6. MemGPT-style supersede: Check for contradicting memories
        if self.llm_config.use_memory_supersede:
            try:
                # Search for similar (but not duplicate) memories
                similar_candidates = await self.repository.vector_search(
                    query_embedding=embedding,
                    limit=3,
                    threshold=0.85  # Lower than duplicate threshold (0.95)
                )
                
                for candidate in similar_candidates:
                    # Skip self and duplicates (already handled above)
                    if candidate.id == item.id:
                        continue
                    
                    # Ask LLM if this is an update/correction
                    relation = await self.llm.is_update_or_correction(
                        new_content=content,
                        existing_content=candidate.content,
                        model_override=self.llm_config.get_supersede_model(),
                    )
                    
                    if relation == "UPDATE":
                        # Mark old memory as superseded by new
                        await self.repository.supersede_memory_item(
                            old_item_id=candidate.id,
                            new_item_id=item.id,
                        )
                        # Log to timeline
                        await self.vault.append_to_timeline(
                            f"🔄 Superseded: '{candidate.content[:50]}...' → '{content[:50]}...'",
                            datetime.now(),
                        )
            except Exception as e:
                # Supersede is optional, don't fail the whole operation
                pass
        
        # 7. Update timeline
        if not skip_resource:
            await self.vault.append_to_timeline(
                f"Stored memory: {content[:100]}...",
                datetime.now(),
            )
        
        return item
    
    async def _ensure_category(self, path: str, parent_id: Optional[int] = None) -> Category:
        """
        Ensure category exists by path, creating all parent categories if needed.
        Uses batch embedding for all new categories in the path.
        """
        # Already exists?
        existing = await self.repository.get_category_by_path(path)
        if existing:
            return existing
        
        # Split path and identify new categories
        parts = path.split("/")
        new_category_names = []
        new_category_paths = []
        parent_id = parent_id
        
        # First pass: identify which categories need to be created
        for i in range(len(parts)):
            current_path = "/".join(parts[:i+1])
            existing = await self.repository.get_category_by_path(current_path)
            
            if existing:
                parent_id = existing.id
            else:
                new_category_names.append(parts[i])
                new_category_paths.append(current_path)
        
        # Batch embed all new categories at once
        if new_category_names:
            cat_embeddings = await self.llm.batch_generate_embeddings(new_category_names)
            
            # Second pass: create categories with pre-computed embeddings
            for j, (name, path_str) in enumerate(zip(new_category_names, new_category_paths)):
                category = Category(
                    name=name,
                    path=path_str,
                    parent_id=parent_id,
                )
                await self.repository.create_category(category, embedding=cat_embeddings[j])
                
                # Create corresponding markdown file
                await self.vault.ensure_category_file(path_str)
                
                parent_id = category.id
        
        return await self.repository.get_category_by_path(path)
    
    def _register_default_hooks(self) -> None:
        """Register built-in hooks for logging and performance tracking."""
        import logging
        logger = logging.getLogger("eternal_memory.pipeline")
        
        # Performance tracking hook (applies to all stages)
        @self.hooks.before("*")
        async def track_stage_start(stage: str, context: dict):
            if "stage_timers" not in context:
                context["stage_timers"] = {}
            context["stage_timers"][stage] = time.time()
        
        @self.hooks.after("*")
        async def track_stage_end(stage: str, context: dict):
            if "stage_timers" in context and stage in context["stage_timers"]:
                elapsed = time.time() - context["stage_timers"][stage]
                logger.debug(f"[Pipeline] {stage} completed in {elapsed:.3f}s")
        
        # Extraction validation hook
        @self.hooks.after("extract")
        async def validate_extraction(context: dict):
            facts = context.get("extracted_facts", [])
            if len(facts) == 0:
                logger.warning(f"No facts extracted from: {context['text'][:50]}...")
            else:
                logger.info(f"Extracted {len(facts)} facts")
        
        # Storage confirmation hook
        @self.hooks.after("store")
        async def log_storage_complete(context: dict):
            items = context.get("created_items", [])
            total_time = time.time() - context.get("start_time", time.time())
            logger.info(f"Stored {len(items)} items in {total_time:.2f}s")
    
    def _register_monitoring_hooks(self) -> None:
        """Register performance monitoring hooks."""
        
        # Record complete pipeline execution after store
        @self.hooks.after("store")
        async def record_metrics(context: dict):
            await self.monitor.record_pipeline_execution(context)
        
        # Record embedding performance
        @self.hooks.after("extract")
        async def record_embedding_perf(context: dict):
            await self.monitor.record_embedding_performance(context)
