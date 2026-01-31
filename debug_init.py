
import asyncio
import os
from eternal_memory.engine.memory_engine import EternalMemorySystem
from eternal_memory.config import load_config

from eternal_memory.config import load_config
from pathlib import Path

def load_env_file():
    """Load environment variables from ~/.openclaw/.env if it exists."""
    env_path = Path.home() / ".openclaw" / ".env"
    if env_path.exists():
        print(f"Loading env from {env_path}")
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())

async def main():
    load_env_file()
    print("Starting debug init...")
    try:
        config = load_config()
        print(f"Config loaded. DB: {config.database.name}")
        
        system = EternalMemorySystem(config)
        print("System instantiated. Initializing...")
        
        await system.initialize()
        print("Initialization successful!")
        
        print(f"Stats: {await system.get_stats()}")
        await system.close()
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"FATAL ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(main())
