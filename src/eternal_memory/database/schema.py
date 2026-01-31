"""
Database Schema

Defines and creates the PostgreSQL schema with pgvector extension
as specified in eternal_memory_spec.md Section 3.
"""

import asyncpg

# SQL Schema as defined in the specification
SCHEMA_SQL = """
-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 1. Resources: Raw Data Source
CREATE TABLE IF NOT EXISTS resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    uri TEXT NOT NULL,                          -- File path or URL
    modality VARCHAR(50) NOT NULL,              -- 'text', 'image', 'conversation'
    content TEXT,                               -- Full text content
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB                              -- Extra info (sender, app context)
);

-- 2. Memory Categories: Semantic Clusters
CREATE TABLE IF NOT EXISTS categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    parent_id UUID REFERENCES categories(id),
    summary TEXT,                               -- High-level summary of contained items
    path TEXT NOT NULL UNIQUE,                  -- Full path like 'knowledge/coding/python'
    embedding vector(1536),                     -- Category embedding for semantic matching
    last_accessed TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Memory Items: Extracted Facts
CREATE TABLE IF NOT EXISTS memory_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID REFERENCES categories(id),
    resource_id UUID REFERENCES resources(id),
    content TEXT NOT NULL,                      -- The actual fact/memory
    embedding vector(1536),                     -- Vector for RAG (OpenAI ada-002 compatible)
    type VARCHAR(20) DEFAULT 'fact',            -- fact, preference, event, plan
    importance FLOAT DEFAULT 0.5,               -- 0.0 to 1.0 (Salience)
    confidence FLOAT DEFAULT 1.0,               -- 0.0 to 1.0
    mention_count INTEGER DEFAULT 1,            -- Reinforcement counter
    is_active BOOLEAN DEFAULT TRUE,             -- Soft delete for superseded memories
    superseded_by UUID REFERENCES memory_items(id),  -- MemGPT-style replacement tracking
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Token Usage: Cost Tracking
CREATE TABLE IF NOT EXISTS token_usage (
    model TEXT PRIMARY KEY,
    prompt_tokens BIGINT DEFAULT 0,
    completion_tokens BIGINT DEFAULT 0,
    total_tokens BIGINT DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Scheduled Tasks: Persistent Job Registry
CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    job_type TEXT NOT NULL,
    interval_seconds INT NOT NULL,
    enabled BOOLEAN DEFAULT true,
    is_system BOOLEAN DEFAULT false,
    last_run TIMESTAMPTZ,
    next_run TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Semantic Triples: Entity-Level Memory (LangMem-style)
CREATE TABLE IF NOT EXISTS semantic_triples (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_item_id UUID REFERENCES memory_items(id) ON DELETE CASCADE,
    
    -- Triple components
    subject TEXT NOT NULL,                      -- "User", "Alice", "Python"
    predicate TEXT NOT NULL,                    -- "likes", "knows", "is_born_on"
    object TEXT NOT NULL,                       -- "apples", "coding", "1990-01-01"
    context TEXT,                               -- Optional: "since 2020", "very much"
    
    -- Metadata
    importance FLOAT DEFAULT 0.5,
    confidence FLOAT DEFAULT 1.0,
    is_active BOOLEAN DEFAULT TRUE,
    superseded_by UUID REFERENCES semantic_triples(id),
    
    -- Embeddings for semantic search
    subject_embedding vector(1536),
    object_embedding vector(1536),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_memory_embedding 
    ON memory_items USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_category_embedding 
    ON categories USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_memory_trgm 
    ON memory_items USING gin (content gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_category_parent 
    ON categories(parent_id);
CREATE INDEX IF NOT EXISTS idx_category_path 
    ON categories(path);
CREATE INDEX IF NOT EXISTS idx_memory_category 
    ON memory_items(category_id);
CREATE INDEX IF NOT EXISTS idx_memory_importance 
    ON memory_items(importance DESC);
CREATE INDEX IF NOT EXISTS idx_memory_last_accessed 
    ON memory_items(last_accessed DESC);

-- Triple-specific indexes
CREATE INDEX IF NOT EXISTS idx_triple_subject 
    ON semantic_triples(subject);
CREATE INDEX IF NOT EXISTS idx_triple_predicate 
    ON semantic_triples(predicate);
CREATE INDEX IF NOT EXISTS idx_triple_object_trgm 
    ON semantic_triples USING gin (object gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_triple_subject_embed 
    ON semantic_triples USING hnsw (subject_embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_triple_object_embed 
    ON semantic_triples USING hnsw (object_embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_triple_is_active 
    ON semantic_triples(is_active);
CREATE INDEX IF NOT EXISTS idx_triple_memory_item 
    ON semantic_triples(memory_item_id);
"""


class DatabaseSchema:
    """
    Manages PostgreSQL database schema creation and migrations.
    """
    
    def __init__(self, connection_string: str = None):
        """
        Initialize schema manager.
        
        Args:
            connection_string: PostgreSQL connection string.
                             Defaults to local 'eternal_memory' database.
        """
        self.connection_string = connection_string or "postgresql://localhost/eternal_memory"
        self._initialized = False
    
    async def initialize(self) -> None:
        """
        Create all tables and indexes if they don't exist.
        """
        if self._initialized:
            return
        
        conn = await asyncpg.connect(self.connection_string)
        try:
            await conn.execute(SCHEMA_SQL)
            
            # Migration for existing databases: Add mention_count if it doesn't exist
            try:
                await conn.execute("ALTER TABLE memory_items ADD COLUMN IF NOT EXISTS mention_count INTEGER DEFAULT 1")
                # MemGPT-style supersede columns
                await conn.execute("ALTER TABLE memory_items ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE")
                await conn.execute("ALTER TABLE memory_items ADD COLUMN IF NOT EXISTS superseded_by UUID REFERENCES memory_items(id)")
            except Exception:
                # Fallback for older Postgres versions or if column exists and IF NOT EXISTS is not supported
                pass
        finally:
            await conn.close()
        
        self._initialized = True
    
    async def drop_all(self) -> None:
        """
        Drop all tables. USE WITH CAUTION - this destroys all data.
        """
        drop_sql = """
        DROP TABLE IF EXISTS semantic_triples CASCADE;
        DROP TABLE IF EXISTS memory_items CASCADE;
        DROP TABLE IF EXISTS categories CASCADE;
        DROP TABLE IF EXISTS resources CASCADE;
        DROP TABLE IF EXISTS token_usage CASCADE;
        DROP TABLE IF EXISTS scheduled_tasks CASCADE;
        """
        conn = await asyncpg.connect(self.connection_string)
        try:
            await conn.execute(drop_sql)
        finally:
            await conn.close()
    
    async def get_stats(self) -> dict:
        """
        Get database statistics.
        """
        conn = await asyncpg.connect(self.connection_string)
        try:
            stats = {}
            stats["resources"] = await conn.fetchval("SELECT COUNT(*) FROM resources")
            stats["categories"] = await conn.fetchval("SELECT COUNT(*) FROM categories")
            stats["memory_items"] = await conn.fetchval("SELECT COUNT(*) FROM memory_items")
            
            # Fetch token usage
            token_rows = await conn.fetch("SELECT model, prompt_tokens, completion_tokens, total_tokens FROM token_usage")
            stats["token_usage"] = [
                {
                    "model": row["model"],
                    "prompt": row["prompt_tokens"],
                    "completion": row["completion_tokens"],
                    "total": row["total_tokens"],
                }
                for row in token_rows
            ]

            # Fetch DB size
            stats["db_size"] = await conn.fetchval("SELECT pg_size_pretty(pg_database_size(current_database()))")
            stats["connected"] = True
            
            return stats
        finally:
            await conn.close()
