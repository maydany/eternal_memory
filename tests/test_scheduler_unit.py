"""
Unit Tests for CronScheduler

Tests the scheduler logic using mocks.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from eternal_memory.scheduling.scheduler import CronScheduler

class TestCronScheduler:
    """Tests for CronScheduler class."""

    @pytest.fixture
    def scheduler(self):
        """Create a scheduler instance."""
        return CronScheduler()

    @pytest.mark.asyncio
    async def test_add_job_registers_correctly(self, scheduler):
        """Test adding a job registers it correctly."""
        mock_func = AsyncMock()
        
        scheduler.add_job(
            name="test_job",
            interval_seconds=60,
            func=mock_func,
            job_type="maintenance"
        )
        
        jobs = scheduler.get_jobs()
        assert len(jobs) == 1
        assert jobs[0]["name"] == "test_job"
        assert jobs[0]["interval_seconds"] == 60
        assert jobs[0]["job_type"] == "maintenance"

    @pytest.mark.asyncio
    async def test_remove_job_success(self, scheduler):
        """Test removing a job succeeds."""
        scheduler.add_job("test_job", 60, AsyncMock())
        
        result = scheduler.remove_job("test_job")
        assert result is True
        assert len(scheduler.get_jobs()) == 0

    @pytest.mark.asyncio
    async def test_remove_system_job_blocked(self, scheduler):
        """Test removing a system job is blocked."""
        scheduler.add_job("system_job", 60, AsyncMock(), is_system=True)
        
        result = scheduler.remove_job("system_job")
        assert result is False
        assert len(scheduler.get_jobs()) == 1

    @pytest.mark.asyncio
    async def test_trigger_job_executes_function(self, scheduler):
        """Test manually triggering a job executes its function."""
        mock_func = AsyncMock()
        scheduler.add_job("test_job", 60, mock_func)
        
        result = await scheduler.trigger_job("test_job")
        
        assert result is True
        mock_func.assert_called_once()
        
        # Verify last_run timestamp was updated
        job_info = scheduler.get_job("test_job")
        assert job_info["last_run"] > 0

    @pytest.mark.asyncio
    async def test_trigger_disabled_job_fails(self, scheduler):
        """Test triggering a disabled job fails."""
        mock_func = AsyncMock()
        scheduler.add_job("test_job", 60, mock_func)
        scheduler.disable_job("test_job")
        
        result = await scheduler.trigger_job("test_job")
        
        assert result is False
        mock_func.assert_not_called()

    @pytest.mark.asyncio
    async def test_enable_disable_job(self, scheduler):
        """Test enabling and disabling jobs."""
        scheduler.add_job("test_job", 60, AsyncMock())
        
        # Default is enabled
        assert scheduler.get_job("test_job")["enabled"] is True
        
        # Disable
        scheduler.disable_job("test_job")
        assert scheduler.get_job("test_job")["enabled"] is False
        
        # Enable
        scheduler.enable_job("test_job")
        assert scheduler.get_job("test_job")["enabled"] is True

    @pytest.mark.asyncio
    async def test_get_job_returns_correct_info(self, scheduler):
        """Test get_job returns correct information."""
        scheduler.add_job("test_job", 120, AsyncMock(), job_type="backup")
        
        info = scheduler.get_job("test_job")
        assert info["name"] == "test_job"
        assert info["job_type"] == "backup"
        assert info["interval_seconds"] == 120
        assert info["next_run_in"] is None  # Not run yet

    @pytest.mark.asyncio
    async def test_start_stop_scheduler(self, scheduler):
        """Test starting and stopping the scheduler."""
        await scheduler.start()
        # Access private member purely for testing state
        assert scheduler._running is True
        assert scheduler._task is not None
        
        await scheduler.stop()
        assert scheduler._running is False

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
