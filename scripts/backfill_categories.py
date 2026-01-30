
import asyncio
import os
from pathlib import Path
from eternal_memory.config import load_config
from eternal_memory.database.repository import MemoryRepository
from eternal_memory.llm.client import LLMClient

async def backfill():
    # Load .env
    env_path = Path.home() / ".openclaw" / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    os.environ[k] = v

    config = load_config()
    repo = MemoryRepository(config.database.connection_string)
    await repo.connect()
    
    llm = LLMClient(config.llm.api_key)
    
    categories = await repo.get_all_categories()
    print(f"Found {len(categories)} categories to backfill.")
    
    for cat in categories:
        print(f"Backfilling {cat.path}...")
        emb = await llm.generate_embedding(cat.name)
        await repo.create_category(cat, embedding=emb)
        
    await repo.disconnect()
    print("Done!")

if __name__ == "__main__":
    asyncio.run(backfill())
