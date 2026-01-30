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
                    (id, category_id, resource_id, content, embedding, type, importance, confidence, created_at, last_accessed)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                    item.id,
                category_id,
                item.source_resource_id,
                item.content,
                str(embedding),  # pgvector accepts string format
                item.type,
                item.importance,
                item.confidence,
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
                    source_resource_id=row["resource_id"],
                    created_at=row["created_at"],
                    last_accessed=row["last_accessed"],
                )
                # Attach score metadata if needed, or just return sorted
                items.append(item)
            
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
                WHERE mi.last_accessed < NOW() - INTERVAL '%s days'
                ORDER BY mi.importance ASC, mi.last_accessed ASC
                LIMIT $1
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
                )
                for row in rows
            ]

    async def count_items(self) -> int:
        """Get total number of memory items."""
        async with self._pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM memory_items")
