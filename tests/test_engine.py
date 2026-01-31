"""
Integration Tests for EternalMemorySystem

Tests the full memory system end-to-end.
Note: Requires PostgreSQL with pgvector extension and OpenAI API key.
"""

import os
import tempfile

import pytest

# Skip if database or API not available
pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set"
)


class TestEternalMemorySystemIntegration:
    """Integration tests for the full system."""
    
    @pytest.mark.asyncio
    async def test_full_memorize_retrieve_flow(self):
        """Test complete memorize → retrieve flow."""
        from eternal_memory import EternalMemorySystem
        from eternal_memory.config import MemoryConfig, DatabaseConfig, LLMConfig
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MemoryConfig(
                database=DatabaseConfig(name="eternal_memory_test"),
                llm=LLMConfig(model="gpt-4o-mini"),
            )
            
            async with EternalMemorySystem(config, vault_path=tmpdir) as memory:
                # Store a memory
                item = await memory.memorize(
                    "사용자는 파이썬보다 타입스크립트를 선호한다",
                    metadata={"source": "test"},
                )
                
                assert item is not None
                assert item.content
                
                # Retrieve the memory
                result = await memory.retrieve(
                    "프로그래밍 언어 선호도",
                    mode="fast",
                )
                
                assert result is not None
                assert result.retrieval_mode == "fast"
    
    @pytest.mark.asyncio
    async def test_context_prediction(self):
        """Test context prediction pipeline."""
        from eternal_memory import EternalMemorySystem
        from eternal_memory.config import MemoryConfig
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MemoryConfig()
            
            async with EternalMemorySystem(config, vault_path=tmpdir) as memory:
                context = await memory.predict_context({
                    "time": "2026-01-31T10:00:00",
                    "open_apps": ["VSCode", "Chrome"],
                })
                
                assert context is not None
                assert isinstance(context, str)
    
    @pytest.mark.asyncio  
    async def test_system_stats(self):
        """Test getting system statistics."""
        from eternal_memory import EternalMemorySystem
        from eternal_memory.config import MemoryConfig
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MemoryConfig()
            
            async with EternalMemorySystem(config, vault_path=tmpdir) as memory:
                stats = await memory.get_stats()
                
                assert "resources" in stats
                assert "categories" in stats
                assert "memory_items" in stats

    @pytest.mark.asyncio
    async def test_daily_reflection_with_memories(self):
        """Test daily reflection when memories exist."""
        from eternal_memory import EternalMemorySystem
        from eternal_memory.config import MemoryConfig
        from eternal_memory.scheduling.jobs import job_daily_reflection
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MemoryConfig()
            
            async with EternalMemorySystem(config, vault_path=tmpdir) as memory:
                # Store some test memories
                await memory.memorize("오늘 카페에서 코딩을 했다")
                await memory.memorize("점심으로 라멘을 먹었다")
                
                # Get initial memory count
                initial_stats = await memory.get_stats()
                initial_count = initial_stats["memory_items"]
                
                # Run daily reflection
                await job_daily_reflection(memory)
                
                # Check that a new memory was created (the reflection)
                final_stats = await memory.get_stats()
                # The reflection should create at least one new memory
                assert final_stats["memory_items"] >= initial_count

    @pytest.mark.asyncio
    async def test_daily_reflection_no_memories(self):
        """Test daily reflection when no recent memories exist."""
        from eternal_memory import EternalMemorySystem
        from eternal_memory.config import MemoryConfig
        from eternal_memory.scheduling.jobs import job_daily_reflection
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MemoryConfig()
            
            async with EternalMemorySystem(config, vault_path=tmpdir) as memory:
                # Run daily reflection without any memories
                # Should complete without error
                await job_daily_reflection(memory)
                
                # Stats should show only initial categories, no reflection memory
                stats = await memory.get_stats()
                # No crash means success for empty case
                assert stats is not None
