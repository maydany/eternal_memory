"""
Tests for Security Sanitizer

Tests input sanitization and path validation.
"""

import pytest

from eternal_memory.security.sanitizer import Sanitizer


class TestSanitizer:
    """Tests for Sanitizer class."""
    
    @pytest.fixture
    def sanitizer(self):
        return Sanitizer()
    
    def test_sanitize_normal_text(self, sanitizer):
        """Test that normal text passes through."""
        text = "This is normal text with no special characters."
        result = sanitizer.sanitize(text)
        assert result == text
    
    def test_sanitize_removes_script_tags(self, sanitizer):
        """Test removal of script tags."""
        text = "Hello <script>alert('xss')</script> World"
        result = sanitizer.sanitize(text)
        assert "<script>" not in result
        assert "alert" not in result
        assert "Hello" in result
        assert "World" in result
    
    def test_sanitize_removes_html_tags(self, sanitizer):
        """Test removal of HTML tags."""
        text = "<div><b>Bold</b> and <i>italic</i></div>"
        result = sanitizer.sanitize(text)
        assert "<div>" not in result
        assert "<b>" not in result
        assert "Bold" in result
        assert "italic" in result
    
    def test_sanitize_removes_control_characters(self, sanitizer):
        """Test removal of control characters."""
        text = "Normal\x00text\x1fwith\x7fcontrol"
        result = sanitizer.sanitize(text)
        assert "\x00" not in result
        assert "\x1f" not in result
        assert "\x7f" not in result
        assert "Normal" in result
    
    def test_sanitize_removes_path_traversal(self, sanitizer):
        """Test removal of path traversal attempts."""
        text = "Look at ../../../etc/passwd"
        result = sanitizer.sanitize(text)
        assert "../" not in result
    
    def test_sanitize_truncates_long_text(self, sanitizer):
        """Test truncation of very long text."""
        text = "a" * 20000
        result = sanitizer.sanitize(text)
        assert len(result) <= 10100  # 10000 + "[truncated]"
        assert "[truncated]" in result
    
    def test_sanitize_empty_string(self, sanitizer):
        """Test empty string handling."""
        assert sanitizer.sanitize("") == ""
        assert sanitizer.sanitize(None) == ""
    
    def test_sanitize_preserves_markdown(self, sanitizer):
        """Test that markdown is preserved."""
        text = "**bold** and *italic* with `code`"
        result = sanitizer.sanitize(text)
        assert "**bold**" in result
        assert "*italic*" in result
        assert "`code`" in result


class TestPathSanitization:
    """Tests for path sanitization."""
    
    @pytest.fixture
    def sanitizer(self):
        return Sanitizer()
    
    def test_sanitize_path_valid(self, sanitizer):
        """Test valid path sanitization."""
        path = "knowledge/coding/python"
        result = sanitizer.sanitize_path(path)
        assert result == path
    
    def test_sanitize_path_removes_traversal(self, sanitizer):
        """Test path traversal removal."""
        path = "../../../etc/passwd"
        result = sanitizer.sanitize_path(path)
        assert "../" not in result if result else True
    
    def test_sanitize_path_removes_null_bytes(self, sanitizer):
        """Test null byte removal."""
        path = "knowledge\x00/coding"
        result = sanitizer.sanitize_path(path)
        assert "\x00" not in result if result else True
    
    def test_sanitize_path_invalid_characters(self, sanitizer):
        """Test rejection of paths with invalid characters."""
        path = "knowledge/<script>"
        result = sanitizer.sanitize_path(path)
        assert result is None


class TestCategoryPathValidation:
    """Tests for category path validation."""
    
    @pytest.fixture
    def sanitizer(self):
        return Sanitizer()
    
    def test_validate_valid_path(self, sanitizer):
        """Test valid paths."""
        assert sanitizer.validate_category_path("knowledge/coding/python")
        assert sanitizer.validate_category_path("personal")
        assert sanitizer.validate_category_path("projects/my-project")
    
    def test_validate_rejects_traversal(self, sanitizer):
        """Test rejection of path traversal."""
        assert not sanitizer.validate_category_path("../etc/passwd")
        assert not sanitizer.validate_category_path("knowledge/../../../etc")
    
    def test_validate_rejects_special_chars(self, sanitizer):
        """Test rejection of special characters."""
        assert not sanitizer.validate_category_path("knowledge/<script>")
        assert not sanitizer.validate_category_path("knowledge/test;rm -rf")
    
    def test_validate_rejects_deep_paths(self, sanitizer):
        """Test rejection of too-deep paths."""
        deep_path = "/".join(["level"] * 10)
        assert not sanitizer.validate_category_path(deep_path)
    
    def test_validate_empty_path(self, sanitizer):
        """Test rejection of empty path."""
        assert not sanitizer.validate_category_path("")
        assert not sanitizer.validate_category_path(None)
