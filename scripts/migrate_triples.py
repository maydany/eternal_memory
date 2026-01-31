#!/usr/bin/env python3
"""
Migration Script: Extract Triples from Existing Memories

This script extracts Subject-Predicate-Object triples from all existing
memory items and stores them in the semantic_triples table.

Usage:
    cd /path/to/eternal_memory
    source .venv/bin/activate
    python scripts/migrate_triples.py
    
Options:
    --dry-run    Show what would be extracted without saving
    --batch-size Number of items to process at once (default: 5)
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
from eternal_memory.models.semantic_triple import SemanticTriple


async def migrate_triples(dry_run: bool = False, batch_size: int = 5):
    """Extract triples from all existing memory items."""
    print("=" * 60)
    print("Triple Extraction Migration")
    print("Based on LangMem (LangChain, 2024)")
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
        existing_triples = await repo.count_triples()
        
        print(f"\nTotal memory items: {total_count}")
        print(f"Existing triples: {existing_triples}")
        
        if dry_run:
            print("\n🔍 DRY RUN MODE - No changes will be made\n")
        else:
            print(f"\n⚠️  This will extract triples from all {total_count} memories")
            print("Press Ctrl+C to cancel, or wait 3 seconds to continue...")
            await asyncio.sleep(3)
        
        # Process in batches
        offset = 0
        total_triples = 0
        error_count = 0
        
        while offset < total_count:
            items = await repo.list_items(limit=batch_size, offset=offset)
            
            if not items:
                break
            
            print(f"\nBatch {offset // batch_size + 1} ({offset + 1}-{offset + len(items)} of {total_count})")
            
            for item in items:
                try:
                    # Check if triples already exist for this item
                    existing = await repo.get_triples_for_memory_item(item.id, active_only=False)
                    if existing:
                        print(f"  ⏭️  Skip (has {len(existing)} triples): {item.content[:40]}...")
                        continue
                    
                    # Extract triples using LLM
                    triple_dicts = await llm.extract_triples(item.content)
                    
                    if not triple_dicts:
                        print(f"  ∅  No triples: {item.content[:50]}...")
                        continue
                    
                    print(f"  📦 {len(triple_dicts)} triples: {item.content[:40]}...")
                    
                    for t in triple_dicts:
                        triple = SemanticTriple(
                            memory_item_id=item.id,
                            subject=t["subject"],
                            predicate=t["predicate"],
                            object=t["object"],
                            context=t.get("context"),
                            importance=item.importance,
                        )
                        
                        print(f"      ({triple.subject}, {triple.predicate}, {triple.object})")
                        
                        if not dry_run:
                            # Generate embedding for object
                            obj_embedding = await llm.generate_embedding(triple.object)
                            
                            # Store triple
                            await repo.create_triple(
                                triple=triple,
                                subject_embedding=None,
                                object_embedding=obj_embedding,
                            )
                            total_triples += 1
                        else:
                            total_triples += 1
                        
                except Exception as e:
                    print(f"  ⚠️  Error: {item.id[:8]}... - {e}")
                    error_count += 1
            
            offset += batch_size
            
            # Rate limiting pause
            await asyncio.sleep(0.5)
        
        # Summary
        print("\n" + "=" * 60)
        print("Migration Complete")
        print("=" * 60)
        print(f"Total memories: {total_count}")
        print(f"Triples extracted: {total_triples}")
        print(f"Errors: {error_count}")
        
        if dry_run:
            print("\n💡 Run without --dry-run to save triples")
        else:
            print("\n✅ Triples extracted and saved!")
            
    finally:
        await repo.disconnect()


def main():
    parser = argparse.ArgumentParser(
        description="Extract triples from existing memory items"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be extracted without saving"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Number of items to process at once (default: 5)"
    )
    
    args = parser.parse_args()
    
    asyncio.run(migrate_triples(
        dry_run=args.dry_run,
        batch_size=args.batch_size
    ))


if __name__ == "__main__":
    main()
