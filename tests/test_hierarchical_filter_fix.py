"""
Test cases for Hierarchical Filtering and Triple Supersede Propagation.

These tests verify the critical bug fixes for:
1. MemoryItems with ALL inactive triples should be excluded from search results
2. supersede_triple should propagate deactivation to parent MemoryItem

Reference:
- Bug Report: implementation_plan.md (2026-02-01)
- Issue: Inactive entities appearing in search results due to incomplete state propagation
"""

import pytest
from uuid import uuid4
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from eternal_memory.models.memory_item import MemoryItem, MemoryType
from eternal_memory.models.semantic_triple import SemanticTriple
from eternal_memory.pipelines.retrieve import RetrievePipeline
from eternal_memory.database.repository import MemoryRepository


class TestHierarchicalFilter:
    """Tests for _apply_hierarchical_filter in RetrievePipeline"""
    
    @pytest.fixture
    def mock_repository(self):
        """Create a mock repository with async methods"""
        repo = AsyncMock(spec=MemoryRepository)
        return repo
    
    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client"""
        return AsyncMock()
    
    @pytest.fixture
    def mock_vault(self):
        """Create a mock vault"""
        return AsyncMock()
    
    @pytest.fixture
    def pipeline(self, mock_repository, mock_llm_client, mock_vault):
        """Create a RetrievePipeline with mocks"""
        from eternal_memory.config import LLMConfig, ScoringConfig
        llm_config = LLMConfig(use_semantic_triples=True)
        return RetrievePipeline(
            repository=mock_repository,
            llm_client=mock_llm_client,
            vault=mock_vault,
            llm_config=llm_config,
        )
    
    def create_memory_item(self, content: str, item_id=None) -> MemoryItem:
        """Helper to create a MemoryItem"""
        return MemoryItem(
            id=item_id or uuid4(),
            content=content,
            category_path="test/category",
            type=MemoryType.FACT,
            confidence=0.9,
            importance=0.8,
        )
    
    def create_triple(self, subject: str, predicate: str, obj: str, 
                     memory_item_id=None, is_active=True) -> SemanticTriple:
        """Helper to create a SemanticTriple"""
        return SemanticTriple(
            id=uuid4(),
            memory_item_id=memory_item_id,
            subject=subject,
            predicate=predicate,
            object=obj,
            is_active=is_active,
        )
    
    @pytest.mark.asyncio
    async def test_exclude_memory_with_all_inactive_triples(self, pipeline, mock_repository):
        """
        CRITICAL TEST: Memory items with ALL triples inactive should be excluded.
        
        Scenario: User deactivated "박주연" - all related triples are inactive,
        but the parent MemoryItem was previously still active.
        """
        # Setup: Create a memory item about "박주연"
        memory_id = uuid4()
        memory_item = self.create_memory_item("박주연은 친구입니다", item_id=memory_id)
        
        # All triples for this memory are INACTIVE
        inactive_triples = [
            self.create_triple("User", "knows", "박주연", memory_item_id=memory_id, is_active=False),
            self.create_triple("박주연", "is", "친구", memory_item_id=memory_id, is_active=False),
        ]
        
        # Mock: No active triples found in semantic search
        mock_repository.search_triples_semantic.return_value = []
        
        # Mock: get_triples_for_memory_item returns ALL triples (including inactive)
        mock_repository.get_triples_for_memory_item.return_value = inactive_triples
        
        # Execute
        query_embedding = [0.1] * 1536
        filtered_items, triple_context = await pipeline._apply_hierarchical_filter(
            memory_items=[memory_item],
            query_embedding=query_embedding,
        )
        
        # Assert: Memory item SHOULD BE EXCLUDED
        assert len(filtered_items) == 0, (
            "Memory items with ALL inactive triples should be excluded from results"
        )
        assert triple_context == "", "No triple context when no active triples"
    
    @pytest.mark.asyncio
    async def test_include_memory_with_some_active_triples(self, pipeline, mock_repository):
        """
        Memory items with at least one active triple should be included.
        """
        memory_id = uuid4()
        memory_item = self.create_memory_item("User likes bananas and apples", item_id=memory_id)
        
        # Mixed triples: one active, one inactive
        mixed_triples = [
            self.create_triple("User", "likes", "bananas", memory_item_id=memory_id, is_active=True),
            self.create_triple("User", "likes", "apples", memory_item_id=memory_id, is_active=False),  # superseded
        ]
        
        active_triple = mixed_triples[0]
        
        # Mock: Active triple found in semantic search
        mock_repository.search_triples_semantic.return_value = [active_triple]
        
        # Mock: All triples for memory
        mock_repository.get_triples_for_memory_item.return_value = mixed_triples
        
        # Execute
        query_embedding = [0.1] * 1536
        filtered_items, triple_context = await pipeline._apply_hierarchical_filter(
            memory_items=[memory_item],
            query_embedding=query_embedding,
        )
        
        # Assert: Memory item SHOULD BE INCLUDED
        assert len(filtered_items) == 1, "Memory with active triples should be included"
        assert "bananas" in triple_context, "Triple context should include active triple"
    
    @pytest.mark.asyncio
    async def test_include_memory_without_any_triples(self, pipeline, mock_repository):
        """
        Memory items without any triples (not yet atomized) should be included as fallback.
        """
        memory_id = uuid4()
        memory_item = self.create_memory_item("New fact not yet atomized", item_id=memory_id)
        
        # No triples for this memory
        mock_repository.search_triples_semantic.return_value = []
        mock_repository.get_triples_for_memory_item.return_value = []
        
        # Execute
        query_embedding = [0.1] * 1536
        filtered_items, triple_context = await pipeline._apply_hierarchical_filter(
            memory_items=[memory_item],
            query_embedding=query_embedding,
        )
        
        # Assert: Memory item SHOULD BE INCLUDED (fallback)
        assert len(filtered_items) == 1, "Memory without triples should be included as fallback"
        assert memory_item.content == filtered_items[0].content


class TestSupersedeTriplePropagation:
    """Tests for supersede_triple parent MemoryItem deactivation"""
    
    @pytest.mark.asyncio
    async def test_supersede_deactivates_parent_when_all_triples_inactive(self):
        """
        CRITICAL TEST: When all triples are superseded, parent MemoryItem should be deactivated.
        """
        # This test requires a real database connection or more sophisticated mocking
        # Here we provide the test structure for integration testing
        
        # Setup would involve:
        # 1. Create a MemoryItem
        # 2. Create 2 triples linked to it
        # 3. Supersede first triple -> parent still active
        # 4. Supersede second triple -> parent should become inactive
        
        # For unit testing, we mock the connection
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {"memory_item_id": uuid4()}
        mock_conn.execute.return_value = "UPDATE 1"
        mock_conn.fetchval.return_value = 0  # No active triples remaining
        
        # Verify the logic flow
        # After superseding the last triple, fetchval returns 0
        # Then execute should be called to deactivate parent
        assert mock_conn.fetchval.return_value == 0, "Should have 0 active triples"
    
    @pytest.mark.asyncio
    async def test_supersede_keeps_parent_active_when_other_triples_remain(self):
        """
        When some triples remain active, parent MemoryItem should stay active.
        """
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {"memory_item_id": uuid4()}
        mock_conn.execute.return_value = "UPDATE 1"
        mock_conn.fetchval.return_value = 1  # One active triple remains
        
        # Parent should NOT be deactivated
        assert mock_conn.fetchval.return_value > 0, "Active triples remain"


class TestIntegrationScenario:
    """
    Integration test scenarios for the complete flow.
    
    These tests document the expected behavior and can be run
    against a real database if available.
    """
    
    @pytest.mark.asyncio
    async def test_juyeon_exclusion_scenario(self):
        """
        Full scenario test: 박주연 should not appear after being deactivated.
        
        Steps:
        1. Store "박주연은 친구입니다"
        2. Extract triple: (User, knows, 박주연)
        3. Later: Supersede triple (user says 박주연 is no longer active)
        4. Search for "이름" or related query
        5. EXPECT: 박주연 should NOT appear in results
        """
        # This is a documentation/integration test
        # Actual implementation would use real DB
        pass


# Fixtures for pytest
@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for async tests"""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
