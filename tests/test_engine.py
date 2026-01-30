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
