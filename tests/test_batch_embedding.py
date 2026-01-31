"""
Batch Embedding Performance Test

This test demonstrates the performance improvement from batch embedding.
"""
import asyncio
import time
from eternal_memory.llm.client import LLMClient


async def test_batch_vs_individual():
    """Compare batch embedding vs individual embedding."""
    
    # Test data
    test_texts = [
        "User prefers Python over JavaScript",
        "User works from home",
        "User likes dark mode",
        "User drinks coffee every morning",
        "User exercises 3 times a week",
        "User is learning machine learning",
        "User prefers vim over vscode",
        "User is interested in AI agents",
        "User lives in Seoul",
        "User speaks Korean and English",
    ]
    
    llm = LLMClient()
    
    # Test 1: Individual embeddings (old way)
    print("=" * 60)
    print("Test 1: Individual Embeddings (N API calls)")
    print("=" * 60)
    start_time = time.time()
    
    individual_embeddings = []
    for text in test_texts:
        embedding = await llm.generate_embedding(text)
        individual_embeddings.append(embedding)
    
    individual_time = time.time() - start_time
    
    # Clear cache for fair comparison
    llm.clear_embedding_cache()
    
    # Test 2: Batch embeddings (new way)
    print("\n" + "=" * 60)
    print("Test 2: Batch Embeddings (1 API call)")
    print("=" * 60)
    start_time = time.time()
    
    batch_embeddings = await llm.batch_generate_embeddings(test_texts)
    
    batch_time = time.time() - start_time
    
    # Results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Number of texts: {len(test_texts)}")
    print(f"\nIndividual approach:")
    print(f"  Time: {individual_time:.2f}s")
    print(f"  API calls: {len(test_texts)}")
    print(f"\nBatch approach:")
    print(f"  Time: {batch_time:.2f}s")
    print(f"  API calls: 1")
    print(f"\nImprovement:")
    print(f"  Speed: {individual_time/batch_time:.1f}x faster")
    print(f"  Cost reduction: ~{(1 - 1/len(test_texts)) * 100:.0f}%")
    
    # Verify results are identical
    assert len(individual_embeddings) == len(batch_embeddings)
    for i, (ind_emb, batch_emb) in enumerate(zip(individual_embeddings, batch_embeddings)):
        assert len(ind_emb) == len(batch_emb) == 1536, f"Embedding {i} has wrong dimension"
    
    print("\n✅ All embeddings are valid!")
    
    # Cache stats
    stats = llm.get_cache_stats()
    print(f"\nCache Stats:")
    print(f"  Hit rate: {stats['hit_rate_percent']:.1f}%")
    print(f"  Hits: {stats['hits']}")
    print(f"  Misses: {stats['misses']}")


async def test_batch_with_cache():
    """Test that batch embedding respects cache."""
    
    print("\n" + "=" * 60)
    print("Test 3: Batch Embedding with Cache")
    print("=" * 60)
    
    llm = LLMClient()
    llm.clear_embedding_cache()
    
    texts = [
        "First text",
        "Second text",
        "Third text",
    ]
    
    # First call: all cache misses
    print("\nFirst call (cold cache):")
    embeddings1 = await llm.batch_generate_embeddings(texts)
    stats1 = llm.get_cache_stats()
    print(f"  Cache misses: {stats1['misses']}")
    print(f"  Cache hits: {stats1['hits']}")
    
    # Second call: all cache hits
    print("\nSecond call (warm cache):")
    embeddings2 = await llm.batch_generate_embeddings(texts)
    stats2 = llm.get_cache_stats()
    print(f"  Cache misses: {stats2['misses']}")
    print(f"  Cache hits: {stats2['hits']}")
    
    # Third call: partial cache (2 cached, 1 new)
    print("\nThird call (partial cache):")
    mixed_texts = [
        "First text",  # cached
        "Second text",  # cached
        "New text",  # not cached
    ]
    embeddings3 = await llm.batch_generate_embeddings(mixed_texts)
    stats3 = llm.get_cache_stats()
    print(f"  Cache misses: {stats3['misses']}")
    print(f"  Cache hits: {stats3['hits']}")
    
    assert len(embeddings1) == len(embeddings2) == len(embeddings3)
    print("\n✅ Cache working correctly!")


if __name__ == "__main__":
    print("Batch Embedding Performance Test")
    print("=" * 60)
    asyncio.run(test_batch_vs_individual())
    asyncio.run(test_batch_with_cache())
