#!/usr/bin/env python3
"""
Migration Script: Fix Orphaned Active MemoryItems

This script fixes data inconsistency where MemoryItems are still active
but ALL their associated semantic triples have been superseded (inactive).

Issue: 
- When triples were superseded, the parent MemoryItem was not deactivated
- This caused inactive entities (e.g., 박주연) to still appear in search results

Solution:
- Find all MemoryItems where ALL triples are inactive
- Mark those MemoryItems as inactive to maintain consistency

Usage:
    # Dry run (see what would be changed):
    python scripts/fix_orphan_memories.py --dry-run
    
    # Execute the fix:
    python scripts/fix_orphan_memories.py

Reference: Bug fix in repository.py supersede_triple() - 2026-02-01
"""

import asyncio
import argparse
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from eternal_memory.database.repository import MemoryRepository


async def find_orphan_memories(repo: MemoryRepository) -> list:
    """
    Find MemoryItems that are active but have ALL triples inactive.
    
    Returns:
        List of tuples: (memory_item_id, content, total_triples, active_triples)
    """
    async with repo._pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT 
                mi.id,
                mi.content,
                mi.is_active as mem_active,
                COUNT(st.id) as total_triples,
                COUNT(CASE WHEN st.is_active THEN 1 END) as active_triples
            FROM memory_items mi
            INNER JOIN semantic_triples st ON st.memory_item_id = mi.id
            WHERE mi.is_active = TRUE
            GROUP BY mi.id, mi.content, mi.is_active
            HAVING COUNT(st.id) > 0 AND COUNT(CASE WHEN st.is_active THEN 1 END) = 0
            ORDER BY mi.created_at DESC
            """
        )
        return [(row["id"], row["content"], row["total_triples"], row["active_triples"]) for row in rows]


async def fix_orphan_memories(repo: MemoryRepository, dry_run: bool = True) -> int:
    """
    Deactivate MemoryItems where all triples are inactive.
    
    Args:
        repo: MemoryRepository instance
        dry_run: If True, only report what would be changed
        
    Returns:
        Number of MemoryItems fixed
    """
    orphans = await find_orphan_memories(repo)
    
    if not orphans:
        print("✅ No orphan memories found. Database is consistent.")
        return 0
    
    print(f"\n🔍 Found {len(orphans)} orphan memories (active MemoryItem with all inactive triples):\n")
    
    for mem_id, content, total, active in orphans:
        content_preview = content[:80] + "..." if len(content) > 80 else content
        print(f"  📝 {mem_id}")
        print(f"     Content: {content_preview}")
        print(f"     Triples: {total} total, {active} active")
        print()
    
    if dry_run:
        print(f"🔶 DRY RUN: Would deactivate {len(orphans)} MemoryItems")
        print("   Run without --dry-run to apply changes.")
        return 0
    
    # Execute the fix
    async with repo._pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE memory_items mi
            SET is_active = FALSE, last_accessed = NOW()
            WHERE mi.id IN (
                SELECT mi2.id
                FROM memory_items mi2
                INNER JOIN semantic_triples st ON st.memory_item_id = mi2.id
                WHERE mi2.is_active = TRUE
                GROUP BY mi2.id
                HAVING COUNT(st.id) > 0 AND COUNT(CASE WHEN st.is_active THEN 1 END) = 0
            )
            """
        )
        
        # Parse result like "UPDATE 5"
        count = int(result.split()[1]) if result and result.startswith("UPDATE") else 0
        
    print(f"✅ Fixed {count} orphan MemoryItems (marked as inactive)")
    return count


async def main():
    parser = argparse.ArgumentParser(
        description="Fix orphan active MemoryItems with all inactive triples"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only show what would be changed, don't modify database"
    )
    parser.add_argument(
        "--db-url",
        default=os.getenv("DATABASE_URL", "postgresql://127.0.0.1/eternal_memory"),
        help="Database connection URL"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Orphan Memory Fix Script")
    print("=" * 60)
    print(f"Database: {args.db_url}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'EXECUTE'}")
    print("=" * 60)
    
    repo = MemoryRepository(connection_string=args.db_url)
    await repo.connect()
    
    try:
        await fix_orphan_memories(repo, dry_run=args.dry_run)
    finally:
        await repo.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
