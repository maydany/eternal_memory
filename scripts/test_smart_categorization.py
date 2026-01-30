
import asyncio
import os
from pathlib import Path
from eternal_memory.config import load_config
from eternal_memory.engine.memory_engine import EternalMemorySystem

async def test_categorization():
    # Load .env
    env_path = Path.home() / ".openclaw" / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    os.environ[k] = v

    config = load_config()
    system = EternalMemorySystem(config)
    await system.initialize()
    
    print("--- Testing Smart Categorization ---")
    text = "I am currently working on a personal project called 'DreamForge' which is a 3D game using Bevy engine."
    print(f"Input: {text}")
    
    # Force add to buffer and flush
    await system.add_to_buffer("user", text)
    items = await system.flush_buffer()
    
    if items:
        for item in items:
            print(f"STORED: '{item.content}'")
            print(f"CATEGORY: {item.category_path}")
    else:
        print("No items stored!")
        
    await system.close()

if __name__ == "__main__":
    asyncio.run(test_categorization())
