
import asyncio
import os
from dotenv import load_dotenv
from eternal_memory.llm.client import LLMClient

from pathlib import Path

env_path = Path(__file__).parent.parent / '.env'
print(f"Loading .env from {env_path}")
load_dotenv(dotenv_path=env_path)

key = os.getenv("OPENAI_API_KEY")
print(f"API Key present: {'Yes' if key else 'No'}")

async def main():
    print("Initializing LLMClient...")
    try:
        client = LLMClient()
        print("Calling complete('Hello')...")
        response = await client.complete("Hello")
        print(f"Result: {response}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
