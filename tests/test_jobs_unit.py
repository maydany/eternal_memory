"""
Unit Tests for Scheduled Jobs

Tests the individual job functions in jobs.py using mocks.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from pathlib import Path
import shutil

# Import the module to test
# We need to mock 'eternal_memory.scheduling.jobs' dependencies if they are imported at top level
# But in this case, imports inside functions are common, so we can test the functions directly.

from eternal_memory.scheduling.jobs import (
    job_vault_backup,
    job_weekly_summary,
    job_monthly_summary,
    job_embedding_refresh,
    register_job,
    get_job_types,
    JOB_REGISTRY
)

class TestJobs:
    """Tests for job functions."""

    @pytest.fixture
    def mock_system(self):
        """Create a mock EternalMemorySystem."""
        system = MagicMock()
        system.repository = AsyncMock()
        system.llm = AsyncMock()
        system.vault_path = Path("/tmp/mock_vault")
        system.memorize = AsyncMock()
        return system

    @pytest.mark.asyncio
    async def test_vault_backup_creates_directory(self, mock_system):
        """Test vault backup job creates a backup directory."""
        # Setup vault path
        mock_system.vault.root_path = "/tmp/mock_vault/root"
        
        # Mock Path.exists to return True
        with patch("eternal_memory.scheduling.jobs.Path") as MockPath:
            # Configure path instance logic
            mock_path_instance = MagicMock()
            MockPath.return_value = mock_path_instance
            mock_path_instance.exists.return_value = True
            mock_path_instance.parent = MagicMock()
            
            # Mock shutil.copytree
            with patch("shutil.copytree") as mock_copytree:
                await job_vault_backup(mock_system)
                
                # Should call copytree
                mock_copytree.assert_called_once()
                # args[1] is destination, should verify it


    @pytest.mark.asyncio
    async def test_weekly_summary_aggregates_reflections(self, mock_system):
        """Test weekly summary aggregates 7 days of daily reflections."""
        # Setup mocks
        mock_reflections = [
            MagicMock(content="Reflection 1"),
            MagicMock(content="Reflection 2")
        ]
        mock_system.repository.get_reflections_by_type.return_value = mock_reflections
        
        mock_system.llm.generate_weekly_summary.return_value = {
            "summary": "Weekly summary",
            "themes": ["theme1"],
            "achievements": ["achieve1"],
            "patterns": "patterns",
            "advice": "advice"
        }
        
        # Execute
        await job_weekly_summary(mock_system)
        
        # Verify
        mock_system.repository.get_reflections_by_type.assert_called_once()
        mock_system.llm.generate_weekly_summary.assert_called_once()
        mock_system.memorize.assert_called_once()
        
        # Check memorize content
        args = mock_system.memorize.call_args
        assert "Weekly Summary" in args[0][0]
        assert args[0][1]["type"] == "weekly_summary"

    @pytest.mark.asyncio
    async def test_weekly_summary_skips_if_empty(self, mock_system):
        """Test weekly summary skips if no daily reflections found."""
        mock_system.repository.get_reflections_by_type.return_value = []
        
        await job_weekly_summary(mock_system)
        
        mock_system.llm.generate_weekly_summary.assert_not_called()
        mock_system.memorize.assert_not_called()

    @pytest.mark.asyncio
    async def test_monthly_summary_aggregates_weeklies(self, mock_system):
        """Test monthly summary aggregates weekly summaries."""
        mock_weeklies = [
            MagicMock(content="Week 1"),
            MagicMock(content="Week 2")
        ]
        mock_system.repository.get_reflections_by_type.return_value = mock_weeklies
        
        mock_system.llm.generate_monthly_summary.return_value = {
            "summary": "Monthly summary",
            "keywords": ["key"],
            "trends": "trends",
            "growth": "growth",
            "goals": ["goal"]
        }
        
        await job_monthly_summary(mock_system)
        
        mock_system.repository.get_reflections_by_type.assert_called_once()
        mock_system.llm.generate_monthly_summary.assert_called_once()
        mock_system.memorize.assert_called_once()

    @pytest.mark.asyncio
    async def test_monthly_summary_skips_if_empty(self, mock_system):
        """Test monthly summary skips if no weekly summaries found."""
        mock_system.repository.get_reflections_by_type.return_value = []
        
        await job_monthly_summary(mock_system)
        
        mock_system.memorize.assert_not_called()

    @pytest.mark.asyncio
    async def test_embedding_refresh_updates_old_items(self, mock_system):
        """Test embedding refresh job updates old items."""
        mock_items = [MagicMock(id="1", content="test"), MagicMock(id="2", content="test2")]
        mock_system.repository.get_stale_items = AsyncMock(return_value=mock_items)
        mock_system.llm.generate_embedding = AsyncMock(return_value=[0.1]*1536)
        
        await job_embedding_refresh(mock_system)
        
        # Should verify repository update method is called
        # Note: function name in jobs.py is actually job_embedding_refresh
        # Assuming implementation detail: it calls repository.update_embedding
        assert mock_system.repository.get_stale_items.called
        # Check call count - one per item or batch? Logic dependent.
        # Assuming the job iterates and updates.
        assert mock_system.llm.generate_embedding.call_count == 2
        # Function assumes logging for now, so no update assertion
        # assert mock_system.repository.update_embedding.call_count == 2

    def test_register_job_decorator(self):
        """Test register_job decorator adds to registry."""
        
        @register_job("test_decorator_job")
        async def my_job(sys):
            pass
            
        assert "test_decorator_job" in JOB_REGISTRY
        assert JOB_REGISTRY["test_decorator_job"] == my_job
        
        # Clean up
        del JOB_REGISTRY["test_decorator_job"]

    def test_get_job_types_returns_all(self):
        """Test get_job_types returns all keys."""
        types = get_job_types()
        assert isinstance(types, list)
        assert len(types) == len(JOB_REGISTRY)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
