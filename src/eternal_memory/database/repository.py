"""
Memory Repository

CRUD operations for memory items, categories, and resources.
Handles vector similarity search and full-text search.
"""

import json
from datetime import datetime
from typing import List, Optional
from uuid import UUID

import asyncpg

from eternal_memory.models.memory_item import Category, MemoryItem, MemoryType, Resource
from eternal_memory.models.semantic_triple import SemanticTriple, normalize_predicate


class MemoryRepository:
    """
    Repository for all database operations on memory data.
    
    Provides methods for:
    - CRUD operations on resources, categories, and memory items
    - Vector similarity search (RAG mode)
    - Full-text search
    - Category management
    """
    
    def __init__(self, connection_string: str = None):
        self.connection_string = connection_string or "postgresql://127.0.0.1/eternal_memory"
        self._pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> None:
        """Initialize connection pool."""
        if self._pool is not None:
            return
        self._pool = await asyncpg.create_pool(self.connection_string, min_size=2, max_size=10)
    
    async def disconnect(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
    
    # ========== Resource Operations ==========
    
    async def create_resource(self, resource: Resource) -> Resource:
        """Create a new resource entry."""
        async with self._pool.acquire() as conn:
            # Serialize metadata dict to JSON string for PostgreSQL
            metadata_json = json.dumps(resource.metadata) if resource.metadata else None
            await conn.execute(
                """
                INSERT INTO resources (id, uri, modality, content, created_at, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                resource.id,
                resource.uri,
                resource.modality,
                resource.content,
                resource.created_at,
                metadata_json,
            )
        return resource
    
    async def get_resource(self, resource_id: UUID) -> Optional[Resource]:
        """Get a resource by ID."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM resources WHERE id = $1",
                resource_id,
            )
            if row:
                return Resource(
                    id=row["id"],
                    uri=row["uri"],
                    modality=row["modality"],
                    content=row["content"],
                    created_at=row["created_at"],
                    metadata=row["metadata"] or {},
                )
        return None
    
    # ========== Category Operations ==========
    
    async def create_category(self, category: Category, embedding: Optional[List[float]] = None) -> Category:
        """Create a new category."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO categories (id, name, description, parent_id, summary, path, embedding, last_accessed)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (path) DO UPDATE SET
                    description = EXCLUDED.description,
                    summary = EXCLUDED.summary,
                    embedding = COALESCE(EXCLUDED.embedding, categories.embedding),
                    last_accessed = NOW()
                """,
                category.id,
                category.name,
                category.description,
                category.parent_id,
                category.summary,
                category.path,
                str(embedding) if embedding else None,
                category.last_accessed,
            )
        return category

    async def vector_search_categories(
        self,
        query_embedding: List[float],
        limit: int = 5,
        threshold: float = 0.3,
    ) -> List[Category]:
        """Search categories by semantic similarity."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT *, 1 - (embedding <=> $1::vector) as similarity
                FROM categories
                WHERE embedding IS NOT NULL AND 1 - (embedding <=> $1::vector) >= $2
                ORDER BY embedding <=> $1::vector
                LIMIT $3
                """,
                str(query_embedding),
                threshold,
                limit,
            )
            
            return [
                Category(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    parent_id=row["parent_id"],
                    summary=row["summary"],
                    path=row["path"],
                    last_accessed=row["last_accessed"],
                )
                for row in rows
            ]
    
    async def get_category_by_path(self, path: str) -> Optional[Category]:
        """Get a category by its path."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM categories WHERE path = $1",
                path,
            )
            if row:
                return Category(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    parent_id=row["parent_id"],
                    summary=row["summary"],
                    path=row["path"],
                    last_accessed=row["last_accessed"],
                )
        return None
    
    async def get_all_categories(self) -> List[Category]:
        """Get all categories."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM categories ORDER BY path")
            return [
                Category(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    parent_id=row["parent_id"],
                    summary=row["summary"],
                    path=row["path"],
                    last_accessed=row["last_accessed"],
                )
                for row in rows
            ]
    
    async def update_category_summary(self, path: str, summary: str) -> None:
        """Update the summary of a category."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE categories 
                SET summary = $1, last_accessed = NOW()
                WHERE path = $2
                """,
                summary,
                path,
            )
    
    # ========== Memory Item Operations ==========
    
    async def create_memory_item(
        self,
        item: MemoryItem,
        embedding: List[float],
        category_id: Optional[UUID] = None,
    ) -> MemoryItem:
        """Create a new memory item with its embedding vector."""
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO memory_items 
                    (id, category_id, resource_id, content, embedding, type, importance, confidence, mention_count, created_at, last_accessed)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    """,
                    item.id,
                    category_id,
                    item.source_resource_id,
                    item.content,
                    str(embedding),  # pgvector accepts string format
                    item.type,
                    item.importance,
                    item.confidence,
                    item.mention_count,
                    item.created_at,
                    item.last_accessed,
                )
        except Exception as e:
            print(f"DEBUG ERROR: Failed to insert memory item: {e}", flush=True)
            raise e
        return item
    
    async def get_memory_item(self, item_id: UUID) -> Optional[MemoryItem]:
        """Get a memory item by ID."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT mi.*, c.path as category_path
                FROM memory_items mi
                LEFT JOIN categories c ON mi.category_id = c.id
                WHERE mi.id = $1
                """,
                item_id,
            )
            if row:
                return MemoryItem(
                    id=row["id"],
                    content=row["content"],
                    category_path=row["category_path"] or "",
                    type=MemoryType(row["type"]),
                    confidence=row["confidence"],
                    importance=row["importance"],
                    mention_count=row.get("mention_count", 1),
                    source_resource_id=row["resource_id"],
                    created_at=row["created_at"],
                    last_accessed=row["last_accessed"],
                )
        return None
    
    async def update_last_accessed(self, item_id: UUID) -> None:
        """Update the last_accessed timestamp for a memory item."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE memory_items SET last_accessed = NOW() WHERE id = $1",
                item_id,
            )

    async def reinforce_memory_item(self, item_id: UUID, new_importance: float) -> int:
        """
        Reinforce a memory item by incrementing mention_count and updating importance.
        Returns the new mention_count.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE memory_items 
                SET last_accessed = NOW(),
                    mention_count = mention_count + 1,
                    importance = $2
                WHERE id = $1
                RETURNING mention_count
                """,
                item_id,
                new_importance,
            )
            return row["mention_count"] if row else 0

    async def supersede_memory_item(
        self,
        old_item_id: UUID,
        new_item_id: UUID,
    ) -> bool:
        """
        MemGPT-style: Mark old memory as superseded by new memory.
        
        Based on MemGPT (Berkeley, 2023) core_memory_replace pattern.
        Old memory is soft-deleted (is_active=False) but preserved for history.
        
        Args:
            old_item_id: The memory being replaced
            new_item_id: The new memory that replaces it
            
        Returns:
            True if supersede was successful
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE memory_items 
                SET is_active = FALSE,
                    superseded_by = $2,
                    last_accessed = NOW()
                WHERE id = $1
                """,
                old_item_id,
                new_item_id,
            )
            return result == "UPDATE 1"
    
    # ========== Search Operations ==========
    
    async def vector_search(
        self,
        query_embedding: List[float],
        limit: int = 5,
        threshold: float = 0.8,
    ) -> List[MemoryItem]:
        """
        Search memory items by vector similarity (RAG mode).
        
        Uses cosine similarity with pgvector's HNSW index.
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT mi.*, c.path as category_path,
                       1 - (mi.embedding <=> $1::vector) as similarity
                FROM memory_items mi
                LEFT JOIN categories c ON mi.category_id = c.id
                WHERE 1 - (mi.embedding <=> $1::vector) >= $2
                ORDER BY mi.embedding <=> $1::vector
                LIMIT $3
                """,
                str(query_embedding),
                threshold,
                limit,
            )
            
            items = []
            for row in rows:
                item = MemoryItem(
                    id=row["id"],
                    content=row["content"],
                    category_path=row["category_path"] or "",
                    type=MemoryType(row["type"]),
                    confidence=row["confidence"] * row["similarity"],  # Adjust by similarity
                    importance=row["importance"],
                    mention_count=row.get("mention_count", 1),
                    source_resource_id=row["resource_id"],
                    created_at=row["created_at"],
                    last_accessed=row["last_accessed"],
                )
                items.append(item)
                # Update access timestamp
                await self.update_last_accessed(row["id"])
            
            return items

    async def hybrid_search(
        self,
        query_text: str,
        query_embedding: List[float],
        limit: int = 5,
        vector_weight: float = 0.7,
    ) -> List[MemoryItem]:
        """
        Hybrid search combining Vector Similarity (Cosine) and Keyword Match (Trigram).
        
        Args:
            query_text: Raw text for keyword search
            query_embedding: Embedding vector for semantic search
            limit: Number of results
            vector_weight: Weight for vector score (0.0 to 1.0)
        
        Returns:
            List of memory items sorted by combined score
        """
        keyword_weight = 1.0 - vector_weight
        
        async with self._pool.acquire() as conn:
            # Combined query using CTEs for normalization
            rows = await conn.fetch(
                """
                WITH vector_scores AS (
                    SELECT id, 1 - (embedding <=> $2::vector) as v_score
                    FROM memory_items
                    WHERE 1 - (embedding <=> $2::vector) > 0.5  -- Basic semantic filter
                ),
                keyword_scores AS (
                    SELECT id, similarity(content, $1) as k_score
                    FROM memory_items
                    WHERE content % $1  -- Trigram match operator
                )
                SELECT mi.*, c.path as category_path,
                       COALESCE(v.v_score, 0) as v_score,
                       COALESCE(k.k_score, 0) as k_score,
                       (COALESCE(v.v_score, 0) * $3 + COALESCE(k.k_score, 0) * $4) as final_score
                FROM memory_items mi
                LEFT JOIN categories c ON mi.category_id = c.id
                LEFT JOIN vector_scores v ON mi.id = v.id
                LEFT JOIN keyword_scores k ON mi.id = k.id
                WHERE (COALESCE(v.v_score, 0) * $3 + COALESCE(k.k_score, 0) * $4) > 0.0
                ORDER BY final_score DESC
                LIMIT $5
                """,
                query_text,
                str(query_embedding),
                vector_weight,
                keyword_weight,
                limit,
            )
            
            items = []
            for row in rows:
                item = MemoryItem(
                    id=row["id"],
                    content=row["content"],
                    category_path=row["category_path"] or "",
                    type=MemoryType(row["type"]),
                    confidence=row["confidence"], # Score is separate
                    importance=row["importance"],
                    mention_count=row.get("mention_count", 1),
                    source_resource_id=row["resource_id"],
                    created_at=row["created_at"],
                    last_accessed=row["last_accessed"],
                )
                # Attach score metadata if needed, or just return sorted
            items.append(item)
            
            return items

    async def generative_agents_search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        alpha_relevance: float = 1.0,
        alpha_recency: float = 1.0,
        alpha_importance: float = 1.0,
        recency_decay_factor: float = 0.995,
        min_relevance_threshold: float = 0.3,
    ) -> List[MemoryItem]:
        """
        Search using Generative Agents (Park et al., 2023) scoring formula.
        
        Score = α_relevance × Relevance + α_recency × Recency + α_importance × Importance
        
        Where:
        - Relevance: Cosine similarity (1 - cosine_distance)
        - Recency: Exponential decay decay_factor^(hours_since_last_access)
        - Importance: Stored importance value (0.0-1.0)
        
        Args:
            query_embedding: Query vector for semantic search
            limit: Maximum results to return
            alpha_relevance: Weight for semantic similarity
            alpha_recency: Weight for time-based decay
            alpha_importance: Weight for importance score
            recency_decay_factor: Per-hour decay factor (0.995 default)
            min_relevance_threshold: Minimum relevance to include
            
        Returns:
            List of MemoryItems sorted by combined score (highest first)
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                WITH scored AS (
                    SELECT 
                        mi.*,
                        c.path as category_path,
                        -- Relevance: Convert cosine distance to similarity
                        1 - (mi.embedding <=> $1::vector) as relevance,
                        -- Recency: Exponential decay based on hours since access
                        -- decay_factor^hours = e^(hours * ln(decay_factor))
                        POWER($5::float, 
                            GREATEST(0, EXTRACT(EPOCH FROM (NOW() - mi.last_accessed)) / 3600.0)
                        ) as recency,
                        -- Importance: Direct from storage
                        mi.importance as importance_score
                    FROM memory_items mi
                    LEFT JOIN categories c ON mi.category_id = c.id
                    WHERE mi.is_active = TRUE
                      AND 1 - (mi.embedding <=> $1::vector) >= $6
                )
                SELECT *,
                       -- Combined score using alpha weights
                       ($2::float * relevance + 
                        $3::float * recency + 
                        $4::float * importance_score) as final_score
                FROM scored
                ORDER BY final_score DESC
                LIMIT $7
                """,
                str(query_embedding),  # $1
                alpha_relevance,       # $2
                alpha_recency,         # $3
                alpha_importance,      # $4
                recency_decay_factor,  # $5
                min_relevance_threshold,  # $6
                limit,                 # $7
            )
            
            items = []
            for row in rows:
                item = MemoryItem(
                    id=row["id"],
                    content=row["content"],
                    category_path=row["category_path"] or "",
                    type=MemoryType(row["type"]),
                    confidence=row["confidence"],
                    importance=row["importance"],
                    mention_count=row.get("mention_count", 1),
                    source_resource_id=row["resource_id"],
                    created_at=row["created_at"],
                    last_accessed=row["last_accessed"],
                )
                items.append(item)
                # Update access timestamp for retrieved items
                await self.update_last_accessed(row["id"])
            
            return items

    
    async def fulltext_search(
        self,
        query: str,
        limit: int = 10,
    ) -> List[MemoryItem]:
        """
        Full-text search using PostgreSQL's tsvector.
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT mi.*, c.path as category_path,
                       ts_rank(mi.fts_content, plainto_tsquery('english', $1)) as rank
                FROM memory_items mi
                LEFT JOIN categories c ON mi.category_id = c.id
                WHERE mi.fts_content @@ plainto_tsquery('english', $1)
                ORDER BY rank DESC
                LIMIT $2
                """,
                query,
                limit,
            )
            
            return [
                MemoryItem(
                    id=row["id"],
                    content=row["content"],
                    category_path=row["category_path"] or "",
                    type=MemoryType(row["type"]),
                    confidence=row["confidence"],
                    importance=row["importance"],
                    mention_count=row.get("mention_count", 1),
                    source_resource_id=row["resource_id"],
                    created_at=row["created_at"],
                    last_accessed=row["last_accessed"],
                )
                for row in rows
            ]
    
    async def get_items_by_category(
        self,
        category_path: str,
        limit: int = 20,
    ) -> List[MemoryItem]:
        """Get all memory items in a specific category."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT mi.*, c.path as category_path
                FROM memory_items mi
                JOIN categories c ON mi.category_id = c.id
                WHERE c.path = $1 OR c.path LIKE $2
                ORDER BY mi.importance DESC, mi.last_accessed DESC
                LIMIT $3
                """,
                category_path,
                f"{category_path}/%",
                limit,
            )
            
            return [
                MemoryItem(
                    id=row["id"],
                    content=row["content"],
                    category_path=row["category_path"] or "",
                    type=MemoryType(row["type"]),
                    confidence=row["confidence"],
                    importance=row["importance"],
                    mention_count=row.get("mention_count", 1),
                    source_resource_id=row["resource_id"],
                    created_at=row["created_at"],
                    last_accessed=row["last_accessed"],
                )
                for row in rows
            ]
    
    async def get_stale_items(
        self,
        days_threshold: int = 30,
        limit: int = 100,
    ) -> List[MemoryItem]:
        """Get memory items that haven't been accessed recently."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT mi.*, c.path as category_path
                FROM memory_items mi
                LEFT JOIN categories c ON mi.category_id = c.id
                WHERE mi.last_accessed < NOW() - (INTERVAL '1 day' * $1)
                ORDER BY mi.importance ASC, mi.last_accessed ASC
                LIMIT $2
                """,
                days_threshold,
                limit,
            )
            
            return [
                MemoryItem(
                    id=row["id"],
                    content=row["content"],
                    category_path=row["category_path"] or "",
                    type=MemoryType(row["type"]),
                    confidence=row["confidence"],
                    importance=row["importance"],
                    mention_count=row.get("mention_count", 1),
                    source_resource_id=row["resource_id"],
                    created_at=row["created_at"],
                    last_accessed=row["last_accessed"],
                )
                for row in rows
            ]
    
    async def delete_memory_item(self, item_id: UUID) -> None:
        """Delete a memory item."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM memory_items WHERE id = $1",
                item_id,
            )
    
    async def get_recent_items(self, limit: int = 10) -> List[MemoryItem]:
        """Get most recently accessed memory items."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT mi.*, c.path as category_path
                FROM memory_items mi
                LEFT JOIN categories c ON mi.category_id = c.id
                ORDER BY mi.last_accessed DESC
                LIMIT $1
                """,
                limit,
            )
            
            return [
                MemoryItem(
                    id=row["id"],
                    content=row["content"],
                    category_path=row["category_path"] or "",
                    type=MemoryType(row["type"]),
                    confidence=row["confidence"],
                    importance=row["importance"],
                    mention_count=row.get("mention_count", 1),
                    source_resource_id=row["resource_id"],
                    created_at=row["created_at"],
                    last_accessed=row["last_accessed"],
                )
                for row in rows
            ]

    async def get_memories_since(
        self,
        since: datetime,
        limit: int = 100,
    ) -> List[MemoryItem]:
        """
        Fetch memory items created after the given datetime.
        
        Used by Daily Reflection to get recent memories for summarization.
        
        Args:
            since: Datetime threshold (exclusive)
            limit: Maximum number of items to return
            
        Returns:
            List of MemoryItems created after `since`, ordered by creation time
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT mi.*, c.path as category_path
                FROM memory_items mi
                LEFT JOIN categories c ON mi.category_id = c.id
                WHERE mi.created_at > $1
                ORDER BY mi.created_at ASC
                LIMIT $2
                """,
                since,
                limit,
            )
            
            return [
                MemoryItem(
                    id=row["id"],
                    content=row["content"],
                    category_path=row["category_path"] or "",
                    type=MemoryType(row["type"]),
                    confidence=row["confidence"],
                    importance=row["importance"],
                    mention_count=row.get("mention_count", 1),
                    source_resource_id=row["resource_id"],
                    created_at=row["created_at"],
                    last_accessed=row["last_accessed"],
                )
                for row in rows
            ]

    async def get_reflections_by_type(
        self,
        reflection_type: str,
        since: datetime,
        limit: int = 50,
    ) -> List[MemoryItem]:
        """
        Get reflection/summary memories by category path prefix.
        
        Args:
            reflection_type: Type prefix like 'timeline/daily', 'timeline/weekly'
            since: Only get reflections created after this date
            limit: Maximum number of items
            
        Returns:
            List of MemoryItems matching the category prefix
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT mi.*, c.path as category_path
                FROM memory_items mi
                LEFT JOIN categories c ON mi.category_id = c.id
                WHERE c.path LIKE $1 || '%'
                  AND mi.created_at > $2
                ORDER BY mi.created_at DESC
                LIMIT $3
                """,
                reflection_type,
                since,
                limit,
            )
            
            return [
                MemoryItem(
                    id=row["id"],
                    content=row["content"],
                    category_path=row["category_path"] or "",
                    type=MemoryType(row["type"]),
                    confidence=row["confidence"],
                    importance=row["importance"],
                    mention_count=row.get("mention_count", 1),
                    source_resource_id=row["resource_id"],
                    created_at=row["created_at"],
                    last_accessed=row["last_accessed"],
                )
                for row in rows
            ]

    async def list_items(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[MemoryItem]:
        """
        List memory items with pagination, sorted by creation date (newest first).
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT mi.*, c.path as category_path
                FROM memory_items mi
                LEFT JOIN categories c ON mi.category_id = c.id
                ORDER BY mi.created_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )
            
            return [
                MemoryItem(
                    id=row["id"],
                    content=row["content"],
                    category_path=row["category_path"] or "",
                    type=MemoryType(row["type"]),
                    confidence=row["confidence"],
                    importance=row["importance"],
                    source_resource_id=row["resource_id"],
                    created_at=row["created_at"],
                    last_accessed=row["last_accessed"],
                    is_active=row.get("is_active", True),
                )
                for row in rows
            ]

    async def count_items(self) -> int:
        """Get total number of memory items."""
        async with self._pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM memory_items")

    async def record_token_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int
    ) -> None:
        """Update cumulative token usage for a model."""
        if not self._pool:
            return
            
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO token_usage (model, prompt_tokens, completion_tokens, total_tokens, updated_at)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (model) DO UPDATE SET
                    prompt_tokens = token_usage.prompt_tokens + EXCLUDED.prompt_tokens,
                    completion_tokens = token_usage.completion_tokens + EXCLUDED.completion_tokens,
                    total_tokens = token_usage.total_tokens + EXCLUDED.total_tokens,
                    updated_at = NOW()
                """,
                model,
                prompt_tokens,
                completion_tokens,
                total_tokens,
            )

    # ========== Scheduled Task Operations ==========

    async def get_scheduled_tasks(self) -> List[dict]:
        """Get all scheduled tasks from the database."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, name, job_type, interval_seconds, enabled, is_system, 
                       last_run, next_run, created_at
                FROM scheduled_tasks
                ORDER BY is_system DESC, name
                """
            )
            return [
                {
                    "id": str(row["id"]),
                    "name": row["name"],
                    "job_type": row["job_type"],
                    "interval_seconds": row["interval_seconds"],
                    "enabled": row["enabled"],
                    "is_system": row["is_system"],
                    "last_run": row["last_run"].isoformat() if row["last_run"] else None,
                    "next_run": row["next_run"].isoformat() if row["next_run"] else None,
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                }
                for row in rows
            ]

    async def save_scheduled_task(
        self,
        name: str,
        job_type: str,
        interval_seconds: int,
        enabled: bool = True,
        is_system: bool = False,
    ) -> dict:
        """Save a scheduled task to the database."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO scheduled_tasks (name, job_type, interval_seconds, enabled, is_system)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (name) DO UPDATE SET
                    job_type = EXCLUDED.job_type,
                    interval_seconds = EXCLUDED.interval_seconds,
                    enabled = EXCLUDED.enabled
                RETURNING id, name, job_type, interval_seconds, enabled, is_system, 
                          last_run, next_run, created_at
                """,
                name,
                job_type,
                interval_seconds,
                enabled,
                is_system,
            )
            return {
                "id": str(row["id"]),
                "name": row["name"],
                "job_type": row["job_type"],
                "interval_seconds": row["interval_seconds"],
                "enabled": row["enabled"],
                "is_system": row["is_system"],
                "last_run": row["last_run"].isoformat() if row["last_run"] else None,
                "next_run": row["next_run"].isoformat() if row["next_run"] else None,
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }

    async def delete_scheduled_task(self, name: str) -> bool:
        """Delete a scheduled task by name. Returns True if deleted."""
        async with self._pool.acquire() as conn:
            # Don't allow deleting system tasks
            result = await conn.execute(
                """
                DELETE FROM scheduled_tasks 
                WHERE name = $1 AND is_system = false
                """,
                name,
            )
            return result == "DELETE 1"

    async def update_task_last_run(self, name: str, last_run: datetime = None) -> None:
        """Update the last_run timestamp for a task."""
        if last_run is None:
            last_run = datetime.now()
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE scheduled_tasks 
                SET last_run = $1, next_run = $1 + (interval_seconds * INTERVAL '1 second')
                WHERE name = $2
                """,
                last_run,
                name,
            )

    async def get_scheduled_task(self, name: str) -> Optional[dict]:
        """Get a scheduled task by name."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, name, job_type, interval_seconds, enabled, is_system, 
                       last_run, next_run, created_at
                FROM scheduled_tasks
                WHERE name = $1
                """,
                name,
            )
            if row:
                return {
                    "id": str(row["id"]),
                    "name": row["name"],
                    "job_type": row["job_type"],
                    "interval_seconds": row["interval_seconds"],
                    "enabled": row["enabled"],
                    "is_system": row["is_system"],
                    "last_run": row["last_run"].isoformat() if row["last_run"] else None,
                    "next_run": row["next_run"].isoformat() if row["next_run"] else None,
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                }
            return None

    # ========== Maintenance ==========
    
    async def optimize_database(self) -> None:
        """
        Run PostgreSQL maintenance tasks.
        
        Executes:
        - VACUUM: Reclaims storage occupied by dead tuples.
        - ANALYZE: Updates statistics used by the query planner.
        
        Note: VACUUM cannot be run inside a transaction block, 
        so we need to use isolation_level='autocommit' or similar.
        Asyncpg connection usually handles this if not in a transaction.
        """
        # We need a separate connection for VACUUM as it cannot run inside a transaction block
        # acquiring a connection from pool *might* be in implicit transaction depending on config,
        # but usually it's fine. However, asyncpg execute() wraps in prepared statement often.
        # Simplest way is to just run it.
        
        try:
            # Manually connect to ensure no transaction wrapping
            conn = await asyncpg.connect(self.connection_string)
            try:
                # VACUUM cannot run in a transaction block
                await conn.execute("VACUUM ANALYZE")
            finally:
                await conn.close()
        except Exception as e:
            print(f"DB Optimization warning: {e}")

    # =========================================================================
    # SEMANTIC TRIPLES (Entity-Level Memory)
    # =========================================================================

    async def create_triple(
        self,
        triple: SemanticTriple,
        subject_embedding: Optional[List[float]] = None,
        object_embedding: Optional[List[float]] = None,
    ) -> SemanticTriple:
        """
        Create a new semantic triple.
        
        Args:
            triple: SemanticTriple object to store
            subject_embedding: Optional embedding for subject
            object_embedding: Optional embedding for object
            
        Returns:
            Created SemanticTriple with assigned ID
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO semantic_triples 
                (id, memory_item_id, subject, predicate, object, context,
                 importance, confidence, is_active, subject_embedding, object_embedding,
                 created_at, last_accessed)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                triple.id,
                triple.memory_item_id,
                triple.subject,
                normalize_predicate(triple.predicate),
                triple.object,
                triple.context,
                triple.importance,
                triple.confidence,
                triple.is_active,
                str(subject_embedding) if subject_embedding else None,
                str(object_embedding) if object_embedding else None,
                triple.created_at,
                triple.last_accessed,
            )
        return triple

    async def search_triples_by_entity(
        self,
        entity: str,
        search_subject: bool = True,
        search_object: bool = True,
        active_only: bool = True,
        limit: int = 20,
    ) -> List[SemanticTriple]:
        """
        Search triples by subject or object entity name.
        
        Args:
            entity: Entity name to search for
            search_subject: Include subject matches
            search_object: Include object matches
            active_only: Only return active triples
            limit: Maximum results
            
        Returns:
            List of matching SemanticTriples
        """
        conditions = []
        if search_subject:
            conditions.append("LOWER(subject) = LOWER($1)")
        if search_object:
            conditions.append("LOWER(object) = LOWER($1)")
        
        where_entity = " OR ".join(conditions) if conditions else "FALSE"
        where_active = "AND is_active = TRUE" if active_only else ""
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT * FROM semantic_triples
                WHERE ({where_entity}) {where_active}
                ORDER BY importance DESC, last_accessed DESC
                LIMIT $2
                """,
                entity,
                limit,
            )
            
            return [self._row_to_triple(row) for row in rows]

    async def search_triples_semantic(
        self,
        query_embedding: List[float],
        limit: int = 10,
        threshold: float = 0.5,
        active_only: bool = True,
    ) -> List[SemanticTriple]:
        """
        Search triples by semantic similarity on object embedding.
        
        Args:
            query_embedding: Query vector
            limit: Maximum results
            threshold: Minimum similarity threshold
            active_only: Only return active triples
            
        Returns:
            List of semantically similar triples
        """
        where_active = "AND is_active = TRUE" if active_only else ""
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT *,
                       1 - (object_embedding <=> $1::vector) as similarity
                FROM semantic_triples
                WHERE object_embedding IS NOT NULL
                  AND 1 - (object_embedding <=> $1::vector) >= $2
                  {where_active}
                ORDER BY similarity DESC
                LIMIT $3
                """,
                str(query_embedding),
                threshold,
                limit,
            )
            
            return [self._row_to_triple(row) for row in rows]

    async def find_conflicting_triples(
        self,
        subject: str,
        predicate: str,
        new_object: Optional[str] = None,
        active_only: bool = True,
    ) -> List[SemanticTriple]:
        """
        Find triples that might conflict with a new triple.
        
        Conflict cases:
        1. Same subject + predicate, different object (for exclusive predicates)
        2. Same subject + object, opposite predicate (likes vs dislikes)
        
        Args:
            subject: Subject to match
            predicate: Predicate to match or find opposites
            new_object: Optional object for opposite predicate check
            active_only: Only check active triples
            
        Returns:
            List of potentially conflicting triples
        """
        normalized_pred = normalize_predicate(predicate)
        where_active = "AND is_active = TRUE" if active_only else ""
        
        # Opposite predicate pairs
        opposite_map = {
            "likes": "dislikes",
            "dislikes": "likes",
            "loves": "hates",
            "hates": "loves",
            "wants": "avoids",
            "avoids": "wants",
            "is": "is_not",
            "is_not": "is",
            "can": "cannot",
            "cannot": "can",
        }
        
        opposite_pred = opposite_map.get(normalized_pred)
        
        async with self._pool.acquire() as conn:
            # Case 1: Same subject + predicate (different object will be filtered by caller)
            rows = await conn.fetch(
                f"""
                SELECT * FROM semantic_triples
                WHERE LOWER(subject) = LOWER($1)
                  AND predicate = $2
                  {where_active}
                """,
                subject,
                normalized_pred,
            )
            
            results = [self._row_to_triple(row) for row in rows]
            
            # Case 2: Opposite predicate with same object
            if opposite_pred and new_object:
                opposite_rows = await conn.fetch(
                    f"""
                    SELECT * FROM semantic_triples
                    WHERE LOWER(subject) = LOWER($1)
                      AND predicate = $2
                      AND LOWER(object) = LOWER($3)
                      {where_active}
                    """,
                    subject,
                    opposite_pred,
                    new_object,
                )
                results.extend([self._row_to_triple(row) for row in opposite_rows])
            
            return results

    async def supersede_triple(
        self,
        old_triple_id: UUID,
        new_triple_id: UUID,
    ) -> bool:
        """
        Mark an old triple as superseded by a new one.
        
        Args:
            old_triple_id: Triple to mark as inactive
            new_triple_id: The new triple that replaces it
            
        Returns:
            True if supersede was successful
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE semantic_triples
                SET is_active = FALSE,
                    superseded_by = $2,
                    last_accessed = NOW()
                WHERE id = $1
                """,
                old_triple_id,
                new_triple_id,
            )
            return result == "UPDATE 1"

    async def get_triples_for_memory_item(
        self,
        memory_item_id: UUID,
        active_only: bool = False,
    ) -> List[SemanticTriple]:
        """
        Get all triples associated with a memory item.
        
        Args:
            memory_item_id: The memory item ID
            active_only: Only return active triples
            
        Returns:
            List of associated triples
        """
        where_active = "AND is_active = TRUE" if active_only else ""
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT * FROM semantic_triples
                WHERE memory_item_id = $1 {where_active}
                ORDER BY created_at
                """,
                memory_item_id,
            )
            
            return [self._row_to_triple(row) for row in rows]

    async def list_triples(
        self,
        limit: int = 50,
        offset: int = 0,
        active_only: bool = False,
    ) -> List[SemanticTriple]:
        """
        List triples with pagination.
        
        Args:
            limit: Maximum results
            offset: Pagination offset
            active_only: Only return active triples
            
        Returns:
            List of triples
        """
        where_active = "WHERE is_active = TRUE" if active_only else ""
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT * FROM semantic_triples
                {where_active}
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )
            
            return [self._row_to_triple(row) for row in rows]

    async def count_triples(self, active_only: bool = False) -> int:
        """Count total triples."""
        where_active = "WHERE is_active = TRUE" if active_only else ""
        
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                f"SELECT COUNT(*) FROM semantic_triples {where_active}"
            )

    def _row_to_triple(self, row) -> SemanticTriple:
        """Convert database row to SemanticTriple object."""
        return SemanticTriple(
            id=row["id"],
            memory_item_id=row["memory_item_id"],
            subject=row["subject"],
            predicate=row["predicate"],
            object=row["object"],
            context=row["context"],
            importance=row["importance"],
            confidence=row["confidence"],
            is_active=row["is_active"],
            created_at=row["created_at"],
            last_accessed=row["last_accessed"],
        )

    # =============================================================================
    # Lazy Triple Extraction (pending processing)
    # =============================================================================
    
    async def mark_pending_triple_extraction(self, item_id: UUID) -> None:
        """
        Mark a memory item as pending triple extraction.
        
        Uses a simple approach: store in metadata JSON.
        This avoids schema changes while still tracking pending status.
        """
        async with self._pool.acquire() as conn:
            # Store pending status in resources.metadata
            # We look up the resource_id from the memory item
            row = await conn.fetchrow(
                "SELECT resource_id FROM memory_items WHERE id = $1",
                item_id
            )
            
            if row and row["resource_id"]:
                await conn.execute(
                    """
                    UPDATE resources 
                    SET metadata = COALESCE(metadata, '{}')::jsonb || '{"pending_triple_extraction": true}'::jsonb
                    WHERE id = $1
                    """,
                    row["resource_id"]
                )

    async def get_pending_triple_items(self, limit: int = 50) -> List[MemoryItem]:
        """
        Get memory items that need triple extraction (Lazy Evaluation).
        
        Returns items where:
        1. The associated resource has pending_triple_extraction = true
        2. The item has no triples yet
        
        Returns:
            List of MemoryItems needing triple extraction
        """
        async with self._pool.acquire() as conn:
            # Find items with pending flag or no triples yet
            rows = await conn.fetch(
                """
                SELECT DISTINCT mi.*, c.path as category_path
                FROM memory_items mi
                LEFT JOIN categories c ON mi.category_id = c.id
                LEFT JOIN resources r ON mi.resource_id = r.id
                LEFT JOIN semantic_triples st ON st.memory_item_id = mi.id
                WHERE mi.is_active = TRUE
                AND (
                    -- Has explicit pending flag
                    (r.metadata->>'pending_triple_extraction')::boolean = true
                    OR
                    -- Has no triples yet (implicit pending)
                    st.id IS NULL
                )
                ORDER BY mi.created_at DESC
                LIMIT $1
                """,
                limit
            )
            
            return [self._row_to_memory_item(row) for row in rows]

    async def clear_pending_triple_flag(self, item_id: UUID) -> None:
        """
        Clear the pending triple extraction flag after successful extraction.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT resource_id FROM memory_items WHERE id = $1",
                item_id
            )
            
            if row and row["resource_id"]:
                await conn.execute(
                    """
                    UPDATE resources 
                    SET metadata = metadata - 'pending_triple_extraction'
                    WHERE id = $1
                    """,
                    row["resource_id"]
                )

    async def count_pending_triple_items(self) -> int:
        """Count memory items pending triple extraction."""
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                """
                SELECT COUNT(DISTINCT mi.id)
                FROM memory_items mi
                LEFT JOIN resources r ON mi.resource_id = r.id
                LEFT JOIN semantic_triples st ON st.memory_item_id = mi.id
                WHERE mi.is_active = TRUE
                AND (
                    (r.metadata->>'pending_triple_extraction')::boolean = true
                    OR st.id IS NULL
                )
                """
            )
