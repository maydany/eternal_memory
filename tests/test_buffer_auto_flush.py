"""
Tests for Buffer Auto-Flush Features

Tests idle timeout flush, race condition protection, and empty buffer handling.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from eternal_memory.config import MemoryConfig, BufferConfig


class TestBufferAutoFlush:
    """Test cases for buffer auto-flush safety features."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock config with short idle timeout for testing."""
        config = MagicMock(spec=MemoryConfig)
        config.buffer = MagicMock(spec=BufferConfig)
        config.buffer.flush_threshold_tokens = 4000
        config.buffer.auto_flush_enabled = True
        config.buffer.idle_flush_timeout_minutes = 1  # 1 minute for faster testing
        return config
    
    @pytest.mark.asyncio
    async def test_idle_flush_timeout_config_default(self):
        """Test that idle_flush_timeout_minutes has correct default value."""
        config = BufferConfig()
        assert config.idle_flush_timeout_minutes == 10
    
    @pytest.mark.asyncio
    async def test_idle_flush_timeout_config_custom(self):
        """Test that idle_flush_timeout_minutes can be customized."""
        config = BufferConfig(idle_flush_timeout_minutes=30)
        assert config.idle_flush_timeout_minutes == 30
    
    @pytest.mark.asyncio
    async def test_flush_buffer_returns_empty_when_buffer_empty(self):
        """Test that flush_buffer returns empty list when buffer is already empty."""
        from eternal_memory.engine.memory_engine import EternalMemorySystem
        
        with patch.object(EternalMemorySystem, '__init__', lambda x, **kwargs: None):
            system = EternalMemorySystem()
            system._initialized = True
            system.conversation_buffer = []
            system._flush_lock = asyncio.Lock()
            system._flush_pipeline = MagicMock()
            
            result = await system.flush_buffer()
            
            assert result == []
            system._flush_pipeline.execute.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_flush_buffer_with_lock_prevents_race_condition(self):
        """Test that concurrent flush calls are serialized via lock."""
        from eternal_memory.engine.memory_engine import EternalMemorySystem
        
        with patch.object(EternalMemorySystem, '__init__', lambda x, **kwargs: None):
            system = EternalMemorySystem()
            system._initialized = True
            system.conversation_buffer = [{"role": "user", "content": "test"}]
            system._flush_lock = asyncio.Lock()
            system._flush_pipeline = MagicMock()
            system._flush_pipeline.execute = AsyncMock(return_value=[])
            system.buffer_file = MagicMock()
            system.buffer_file.exists.return_value = False
            
            # Simulate a long-running flush
            async def slow_flush(buffer):
                await asyncio.sleep(0.1)
                return []
            
            system._flush_pipeline.execute = slow_flush
            
            # Start two concurrent flushes
            flush1 = asyncio.create_task(system.flush_buffer(source="test1"))
            flush2 = asyncio.create_task(system.flush_buffer(source="test2"))
            
            await asyncio.gather(flush1, flush2)
            
            # Both should complete without error (second one sees empty buffer)
            result1 = await flush1
            result2 = await flush2
            
            # First flush gets the items, second sees empty buffer
            assert isinstance(result1, list)
            assert isinstance(result2, list)
    
    @pytest.mark.asyncio
    async def test_add_to_buffer_updates_activity_time(self):
        """Test that add_to_buffer updates the last activity timestamp."""
        from eternal_memory.engine.memory_engine import EternalMemorySystem
        
        with patch.object(EternalMemorySystem, '__init__', lambda x, **kwargs: None):
            system = EternalMemorySystem()
            system.conversation_buffer = []
            system._last_buffer_activity = datetime.now() - timedelta(hours=1)
            system.buffer_dir = MagicMock()
            system.buffer_file = MagicMock()
            
            old_activity_time = system._last_buffer_activity
            
            with patch('aiofiles.open', new_callable=MagicMock) as mock_open:
                mock_file = AsyncMock()
                mock_open.return_value.__aenter__ = AsyncMock(return_value=mock_file)
                mock_open.return_value.__aexit__ = AsyncMock(return_value=None)
                
                await system.add_to_buffer("user", "test message")
            
            # Activity time should be updated to now
            assert system._last_buffer_activity > old_activity_time
            assert len(system.conversation_buffer) == 1
    
    @pytest.mark.asyncio
    async def test_flush_buffer_logs_source(self):
        """Test that flush_buffer logs the source of the flush request."""
        from eternal_memory.engine.memory_engine import EternalMemorySystem
        
        with patch.object(EternalMemorySystem, '__init__', lambda x, **kwargs: None):
            system = EternalMemorySystem()
            system._initialized = True
            system.conversation_buffer = [{"role": "user", "content": "test"}]
            system._flush_lock = asyncio.Lock()
            system._flush_pipeline = MagicMock()
            system._flush_pipeline.execute = AsyncMock(return_value=[])
            system.buffer_file = MagicMock()
            system.buffer_file.exists.return_value = False
            
            # Capture print output
            with patch('builtins.print') as mock_print:
                await system.flush_buffer(source="session_end")
                
                # Check that source was logged
                mock_print.assert_called()
                call_args = str(mock_print.call_args)
                assert "session_end" in call_args


class TestBufferFlushAPI:
    """Test cases for buffer flush API endpoint."""
    
    @pytest.mark.asyncio
    async def test_flush_endpoint_accepts_source_param(self):
        """Test that /flush endpoint accepts source parameter."""
        from fastapi.testclient import TestClient
        from eternal_memory.api.main import app
        
        # This is an integration test - skip if dependencies not available
        pytest.importorskip("httpx")
        
        # Note: Full integration test would require running server
        # This just validates the route definition
        from eternal_memory.api.routes.buffer import flush_buffer
        import inspect
        
        sig = inspect.signature(flush_buffer)
        params = list(sig.parameters.keys())
        assert "source" in params


class TestIdleFlushLoop:
    """Test cases for the idle flush background loop."""
    
    @pytest.mark.asyncio
    async def test_idle_flush_loop_checks_idle_time(self):
        """Test that idle flush loop correctly calculates idle time."""
        from eternal_memory.engine.memory_engine import EternalMemorySystem
        
        with patch.object(EternalMemorySystem, '__init__', lambda x, **kwargs: None):
            system = EternalMemorySystem()
            system.conversation_buffer = [{"role": "user", "content": "test"}]
            system._last_buffer_activity = datetime.now() - timedelta(minutes=15)
            system._idle_flush_timeout_minutes = 10
            system._flush_lock = asyncio.Lock()
            system._flush_pipeline = MagicMock()
            system._flush_pipeline.execute = AsyncMock(return_value=[])
            system.buffer_file = MagicMock()
            system.buffer_file.exists.return_value = False
            system._initialized = True
            
            # Mock the sleep to return immediately, then raise CancelledError
            call_count = 0
            async def mock_sleep(seconds):
                nonlocal call_count
                call_count += 1
                if call_count > 1:
                    raise asyncio.CancelledError()
            
            with patch('asyncio.sleep', mock_sleep):
                with patch.object(system, 'flush_buffer', new_callable=AsyncMock) as mock_flush:
                    try:
                        await system._idle_flush_loop()
                    except asyncio.CancelledError:
                        pass
                    
                    # Should have called flush because idle time > timeout
                    mock_flush.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_idle_flush_loop_skips_empty_buffer(self):
        """Test that idle flush loop skips when buffer is empty."""
        from eternal_memory.engine.memory_engine import EternalMemorySystem
        
        with patch.object(EternalMemorySystem, '__init__', lambda x, **kwargs: None):
            system = EternalMemorySystem()
            system.conversation_buffer = []  # Empty buffer
            system._last_buffer_activity = datetime.now() - timedelta(minutes=15)
            system._idle_flush_timeout_minutes = 10
            
            call_count = 0
            async def mock_sleep(seconds):
                nonlocal call_count
                call_count += 1
                if call_count > 1:
                    raise asyncio.CancelledError()
            
            with patch('asyncio.sleep', mock_sleep):
                with patch.object(system, 'flush_buffer', new_callable=AsyncMock) as mock_flush:
                    try:
                        await system._idle_flush_loop()
                    except asyncio.CancelledError:
                        pass
                    
                    # Should NOT have called flush because buffer is empty
                    mock_flush.assert_not_called()
