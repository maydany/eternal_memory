"""
Unit Tests for Flush Pipeline

Tests the memory flush logic using mocks.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from eternal_memory.pipelines.flush import FlushPipeline

class TestFlushPipeline:
    """Tests for FlushPipeline."""

    @pytest.fixture
    def pipeline(self):
        """Create a mock FlushPipeline."""
        repo = AsyncMock()
        llm = AsyncMock()
        vault = AsyncMock()
        memorize = AsyncMock()
        
        return FlushPipeline(repo, llm, vault, memorize)

    @pytest.mark.asyncio
    async def test_execute_extracts_facts_from_conversation(self, pipeline):
        """Test extract facts from conversation and memorize them."""
        # Setup mocks
        pipeline.llm.complete.return_value = "- User likes coding\n- User lives in Seoul"
        pipeline.memorize_pipeline.store_single_memory.return_value = MagicMock(content="User likes coding")
        
        messages = [
            {"role": "user", "content": "I love coding"},
            {"role": "assistant", "content": "That's great!"},
            {"role": "user", "content": "I live in Seoul too."}
        ]
        
        # Execute
        items = await pipeline.execute(messages)
        
        # Verify
        pipeline.llm.complete.assert_called_once()
        assert len(items) == 2
        assert pipeline.memorize_pipeline.store_single_memory.call_count == 2
        
        # Check call args for first item
        call_args = pipeline.memorize_pipeline.store_single_memory.call_args_list[0]
        assert call_args.kwargs["content"] == "User likes coding"
        assert call_args.kwargs["metadata"]["source"] == "memory_flush"

    @pytest.mark.asyncio
    async def test_execute_handles_none_response(self, pipeline):
        """Test handling of NONE response from LLM."""
        pipeline.llm.complete.return_value = "NONE"
        
        messages = [{"role": "user", "content": "Hello"}]
        items = await pipeline.execute(messages)
        
        assert items == []
        pipeline.memorize_pipeline.store_single_memory.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_empty_messages_returns_empty(self, pipeline):
        """Test handling of empty message list."""
        items = await pipeline.execute([])
        
        assert items == []
        pipeline.llm.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_cleans_bullet_points(self, pipeline):
        """Test that bullet points are stripped from facts."""
        pipeline.llm.complete.return_value = "- Fact 1\r\n- Fact 2"
        pipeline.memorize_pipeline.store_single_memory.side_effect = lambda content, metadata: MagicMock(content=content)
        
        items = await pipeline.execute([{"role": "user", "content": "msg"}])
        
        assert len(items) == 2
        assert items[0].content == "Fact 1"
        assert items[1].content == "Fact 2"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
