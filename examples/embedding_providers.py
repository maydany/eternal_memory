"""
Example: Using different embedding providers with Eternal Memory.
"""

import asyncio
from eternal_memory.llm.client import LLMClient


async def example_openai():
    """Example using OpenAI embeddings (default)."""
    print("=== OpenAI Provider Example ===\n")
    
    llm = LLMClient(
        embedding_provider="openai",  # Default
        api_key="your-openai-api-key"
    )
    
    texts = [
        "User prefers Python over JavaScript",
        "User works from home",
        "User likes coffee"
    ]
    
    embeddings = await llm.batch_generate_embeddings(texts)
    
    print(f"Provider: {llm.embedding_provider_name}")
    print(f"Model: {llm._embedding_provider.get_model_name()}")
    print(f"Dimension: {llm._embedding_provider.get_embedding_dimension()}")
    print(f"Generated {len(embeddings)} embeddings")
    print(f"First embedding preview: {embeddings[0][:5]}...")


async def example_gemini():
    """Example using Google Gemini embeddings."""
    print("\n=== Gemini Provider Example ===\n")
    
    llm = LLMClient(
        embedding_provider="gemini",
        embedding_api_key="your-google-api-key"
    )
    
    texts = [
        "User prefers Python over JavaScript",
        "User works from home",
        "User likes coffee"
    ]
    
    embeddings = await llm.batch_generate_embeddings(texts)
    
    print(f"Provider: {llm.embedding_provider_name}")
    print(f"Model: {llm._embedding_provider.get_model_name()}")
    print(f"Dimension: {llm._embedding_provider.get_embedding_dimension()}")
    print(f"Generated {len(embeddings)} embeddings")
    print(f"First embedding preview: {embeddings[0][:5]}...")


async def example_with_cache():
    """Example showing cache effectiveness."""
    print("\n=== Cache Example ===\n")
    
    llm = LLMClient(
        embedding_provider="openai",
        enable_embedding_cache=True,
        max_cache_size=1000
    )
    
    texts = ["User prefers Python", "User works remotely", "User likes coffee"]
    
    # First call: cache miss
    print("First call (cold cache):")
    await llm.batch_generate_embeddings(texts)
    stats1 = llm.get_cache_stats()
    print(f"  Hits: {stats1['hits']}, Misses: {stats1['misses']}")
    
    # Second call: cache hit
    print("\nSecond call (warm cache):")
    await llm.batch_generate_embeddings(texts)
    stats2 = llm.get_cache_stats()
    print(f"  Hits: {stats2['hits']}, Misses: {stats2['misses']}")
    print(f"  Hit rate: {stats2['hit_rate_percent']}%")


if __name__ == "__main__":
    # Run examples
    # asyncio.run(example_openai())
    # asyncio.run(example_gemini())
    asyncio.run(example_with_cache())
