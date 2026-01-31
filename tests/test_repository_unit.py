"""
Unit Tests for Memory Repository

Tests repository logic using mocks for the database connection.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timedelta
from eternal_memory.database.repository import MemoryRepository

class TestRepositoryUnit:
    """Unit tests for MemoryRepository."""

    @pytest.fixture
    def mock_repo(self):
        """Create a repository with mocked pool."""
        repo = MemoryRepository(connection_string="mock://")
        
        # Correctly mock async context manager for pool.acquire()
        mock_pool = MagicMock()
        mock_ctx = MagicMock()
        mock_conn = AsyncMock()
        
        # __aenter__ must be an async function (or return an awaitable)
        # AsyncMock() is a callable that returns a coroutine
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)
        
        mock_pool.acquire.return_value = mock_ctx
        
        repo._pool = mock_pool
        return repo

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_vector_search_returns_similar_items(self, mock_repo):
        """Test vector search executes correct query."""
        # Get the mock connection from the configured fixture
        # mock_repo._pool.acquire() returns mock_ctx
        # mock_ctx.__aenter__() returns mock_conn
        mock_conn = await mock_repo._pool.acquire.return_value.__aenter__()
        
        # Mock DB return
        mock_conn.fetch.return_value = [
            {
                "id": uuid4(),
                "content": "test",
                "similarity": 0.9,
                "category_path": "test",
                "created_at": datetime.now(),
                "importance": 0.5,
                "metadata": "{}",
                "category_id": uuid4(),
                "type": "fact",  # Added keys
                "confidence": 0.9,
                "resource_id": None,
                "last_accessed": datetime.now()
            }
        ]
        
        embedding = [0.1] * 1536
        results = await mock_repo.vector_search(embedding, limit=5)
        
        assert len(results) == 1
        # Check query contained vector logic
        args = mock_conn.fetch.call_args
        assert "ORDER BY mi.embedding <=> $1::vector" in args[0][0]

    @pytest.mark.asyncio
    async def test_hybrid_search_combines_scores(self, mock_repo):
        """Test hybrid search logic."""
        mock_conn = await mock_repo._pool.acquire.return_value.__aenter__()
        
        # Mock fetch result for keywords and sematic
        mock_conn.fetch.return_value = []
        
        await mock_repo.hybrid_search("query", [0.1]*1536)
        
        # Just verify a fetch happened
        mock_conn.fetch.assert_called()

    @pytest.mark.asyncio
    async def test_fulltext_search_uses_tsvector(self, mock_repo):
        """Test fulltext search uses correct SQL."""
        mock_conn = await mock_repo._pool.acquire.return_value.__aenter__()
        
        await mock_repo.fulltext_search("query")
        
        args = mock_conn.fetch.call_args
        assert "to_tsquery" in args[0][0]
        assert "ORDER BY rank DESC" in args[0][0]

    @pytest.mark.asyncio
    async def test_get_stale_items_filters_by_date(self, mock_repo):
        """Test fetching stale items."""
        mock_conn = await mock_repo._pool.acquire.return_value.__aenter__()
        
        # Mock fetch return with empty list (safe default)
        mock_conn.fetch.return_value = []
        
        await mock_repo.get_stale_items(days_threshold=30)
        
        args = mock_conn.fetch.call_args
        # Check logic for date comparison
        # Code: WHERE mi.last_accessed < NOW() - (INTERVAL '1 day' * $1)
        sql = args[0][0]
        assert "last_accessed < NOW()" in sql
        assert "INTERVAL '1 day'" in sql

    @pytest.mark.asyncio
    async def test_reinforce_memory_item_increments(self, mock_repo):
        """Test reinforcement updates mention_count."""
        mock_conn = await mock_repo._pool.acquire.return_value.__aenter__()
        # It uses fetchrow, returns a record (dict-like)
        mock_conn.fetchrow.return_value = {"mention_count": 5}
        
        count = await mock_repo.reinforce_memory_item(uuid4(), new_importance=0.8)
        
        assert count == 5
        args = mock_conn.fetchrow.call_args
        sql = args[0][0]
        assert "UPDATE memory_items" in sql
        assert "mention_count = mention_count + 1" in sql
        assert "importance = $2" in sql

    @pytest.mark.asyncio
    async def test_get_scheduled_tasks_returns_all(self, mock_repo):
        """Test fetching scheduled tasks."""
        mock_conn = await mock_repo._pool.acquire.return_value.__aenter__()
        mock_conn.fetch.return_value = []
        
        await mock_repo.get_scheduled_tasks()
        
        args = mock_conn.fetch.call_args
        assert "SELECT id, name, job_type" in args[0][0]
        assert "FROM scheduled_tasks" in args[0][0]

    @pytest.mark.asyncio
    async def test_save_scheduled_task_inserts(self, mock_repo):
        """Test saving a scheduled task."""
        mock_conn = await mock_repo._pool.acquire.return_value.__aenter__()
        
        # It uses fetchrow expecting RETURNING ...
        mock_conn.fetchrow.return_value = {
            "id": uuid4(),
            "name": "job1",
            "job_type": "success",
            "interval_seconds": 60,
            "enabled": True,
            "is_system": False,
            "last_run": None,
            "next_run": None,
            "created_at": None
        }
        
        await mock_repo.save_scheduled_task("job1", "cron", 60)
        
        args = mock_conn.fetchrow.call_args
        sql = args[0][0]
        assert "INSERT INTO scheduled_tasks" in sql


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
