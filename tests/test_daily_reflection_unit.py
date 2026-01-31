"""
Unit Tests for Daily Reflection Logic

Tests the Daily Reflection components using mocks - no LLM API calls required.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


class TestDailyReflectionLogic:
    """Unit tests for Daily Reflection that don't require external services."""
    
    @pytest.mark.asyncio
    async def test_get_memories_since_returns_recent_items(self):
        """Test that get_memories_since filters by datetime correctly."""
        from eternal_memory.database.repository import MemoryRepository
        from eternal_memory.models.memory_item import MemoryItem, MemoryType
        
        # Create mock repository with mocked pool
        repo = MemoryRepository("mock://connection")
        repo._pool = AsyncMock()
        
        # Mock database response
        now = datetime.now()
        mock_rows = [
            {
                "id": uuid4(),
                "content": "Test memory 1",
                "category_path": "test/category",
                "type": "fact",
                "confidence": 1.0,
                "importance": 0.5,
                "mention_count": 1,
                "resource_id": None,
                "created_at": now - timedelta(hours=1),
                "last_accessed": now,
            },
            {
                "id": uuid4(),
                "content": "Test memory 2",
                "category_path": "test/category",
                "type": "preference",
                "confidence": 0.9,
                "importance": 0.7,
                "mention_count": 2,
                "resource_id": None,
                "created_at": now - timedelta(hours=2),
                "last_accessed": now,
            },
        ]
        
        # Setup mock
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=mock_rows)
        repo._pool.acquire = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_conn), __aexit__=AsyncMock()))
        
        # Execute
        since = now - timedelta(hours=24)
        result = await repo.get_memories_since(since, limit=100)
        
        # Verify
        assert len(result) == 2
        assert result[0].content == "Test memory 1"
        assert result[1].content == "Test memory 2"
        
        # Verify SQL was called with correct params
        mock_conn.fetch.assert_called_once()
        call_args = mock_conn.fetch.call_args
        assert "created_at > $1" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_generate_daily_reflection_returns_structured_output(self):
        """Test that generate_daily_reflection returns expected structure."""
        from eternal_memory.llm.client import LLMClient
        
        client = LLMClient(api_key="mock-key", model="gpt-4o-mini")
        
        # Mock the OpenAI client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''{
            "summary": "오늘은 생산적인 하루였습니다.",
            "key_events": ["코딩 작업", "점심 미팅"],
            "sentiment": "positive",
            "insights": "사용자는 오전에 집중력이 높습니다."
        }'''
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        
        client.client = AsyncMock()
        client.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Execute
        result = await client.generate_daily_reflection(
            memory_items=["오늘 코딩을 했다", "점심에 미팅이 있었다"],
            date_str="2026-01-31"
        )
        
        # Verify structure
        assert "summary" in result
        assert "key_events" in result
        assert "sentiment" in result
        assert "insights" in result
        
        assert result["summary"] == "오늘은 생산적인 하루였습니다."
        assert len(result["key_events"]) == 2
        assert result["sentiment"] == "positive"

    @pytest.mark.asyncio
    async def test_generate_daily_reflection_handles_invalid_json(self):
        """Test graceful handling of invalid JSON response."""
        from eternal_memory.llm.client import LLMClient
        
        client = LLMClient(api_key="mock-key", model="gpt-4o-mini")
        
        # Mock invalid JSON response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is not valid JSON"
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        
        client.client = AsyncMock()
        client.client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Execute - should not raise
        result = await client.generate_daily_reflection(
            memory_items=["test"],
            date_str="2026-01-31"
        )
        
        # Verify fallback values
        assert "summary" in result
        assert "2026-01-31" in result["summary"]
        assert result["sentiment"] == "neutral"
        assert result["key_events"] == []

    @pytest.mark.asyncio
    async def test_job_daily_reflection_skips_when_no_memories(self):
        """Test that daily reflection job handles empty memories gracefully."""
        from eternal_memory.scheduling.jobs import job_daily_reflection
        
        # Create mock system
        mock_system = MagicMock()
        mock_system.repository = AsyncMock()
        mock_system.repository.get_memories_since = AsyncMock(return_value=[])
        mock_system.llm = AsyncMock()
        mock_system.memorize = AsyncMock()
        
        # Execute
        await job_daily_reflection(mock_system)
        
        # Verify LLM was NOT called when no memories exist
        mock_system.llm.generate_daily_reflection.assert_not_called()
        mock_system.memorize.assert_not_called()

    @pytest.mark.asyncio
    async def test_job_daily_reflection_processes_memories(self):
        """Test that daily reflection job processes memories correctly."""
        from eternal_memory.scheduling.jobs import job_daily_reflection
        from eternal_memory.models.memory_item import MemoryItem, MemoryType
        
        # Create mock memories
        mock_memories = [
            MagicMock(content="오늘 카페에서 일했다"),
            MagicMock(content="새 프로젝트를 시작했다"),
        ]
        
        # Create mock system
        mock_system = MagicMock()
        mock_system.repository = AsyncMock()
        mock_system.repository.get_memories_since = AsyncMock(return_value=mock_memories)
        mock_system.llm = AsyncMock()
        mock_system.llm.generate_daily_reflection = AsyncMock(return_value={
            "summary": "생산적인 하루",
            "key_events": ["카페 작업", "프로젝트 시작"],
            "sentiment": "positive",
            "insights": "새로운 일을 시작함",
        })
        mock_system.memorize = AsyncMock()
        
        # Execute
        await job_daily_reflection(mock_system)
        
        # Verify LLM was called with memory contents
        mock_system.llm.generate_daily_reflection.assert_called_once()
        call_args = mock_system.llm.generate_daily_reflection.call_args
        assert len(call_args.kwargs["memory_items"]) == 2
        
        # Verify memorize was called with reflection
        mock_system.memorize.assert_called_once()
        memorize_args = mock_system.memorize.call_args
        assert "[Daily Reflection" in memorize_args[0][0]
        assert "생산적인 하루" in memorize_args[0][0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
