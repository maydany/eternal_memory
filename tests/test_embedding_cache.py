"""
Test Embedding Cache

Verifies that embedding caching works correctly and reduces API calls.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from eternal_memory.llm.client import LLMClient


class TestEmbeddingCache:
    """Tests for embedding cache functionality."""
    
    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """Test that repeated queries use cache."""
        client = LLMClient(api_key="test-key", enable_embedding_cache=True)
        
        # Mock the OpenAI client
        mock_embedding = [0.1, 0.2, 0.3] * 512  # 1536 dims
        client.client.embeddings = AsyncMock()
        client.client.embeddings.create = AsyncMock(
            return_value=MagicMock(
                data=[MagicMock(embedding=mock_embedding)],
                usage=None
            )
        )
        
        # First call - should hit API
        text = "내가 좋아하는 과일이 뭐였지?"
        result1 = await client.generate_embedding(text)
        
        assert result1 == mock_embedding
        assert client.client.embeddings.create.call_count == 1
        assert client._cache_misses == 1
        assert client._cache_hits == 0
        
        # Second call - should use cache
        result2 = await client.generate_embedding(text)
        
        assert result2 == mock_embedding
        assert client.client.embeddings.create.call_count == 1  # No new call!
        assert client._cache_misses == 1
        assert client._cache_hits == 1
        
        # Third call - still cached
        result3 = await client.generate_embedding(text)
        
        assert result3 == mock_embedding
        assert client.client.embeddings.create.call_count == 1
        assert client._cache_hits == 2
    
    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test that different queries call API."""
        client = LLMClient(api_key="test-key", enable_embedding_cache=True)
        
        # Mock different embeddings
        mock_embedding1 = [0.1] * 1536
        mock_embedding2 = [0.2] * 1536
        
        client.client.embeddings = AsyncMock()
        client.client.embeddings.create = AsyncMock(
            side_effect=[
                MagicMock(data=[MagicMock(embedding=mock_embedding1)], usage=None),
                MagicMock(data=[MagicMock(embedding=mock_embedding2)], usage=None),
            ]
        )
        
        # Different texts
        result1 = await client.generate_embedding("사과")
        result2 = await client.generate_embedding("바나나")
        
        assert result1 == mock_embedding1
        assert result2 == mock_embedding2
        assert client.client.embeddings.create.call_count == 2
        assert client._cache_misses == 2
        assert client._cache_hits == 0
    
    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """Test that LRU eviction works when cache is full."""
        client = LLMClient(api_key="test-key", enable_embedding_cache=True, max_cache_size=3)
        
        # Mock embeddings
        client.client.embeddings = AsyncMock()
        client.client.embeddings.create = AsyncMock(
            return_value=MagicMock(
                data=[MagicMock(embedding=[0.1] * 1536)],
                usage=None
            )
        )
        
        # Fill cache with 3 items
        await client.generate_embedding("text1")
        await client.generate_embedding("text2")
        await client.generate_embedding("text3")
        
        assert len(client._embedding_cache) == 3
        assert client._cache_misses == 3
        
        # Add 4th item - should evict "text1"
        await client.generate_embedding("text4")
        
        assert len(client._embedding_cache) == 3
        assert "text1" not in client._embedding_cache
        assert "text2" in client._embedding_cache
        assert "text3" in client._embedding_cache
        assert "text4" in client._embedding_cache
    
    @pytest.mark.asyncio
    async def test_cache_stats(self):
        """Test cache statistics reporting."""
        client = LLMClient(api_key="test-key", enable_embedding_cache=True)
        
        client.client.embeddings = AsyncMock()
        client.client.embeddings.create = AsyncMock(
            return_value=MagicMock(
                data=[MagicMock(embedding=[0.1] * 1536)],
                usage=None
            )
        )
        
        # Initial stats
        stats = client.get_cache_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate_percent"] == 0
        
        # 1 miss, 2 hits
        await client.generate_embedding("query")
        await client.generate_embedding("query")
        await client.generate_embedding("query")
        
        stats = client.get_cache_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["total_requests"] == 3
        assert stats["hit_rate_percent"] == 66.67
        assert stats["cache_size"] == 1
    
    @pytest.mark.asyncio
    async def test_cache_disabled(self):
        """Test that caching can be disabled."""
        client = LLMClient(api_key="test-key", enable_embedding_cache=False)
        
        mock_embedding = [0.1] * 1536
        client.client.embeddings = AsyncMock()
        client.client.embeddings.create = AsyncMock(
            return_value=MagicMock(
                data=[MagicMock(embedding=mock_embedding)],
                usage=None
            )
        )
        
        # Same query twice
        await client.generate_embedding("test")
        await client.generate_embedding("test")
        
        # Should call API both times
        assert client.client.embeddings.create.call_count == 2
        assert len(client._embedding_cache) == 0
    
    @pytest.mark.asyncio
    async def test_clear_cache(self):
        """Test cache clearing."""
        client = LLMClient(api_key="test-key", enable_embedding_cache=True)
        
        client.client.embeddings = AsyncMock()
        client.client.embeddings.create = AsyncMock(
            return_value=MagicMock(
                data=[MagicMock(embedding=[0.1] * 1536)],
                usage=None
            )
        )
        
        # Add some items
        await client.generate_embedding("query1")
        await client.generate_embedding("query2")
        
        assert len(client._embedding_cache) == 2
        assert client._cache_misses == 2
        
        # Clear cache
        client.clear_embedding_cache()
        
        assert len(client._embedding_cache) == 0
        assert client._cache_hits == 0
        assert client._cache_misses == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
