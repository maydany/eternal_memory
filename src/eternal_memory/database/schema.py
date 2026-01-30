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
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed TIMESTAMPTZ DEFAULT NOW()
);

-- Full Text Search column (PostgreSQL 12+ requires explicit ADD COLUMN)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'memory_items' AND column_name = 'fts_content'
    ) THEN
        ALTER TABLE memory_items ADD COLUMN fts_content TSVECTOR 
            GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;
    END IF;
END $$;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_memory_embedding 
    ON memory_items USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_memory_fts 
    ON memory_items USING GIN (fts_content);
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
    
    async def initialize(self) -> None:
        """
        Create all tables and indexes if they don't exist.
        """
        conn = await asyncpg.connect(self.connection_string)
        try:
            await conn.execute(SCHEMA_SQL)
        finally:
            await conn.close()
    
    async def drop_all(self) -> None:
        """
        Drop all tables. USE WITH CAUTION - this destroys all data.
        """
        drop_sql = """
        DROP TABLE IF EXISTS memory_items CASCADE;
        DROP TABLE IF EXISTS categories CASCADE;
        DROP TABLE IF EXISTS resources CASCADE;
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
            
            # Fetch DB size
            stats["db_size"] = await conn.fetchval("SELECT pg_size_pretty(pg_database_size(current_database()))")
            stats["connected"] = True
            
            return stats
        finally:
            await conn.close()
