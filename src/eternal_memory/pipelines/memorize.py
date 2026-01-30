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

from eternal_memory.database.repository import MemoryRepository
from eternal_memory.llm.client import LLMClient
from eternal_memory.models.memory_item import Category, MemoryItem, MemoryType, Resource
from eternal_memory.vault.markdown_vault import MarkdownVault


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
    ):
        self.repository = repository
        self.llm = llm_client
        self.vault = vault
    
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
        
        # 1. Create resource entry for traceability
        resource = Resource(
            uri=metadata.get("uri", f"conversation/{datetime.now().isoformat()}"),
            modality=metadata.get("modality", "conversation"),
            content=text,
            metadata=metadata,
        )
        await self.repository.create_resource(resource)
        
        # 2. Extract facts using LLM (No longer needs all category_paths)
        extracted_facts = await self.llm.extract_facts(text, [])
        
        if not extracted_facts:
            # No meaningful facts extracted, still log to timeline
            await self.vault.append_to_timeline(text, datetime.now())
            return []
        
        # 3. Process each extracted fact
        for fact in extracted_facts:
            content = fact.get("content", "")
            if not content:
                continue
            
            # Smart Categorization is now part of store_single_memory or process_fact
            item = await self.store_single_memory(
                content=content,
                fact_type=fact.get("type", "fact"),
                importance=float(fact.get("importance", 0.5)),
                metadata={"resource_id": str(resource.id)},
                skip_resource=True # Resource already created
            )
            created_items.append(item)
        
        # 8. Update timeline
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
        
        # 2. Check for duplicates (using pre-calculated embedding)
        embedding = await self.llm.generate_embedding(content)
        similar_items = await self.repository.vector_search(
            query_embedding=embedding,
            limit=1,
            threshold=0.95
        )
        
        if similar_items:
            existing = similar_items[0]
            await self.repository.update_last_accessed(existing.id)
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

        # 4. Process and persist
        item = await self.process_fact(
            content=content,
            category_path=category_path,
            fact_type=fact_type,
            importance=importance,
            resource_id=resource_id,
            embedding=embedding
        )
        
        # 5. Update timeline
        if not skip_resource:
            await self.vault.append_to_timeline(
                f"Stored memory: {content[:100]}...",
                datetime.now(),
            )
        
        return item
    
    async def _ensure_category(self, path: str) -> Category:
        """
        Ensure a category exists, creating it if necessary.
        Also creates parent categories as needed.
        """
        existing = await self.repository.get_category_by_path(path)
        if existing:
            return existing
        
        # Create parent categories first
        parts = path.split("/")
        parent_id = None
        
        for i in range(len(parts)):
            current_path = "/".join(parts[:i+1])
            existing = await self.repository.get_category_by_path(current_path)
            
            if existing:
                parent_id = existing.id
            else:
                # Generate embedding for the new category path/name
                cat_embedding = await self.llm.generate_embedding(parts[i])
                
                category = Category(
                    name=parts[i],
                    path=current_path,
                    parent_id=parent_id,
                )
                await self.repository.create_category(category, embedding=cat_embedding)
                
                # Create corresponding markdown file
                await self.vault.ensure_category_file(current_path)
                
                parent_id = category.id
        
        return await self.repository.get_category_by_path(path)
