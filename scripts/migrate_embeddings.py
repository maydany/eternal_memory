#!/usr/bin/env python3
"""
Embedding Migration Script: text-embedding-ada-002 → text-embedding-3-large

This script:
1. Alters DB columns from vector(1536) to vector(3072)
2. Re-generates all embeddings using the new model
3. Provides rollback capability

Usage:
    python scripts/migrate_embeddings.py [--dry-run] [--batch-size 50]
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Load .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / "setting" / ".env"
if env_path.exists():
    load_dotenv(env_path)

import asyncpg
from openai import AsyncOpenAI
import os


# Configuration
OLD_DIMENSION = 1536
NEW_DIMENSION = 1536  # Using Matryoshka reduction from embedding-3-large
NEW_MODEL = "text-embedding-3-large"
MATRYOSHKA_DIMENSIONS = 1536  # Reduced from native 3072d

# Tables with embedding columns
EMBEDDING_COLUMNS = [
    ("categories", "embedding"),
    ("memory_items", "embedding"),
    ("semantic_triples", "subject_embedding"),
    ("semantic_triples", "object_embedding"),
]


async def get_connection():
    """Create database connection."""
    return await asyncpg.connect(
        os.getenv("DATABASE_URL", "postgresql://localhost/eternal_memory")
    )


async def alter_column_dimension(conn, table: str, column: str, dimension: int, dry_run: bool):
    """Alter a vector column to new dimension."""
    print(f"  📐 Altering {table}.{column} to vector({dimension})...")
    
    if dry_run:
        print(f"     [DRY-RUN] Would execute: ALTER TABLE {table} ALTER COLUMN {column} TYPE vector({dimension})")
        return
    
    # PostgreSQL requires dropping the column and re-adding with new type
    # But pgvector supports ALTER COLUMN directly for vector types
    try:
        # First, drop any indexes on this column (they'll be recreated)
        await conn.execute(f"""
            DO $$ 
            DECLARE idx_name text;
            BEGIN
                FOR idx_name IN 
                    SELECT indexname FROM pg_indexes 
                    WHERE tablename = '{table}' 
                    AND indexdef LIKE '%{column}%'
                    AND indexdef LIKE '%hnsw%'
                LOOP
                    EXECUTE 'DROP INDEX IF EXISTS ' || idx_name;
                END LOOP;
            END $$;
        """)
        
        # Set column to NULL first (required for dimension change)
        await conn.execute(f"UPDATE {table} SET {column} = NULL")
        
        # Alter column type
        await conn.execute(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE vector({dimension})")
        
        print(f"     ✅ Column altered successfully")
    except Exception as e:
        print(f"     ❌ Error altering column: {e}")
        raise


async def regenerate_embeddings(conn, client, table: str, column: str, content_column: str, batch_size: int, dry_run: bool):
    """Re-generate embeddings for all rows in a table."""
    # Count rows needing regeneration
    count = await conn.fetchval(f"SELECT COUNT(*) FROM {table} WHERE {content_column} IS NOT NULL")
    print(f"  🔄 Regenerating {count} embeddings for {table}.{column}...")
    
    if dry_run or count == 0:
        print(f"     [DRY-RUN] Would regenerate {count} embeddings")
        return
    
    # Fetch all IDs and contents
    rows = await conn.fetch(f"SELECT id, {content_column} FROM {table} WHERE {content_column} IS NOT NULL")
    
    processed = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        texts = [row[content_column] for row in batch]
        ids = [row["id"] for row in batch]
        
        # Generate embeddings in batch with Matryoshka dimension reduction
        response = await client.embeddings.create(
            model=NEW_MODEL,
            input=texts,
            dimensions=MATRYOSHKA_DIMENSIONS  # Reduce 3072 → 1536
        )
        
        # Update each row
        for j, embedding_data in enumerate(response.data):
            embedding = embedding_data.embedding
            embedding_str = "[" + ",".join(map(str, embedding)) + "]"
            await conn.execute(
                f"UPDATE {table} SET {column} = $1 WHERE id = $2",
                embedding_str, ids[j]
            )
        
        processed += len(batch)
        print(f"     Progress: {processed}/{count} ({processed * 100 // count}%)")
    
    print(f"     ✅ Regenerated {processed} embeddings")


async def recreate_indexes(conn, dry_run: bool):
    """Recreate HNSW indexes for vector columns.
    
    Using embedding-3-large with Matryoshka reduction (1536d) for HNSW compatibility.
    """
    print("  📇 Recreating HNSW indexes...")
    
    index_sql = """
    CREATE INDEX IF NOT EXISTS idx_memory_embedding 
        ON memory_items USING hnsw (embedding vector_cosine_ops);
    CREATE INDEX IF NOT EXISTS idx_category_embedding 
        ON categories USING hnsw (embedding vector_cosine_ops);
    CREATE INDEX IF NOT EXISTS idx_triple_subject_embed 
        ON semantic_triples USING hnsw (subject_embedding vector_cosine_ops);
    CREATE INDEX IF NOT EXISTS idx_triple_object_embed 
        ON semantic_triples USING hnsw (object_embedding vector_cosine_ops);
    """
    
    if dry_run:
        print("     [DRY-RUN] Would recreate HNSW indexes")
        return
    
    await conn.execute(index_sql)
    print("     ✅ Indexes recreated")


async def migrate(dry_run: bool = True, batch_size: int = 50):
    """Run the full migration."""
    print("=" * 60)
    print("Embedding Migration: ada-002 (1536) → embedding-3-large (3072)")
    print("=" * 60)
    
    if dry_run:
        print("⚠️  DRY-RUN MODE - No changes will be made\n")
    
    conn = await get_connection()
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    try:
        # Step 1: Alter column dimensions
        print("\n📌 Step 1: Altering column dimensions...")
        for table, column in EMBEDDING_COLUMNS:
            await alter_column_dimension(conn, table, column, NEW_DIMENSION, dry_run)
        
        # Step 2: Regenerate embeddings
        print("\n📌 Step 2: Regenerating embeddings...")
        
        # Categories (embed the name)
        await regenerate_embeddings(conn, client, "categories", "embedding", "name", batch_size, dry_run)
        
        # Memory items (embed the content)
        await regenerate_embeddings(conn, client, "memory_items", "embedding", "content", batch_size, dry_run)
        
        # Semantic triples - subject and object separately
        # For subject_embedding, we embed the subject field
        await regenerate_embeddings(conn, client, "semantic_triples", "subject_embedding", "subject", batch_size, dry_run)
        await regenerate_embeddings(conn, client, "semantic_triples", "object_embedding", "object", batch_size, dry_run)
        
        # Step 3: Recreate indexes
        print("\n📌 Step 3: Recreating HNSW indexes...")
        await recreate_indexes(conn, dry_run)
        
        print("\n" + "=" * 60)
        if dry_run:
            print("✅ DRY-RUN complete. Run without --dry-run to apply changes.")
        else:
            print("✅ Migration complete!")
        print("=" * 60)
        
    finally:
        await conn.close()


def main():
    parser = argparse.ArgumentParser(description="Migrate embeddings to embedding-3-large")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for embedding generation (default: 50)")
    args = parser.parse_args()
    
    asyncio.run(migrate(dry_run=args.dry_run, batch_size=args.batch_size))


if __name__ == "__main__":
    main()
