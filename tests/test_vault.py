"""
Tests for Markdown Vault

Tests the MarkdownVault file operations and directory structure.
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from eternal_memory.vault.markdown_vault import MarkdownVault


@pytest.fixture
def temp_vault():
    """Create a temporary vault for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault = MarkdownVault(base_path=tmpdir)
        yield vault


class TestMarkdownVault:
    """Tests for MarkdownVault."""
    
    @pytest.mark.asyncio
    async def test_initialize_creates_directories(self, temp_vault):
        """Test that initialize creates the directory structure."""
        await temp_vault.initialize()
        
        # Check directories exist
        assert temp_vault.memory_path.exists()
        assert (temp_vault.memory_path / "timeline").exists()
        assert (temp_vault.memory_path / "knowledge").exists()
        assert temp_vault.storage_path.exists()
        assert temp_vault.config_path.exists()
    
    @pytest.mark.asyncio
    async def test_initialize_creates_profile(self, temp_vault):
        """Test that initialize creates profile.md."""
        await temp_vault.initialize()
        
        profile_path = temp_vault.memory_path / "profile.md"
        assert profile_path.exists()
        
        content = profile_path.read_text()
        assert "# User Profile" in content
    
    @pytest.mark.asyncio
    async def test_initialize_creates_config(self, temp_vault):
        """Test that initialize creates memory_config.yaml."""
        await temp_vault.initialize()
        
        config_path = temp_vault.config_path / "memory_config.yaml"
        assert config_path.exists()
    
    @pytest.mark.asyncio
    async def test_append_to_timeline(self, temp_vault):
        """Test appending to timeline."""
        await temp_vault.initialize()
        
        now = datetime.now()
        await temp_vault.append_to_timeline("Test entry", now)
        
        filename = now.strftime("%Y-%m") + ".md"
        filepath = temp_vault.memory_path / "timeline" / filename
        
        assert filepath.exists()
        content = filepath.read_text()
        assert "Test entry" in content
    
    @pytest.mark.asyncio
    async def test_ensure_category_file(self, temp_vault):
        """Test creating category files."""
        await temp_vault.initialize()
        
        filepath = await temp_vault.ensure_category_file("knowledge/coding/python")
        
        assert filepath.exists()
        content = filepath.read_text()
        assert "# Python" in content
        assert "knowledge/coding/python" in content
    
    @pytest.mark.asyncio
    async def test_append_to_category(self, temp_vault):
        """Test appending memories to category."""
        await temp_vault.initialize()
        
        await temp_vault.append_to_category(
            category_path="knowledge/coding/python",
            content="Python uses indentation for blocks",
            memory_type="fact",
            timestamp=datetime.now(),
        )
        
        content = await temp_vault.read_category_file("knowledge/coding/python")
        assert "Python uses indentation for blocks" in content
        assert "📝" in content  # Fact emoji
    
    @pytest.mark.asyncio
    async def test_different_memory_types(self, temp_vault):
        """Test that different memory types get different emojis."""
        await temp_vault.initialize()
        
        types_emojis = {
            "fact": "📝",
            "preference": "⭐",
            "event": "📅",
            "plan": "🎯",
        }
        
        for mem_type, emoji in types_emojis.items():
            await temp_vault.append_to_category(
                category_path="test",
                content=f"Test {mem_type}",
                memory_type=mem_type,
                timestamp=datetime.now(),
            )
        
        content = await temp_vault.read_category_file("test")
        for emoji in types_emojis.values():
            assert emoji in content
    
    @pytest.mark.asyncio
    async def test_update_category_summary(self, temp_vault):
        """Test updating category summary."""
        await temp_vault.initialize()
        
        await temp_vault.ensure_category_file("knowledge/test")
        await temp_vault.update_category_summary(
            "knowledge/test",
            "This is a test summary"
        )
        
        content = await temp_vault.read_category_file("knowledge/test")
        assert "This is a test summary" in content
    
    @pytest.mark.asyncio
    async def test_secure_permissions(self, temp_vault):
        """Test that memory directory has secure permissions."""
        await temp_vault.initialize()
        
        # Check memory directory permissions
        mode = os.stat(temp_vault.memory_path).st_mode
        # Should be 0o700 (owner read/write/execute only)
        assert (mode & 0o777) == 0o700


class TestSanitization:
    """Tests for content sanitization in vault."""
    
    @pytest.mark.asyncio
    async def test_sanitize_script_tags(self, temp_vault):
        """Test that script tags are removed."""
        await temp_vault.initialize()
        
        malicious = "<script>alert('xss')</script>Safe content"
        await temp_vault.append_to_category(
            category_path="test",
            content=malicious,
            memory_type="fact",
            timestamp=datetime.now(),
        )
        
        content = await temp_vault.read_category_file("test")
        assert "<script>" not in content
        assert "Safe content" in content
    
    @pytest.mark.asyncio
    async def test_sanitize_html_tags(self, temp_vault):
        """Test that HTML tags are removed."""
        await temp_vault.initialize()
        
        html_content = "<b>Bold</b> and <script>bad</script> content"
        await temp_vault.append_to_category(
            category_path="test",
            content=html_content,
            memory_type="fact",
            timestamp=datetime.now(),
        )
        
        content = await temp_vault.read_category_file("test")
        assert "<b>" not in content
        assert "Bold" in content
