"""
Tests for Memory Reinforcement Logic

Tests that redundant information strengthens existing memories rather than creating duplicates.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime

from eternal_memory.pipelines.memorize import MemorizePipeline
from eternal_memory.models.memory_item import MemoryItem, MemoryType, Resource


class TestReinforcementLogic:
    """Tests for memory reinforcement (duplicate handling)."""

    @pytest.fixture
    def mock_components(self):
        """Create mock components for testing."""
        repo = AsyncMock()
        llm = AsyncMock()
        vault = AsyncMock()
        
        pipeline = MemorizePipeline(repo, llm, vault)
        return pipeline, repo, llm, vault

    @pytest.mark.asyncio
    async def test_store_single_memory_detects_duplicate(self, mock_components):
        """Test that storing duplicate content reinforces existing memory."""
        pipeline, repo, llm, vault = mock_components
        
        # Setup data
        content = "I love Python"
        embedding = [0.1] * 1536
        existing_id = uuid4()
        
        existing_memory = MemoryItem(
            id=existing_id,
            content=content,
            category_path="knowledge/coding",
            type="fact",
            importance=0.5,
            mention_count=1,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
        )
        
        # Mocks
        llm.generate_embedding.return_value = embedding
        
        # Simulate finding an existing item
        repo.vector_search.return_value = [existing_memory]
        
        # Simulate reinforcement update returning new count
        repo.reinforce_memory_item.return_value = 2
        
        # Execute
        result = await pipeline.store_single_memory(content=content)
        
        # Verify
        assert result.id == existing_id
        assert result.mention_count == 2
        # Importance should increase: min(1.0, 0.5 + 0.1) = 0.6
        assert result.importance == 0.6
        
        # Verify repo calls
        repo.vector_search.assert_called_once()
        repo.reinforce_memory_item.assert_called_once_with(existing_id, 0.6)
        
        # Verify vault calls
        vault.update_memory_in_file.assert_called_once_with(
            category_path="knowledge/coding",
            content=content,
            new_importance=0.6,
            mention_count=2
        )
        
        # Verify NO new memory creation
        repo.create_memory_item.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_single_memory_creates_new_if_unique(self, mock_components):
        """Test that unique content creates a new memory."""
        pipeline, repo, llm, vault = mock_components
        
        # Setup
        content = "New unique fact"
        embedding = [0.2] * 1536
        
        llm.generate_embedding.return_value = embedding
        # Simulate no existing similar items
        repo.vector_search.return_value = []
        
        # Simulate checking category exists
        repo.get_category_by_path.return_value = MagicMock(id=uuid4())
        
        # Execute
        result = await pipeline.store_single_memory(
            content=content,
            category_path="knowledge/new"
        )
        
        # Verify
        assert result.content == content
        assert result.mention_count == 1
        
        # Verify creation calls
        repo.create_memory_item.assert_called_once()
        repo.reinforce_memory_item.assert_not_called()
        vault.append_to_category.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_single_memory_max_importance_cap(self, mock_components):
        """Test that importance doesn't exceed 1.0."""
        pipeline, repo, llm, vault = mock_components
        
        # Setup existing item with high importance
        existing_memory = MemoryItem(
            content="Important fact",
            category_path="test",
            importance=0.95,
            mention_count=5
        )
        
        llm.generate_embedding.return_value = [0.1] * 1536
        repo.vector_search.return_value = [existing_memory]
        repo.reinforce_memory_item.return_value = 6
        
        # Execute reinforcement
        result = await pipeline.store_single_memory("Important fact")
        
        # Verify importance capped at 1.0 (0.95 + 0.1 = 1.05 -> 1.0)
        assert result.importance == 1.0
        
        repo.reinforce_memory_item.assert_called_once_with(existing_memory.id, 1.0)
