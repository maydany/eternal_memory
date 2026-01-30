"""
Security Sanitizer

Implements input sanitization as specified in Section 5.3:
- Remove script tags and control characters
- Validate input format
- Manage file permissions
"""

import html
import os
import re
from pathlib import Path
from typing import Optional


class Sanitizer:
    """
    Sanitizes input text before writing to Markdown files.
    
    Removes potentially dangerous content:
    - Script tags
    - HTML tags (except safe markdown-compatible ones)
    - Control characters
    - Path traversal attempts
    """
    
    # Regex patterns for dangerous content
    SCRIPT_PATTERN = re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL)
    HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
    CONTROL_CHARS_PATTERN = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
    PATH_TRAVERSAL_PATTERN = re.compile(r'\.\./')
    
    # Safe markdown elements we want to preserve
    SAFE_MD_ELEMENTS = {'**', '__', '*', '_', '`', '```', '#', '-', '+', '>', '[', ']', '(', ')'}
    
    def sanitize(self, text: str) -> str:
        """
        Sanitize input text for safe storage.
        
        Args:
            text: Raw input text
            
        Returns:
            Sanitized text safe for Markdown storage
        """
        if not text:
            return ""
        
        # Remove script tags
        text = self.SCRIPT_PATTERN.sub('', text)
        
        # HTML escape dangerous characters but preserve markdown
        text = self._escape_html_preserve_markdown(text)
        
        # Remove control characters
        text = self.CONTROL_CHARS_PATTERN.sub('', text)
        
        # Remove path traversal attempts
        text = self.PATH_TRAVERSAL_PATTERN.sub('', text)
        
        # Limit length to prevent DoS
        max_length = 10000
        if len(text) > max_length:
            text = text[:max_length] + "... [truncated]"
        
        return text.strip()
    
    def _escape_html_preserve_markdown(self, text: str) -> str:
        """
        Escape HTML but preserve markdown formatting.
        """
        # First, remove all HTML tags
        text = self.HTML_TAG_PATTERN.sub('', text)
        
        # Escape remaining HTML entities
        text = html.escape(text, quote=False)
        
        # Unescape common markdown-compatible entities
        text = text.replace('&amp;', '&')  # Allow ampersand
        text = text.replace('&lt;', '<')    # Allow for comparison operators in code
        text = text.replace('&gt;', '>')    # Allow for comparison operators in code
        
        return text
    
    def sanitize_path(self, path: str) -> Optional[str]:
        """
        Sanitize a file path to prevent traversal attacks.
        
        Args:
            path: Raw path string
            
        Returns:
            Sanitized path or None if invalid
        """
        if not path:
            return None
        
        # Remove path traversal
        path = self.PATH_TRAVERSAL_PATTERN.sub('', path)
        
        # Remove null bytes
        path = path.replace('\x00', '')
        
        # Only allow alphanumeric, dash, underscore, slash
        if not re.match(r'^[\w\-/]+$', path):
            return None
        
        return path
    
    def validate_category_path(self, path: str) -> bool:
        """
        Validate a category path format.
        
        Valid: knowledge/coding/python
        Invalid: ../../../etc/passwd, <script>alert(1)</script>
        """
        if not path:
            return False
        
        # Check for path traversal
        if '..' in path:
            return False
        
        # Must be alphanumeric with slashes
        if not re.match(r'^[\w\-]+(/[\w\-]+)*$', path):
            return False
        
        # Limit depth
        if path.count('/') > 5:
            return False
        
        return True
    
    @staticmethod
    def set_secure_permissions(path: Path) -> None:
        """
        Set secure file permissions (chmod 700 for directories, 600 for files).
        """
        if path.is_dir():
            os.chmod(path, 0o700)
        else:
            os.chmod(path, 0o600)
    
    @staticmethod
    def validate_file_size(path: Path, max_bytes: int = 10 * 1024 * 1024) -> bool:
        """
        Validate file size doesn't exceed maximum.
        
        Default max: 10MB
        """
        if not path.exists():
            return True
        
        return path.stat().st_size <= max_bytes
