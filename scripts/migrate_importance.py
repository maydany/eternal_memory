#!/usr/bin/env python3
"""
Migration Script: Re-evaluate Importance Scores using LLM

This script re-evaluates all existing memory items' importance scores
using the Generative Agents-style LLM rating (1-10 scale → 0.0-1.0).

Usage:
    cd /path/to/eternal_memory
    source .venv/bin/activate
    python scripts/migrate_importance.py
    
Options:
    --dry-run    Show what would be updated without making changes
    --batch-size Number of items to process at once (default: 10)
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eternal_memory.config import load_config
from eternal_memory.database.repository import MemoryRepository
from eternal_memory.llm.client import LLMClient


async def migrate_importance(dry_run: bool = False, batch_size: int = 10):
    """Re-evaluate importance for all memory items."""
    print("=" * 60)
    print("Memory Importance Re-evaluation Migration")
    print("Based on Generative Agents (Park et al., 2023)")
    print("=" * 60)
    
    # Load config
    config = load_config()
    
    # Initialize repository
    repo = MemoryRepository(config.database.connection_string)
    await repo.connect()
    
    # Initialize LLM client
    llm = LLMClient(
        api_key=config.llm.api_key,
        model=config.llm.model,
    )
    
    try:
        # Get total count
        total_count = await repo.count_items()
        print(f"\nTotal memory items: {total_count}")
        
        if dry_run:
            print("\n🔍 DRY RUN MODE - No changes will be made\n")
        else:
            print(f"\n⚠️  This will update importance for all {total_count} items")
            print("Press Ctrl+C to cancel, or wait 5 seconds to continue...")
            await asyncio.sleep(5)
        
        # Process in batches
        offset = 0
        updated_count = 0
        skipped_count = 0
        
        while offset < total_count:
            items = await repo.list_items(limit=batch_size, offset=offset)
            
            if not items:
                break
            
            print(f"\nProcessing batch {offset // batch_size + 1} ({offset + 1}-{offset + len(items)} of {total_count})")
            
            for item in items:
                try:
                    # Get LLM importance rating
                    new_importance = await llm.rate_importance(item.content)
                    
                    old_importance = item.importance
                    change = new_importance - old_importance
                    
                    # Show what would change
                    change_symbol = "↑" if change > 0.05 else ("↓" if change < -0.05 else "→")
                    print(f"  {change_symbol} {old_importance:.2f} → {new_importance:.2f} | {item.content[:50]}...")
                    
                    if not dry_run and abs(change) > 0.01:
                        # Update in database
                        await repo._pool.execute(
                            """
                            UPDATE memory_items 
                            SET importance = $2
                            WHERE id = $1
                            """,
                            item.id,
                            new_importance,
                        )
                        updated_count += 1
                    else:
                        skipped_count += 1
                        
                except Exception as e:
                    print(f"  ⚠️ Error processing item {item.id}: {e}")
                    skipped_count += 1
            
            offset += batch_size
            
            # Rate limiting pause
            await asyncio.sleep(0.5)
        
        # Summary
        print("\n" + "=" * 60)
        print("Migration Complete")
        print("=" * 60)
        print(f"Total items: {total_count}")
        print(f"Updated: {updated_count}")
        print(f"Skipped: {skipped_count}")
        
        if dry_run:
            print("\n💡 Run without --dry-run to apply changes")
        else:
            print("\n✅ Importance scores updated successfully!")
            
    finally:
        await repo.disconnect()


def main():
    parser = argparse.ArgumentParser(
        description="Re-evaluate memory importance scores using LLM"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of items to process at once (default: 10)"
    )
    
    args = parser.parse_args()
    
    asyncio.run(migrate_importance(
        dry_run=args.dry_run,
        batch_size=args.batch_size
    ))


if __name__ == "__main__":
    main()
