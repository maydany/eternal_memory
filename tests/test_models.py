"""
Tests for Data Models

Tests MemoryItem, Resource, Category, and RetrievalResult models.
"""

import uuid
from datetime import datetime

import pytest

from eternal_memory.models.memory_item import Category, MemoryItem, MemoryType, Resource
from eternal_memory.models.retrieval import RetrievalResult


class TestMemoryItem:
    """Tests for MemoryItem model."""
    
    def test_create_default(self):
        """Test creating MemoryItem with defaults."""
        item = MemoryItem(
            content="User prefers TypeScript",
            category_path="knowledge/coding",
        )
        
        assert item.content == "User prefers TypeScript"
        assert item.category_path == "knowledge/coding"
        assert item.type == MemoryType.FACT
        assert item.confidence == 1.0
        assert item.importance == 0.5
        assert item.id is not None
        assert isinstance(item.created_at, datetime)
    
    def test_create_with_all_fields(self):
        """Test creating MemoryItem with all fields specified."""
        item_id = uuid.uuid4()
        resource_id = uuid.uuid4()
        now = datetime.now()
        
        item = MemoryItem(
            id=item_id,
            content="Meeting scheduled for Monday",
            category_path="personal/schedule",
            type=MemoryType.EVENT,
            confidence=0.9,
            importance=0.8,
            source_resource_id=resource_id,
            created_at=now,
            last_accessed=now,
        )
        
        assert item.id == item_id
        assert item.type == MemoryType.EVENT
        assert item.confidence == 0.9
        assert item.importance == 0.8
        assert item.source_resource_id == resource_id
    
    def test_memory_types(self):
        """Test all memory types."""
        for mem_type in MemoryType:
            item = MemoryItem(
                content=f"Test {mem_type.value}",
                category_path="test",
                type=mem_type,
            )
            assert item.type == mem_type
    
    def test_validation_confidence_bounds(self):
        """Test confidence validation."""
        with pytest.raises(ValueError):
            MemoryItem(
                content="Test",
                category_path="test",
                confidence=1.5,  # Invalid: > 1.0
            )
        
        with pytest.raises(ValueError):
            MemoryItem(
                content="Test",
                category_path="test",
                confidence=-0.1,  # Invalid: < 0.0
            )


class TestResource:
    """Tests for Resource model."""
    
    def test_create_resource(self):
        """Test creating a Resource."""
        resource = Resource(
            uri="file:///docs/meeting.txt",
            modality="text",
            content="Meeting notes...",
        )
        
        assert resource.uri == "file:///docs/meeting.txt"
        assert resource.modality == "text"
        assert resource.content == "Meeting notes..."
        assert resource.id is not None
    
    def test_resource_with_metadata(self):
        """Test Resource with metadata."""
        resource = Resource(
            uri="telegram://123456",
            modality="conversation",
            content="Hello!",
            metadata={
                "sender": "user123",
                "channel": "dm",
            },
        )
        
        assert resource.metadata["sender"] == "user123"


class TestCategory:
    """Tests for Category model."""
    
    def test_create_category(self):
        """Test creating a Category."""
        category = Category(
            name="python",
            path="knowledge/coding/python",
            description="Python programming knowledge",
        )
        
        assert category.name == "python"
        assert category.path == "knowledge/coding/python"
        assert category.parent_id is None
    
    def test_category_hierarchy(self):
        """Test parent-child relationship."""
        parent_id = uuid.uuid4()
        
        child = Category(
            name="python",
            path="knowledge/coding/python",
            parent_id=parent_id,
        )
        
        assert child.parent_id == parent_id


class TestRetrievalResult:
    """Tests for RetrievalResult model."""
    
    def test_create_empty_result(self):
        """Test creating empty RetrievalResult."""
        result = RetrievalResult()
        
        assert result.items == []
        assert result.related_categories == []
        assert result.suggested_context == ""
        assert result.retrieval_mode == "fast"
    
    def test_create_with_items(self):
        """Test RetrievalResult with items."""
        items = [
            MemoryItem(content="Fact 1", category_path="test"),
            MemoryItem(content="Fact 2", category_path="test"),
        ]
        
        result = RetrievalResult(
            items=items,
            related_categories=["knowledge/coding"],
            suggested_context="Related programming context",
            query_evolved="What are the coding preferences?",
            retrieval_mode="deep",
            confidence_score=0.85,
        )
        
        assert len(result.items) == 2
        assert result.retrieval_mode == "deep"
        assert result.confidence_score == 0.85
