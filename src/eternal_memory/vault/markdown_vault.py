"""
Markdown Memory Vault

Implements the human-readable Markdown storage as specified in Section 2.3.
All memories are stored in the ~/.openclaw/memory/ directory.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiofiles

from eternal_memory.security.sanitizer import Sanitizer


class MarkdownVault:
    """
    Manages the Markdown Memory Vault for human-readable storage.
    
    Directory structure:
    ~/.openclaw/
    ├── memory/
    │   ├── profile.md
    │   ├── index.json
    │   ├── timeline/
    │   └── knowledge/
    ├── storage/
    └── config/
    """
    
    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize the vault.
        
        Args:
            base_path: Base path for the vault. Defaults to ~/.openclaw
        """
        self.base_path = Path(base_path or os.path.expanduser("~/.openclaw"))
        self.memory_path = self.base_path / "memory"
        self.storage_path = self.base_path / "storage"
        self.config_path = self.base_path / "config"
        self.sanitizer = Sanitizer()
    
    async def initialize(self) -> None:
        """
        Create the vault directory structure and set permissions.
        """
        # Create directories
        directories = [
            self.memory_path,
            self.memory_path / "timeline",
            self.memory_path / "knowledge",
            self.memory_path / "knowledge" / "coding",
            self.memory_path / "knowledge" / "projects",
            self.memory_path / "personal",
            self.storage_path,
            self.storage_path / "vector_store",
            self.storage_path / "blobs",
            self.config_path,
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Set secure permissions (chmod 700)
        os.chmod(self.memory_path, 0o700)
        
        # Create initial files
        await self._create_profile()
        await self._create_index()
        await self._create_config()
    
    async def _create_profile(self) -> None:
        """Create the profile.md file."""
        profile_path = self.memory_path / "profile.md"
        if not profile_path.exists():
            content = """# User Profile

## Basic Information
- Created: {date}

## Preferences
- (To be learned from interactions)

## Core Settings
- Language: Auto-detect
- Timezone: Auto-detect
""".format(date=datetime.now().strftime("%Y-%m-%d"))
            
            async with aiofiles.open(profile_path, "w") as f:
                await f.write(content)
    
    async def _create_index(self) -> None:
        """Create the index.json for category mapping."""
        index_path = self.memory_path / "index.json"
        if not index_path.exists():
            async with aiofiles.open(index_path, "w") as f:
                await f.write('{"categories": [], "last_updated": null}')
    
    async def _create_config(self) -> None:
        """Create the memory_config.yaml file."""
        config_file = self.config_path / "memory_config.yaml"
        if not config_file.exists():
            content = """# Eternal Memory Configuration

# Database connection
database:
  host: localhost
  port: 5432
  name: eternal_memory

# Retention policy
retention:
  stale_days_threshold: 30
  archive_low_importance: true
  importance_threshold: 0.3

# Embedding model
embedding:
  model: text-embedding-ada-002
  dimension: 1536

# Consolidation schedule
consolidation:
  enabled: true
  interval_hours: 24
"""
            async with aiofiles.open(config_file, "w") as f:
                await f.write(content)
    
    async def append_to_timeline(
        self,
        content: str,
        timestamp: datetime,
    ) -> None:
        """
        Append an entry to the timeline.
        
        Timeline files are organized by month: timeline/2026-01.md
        """
        filename = timestamp.strftime("%Y-%m") + ".md"
        filepath = self.memory_path / "timeline" / filename
        
        # Sanitize content
        safe_content = self.sanitizer.sanitize(content)
        
        # Create file if doesn't exist
        if not filepath.exists():
            async with aiofiles.open(filepath, "w") as f:
                await f.write(f"# Timeline - {timestamp.strftime('%B %Y')}\n\n")
        
        # Append entry
        entry = f"- [{timestamp.strftime('%Y-%m-%d %H:%M')}] {safe_content}\n"
        async with aiofiles.open(filepath, "a") as f:
            await f.write(entry)
    
    async def ensure_category_file(self, category_path: str) -> Path:
        """
        Ensure a category markdown file exists.
        
        Creates the file and parent directories if needed.
        """
        parts = category_path.split("/")
        
        # Build file path
        if len(parts) == 1:
            filepath = self.memory_path / f"{parts[0]}.md"
        else:
            dir_path = self.memory_path / "/".join(parts[:-1])
            dir_path.mkdir(parents=True, exist_ok=True)
            filepath = self.memory_path / f"{category_path}.md"
        
        # Create file if doesn't exist
        if not filepath.exists():
            filepath.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(filepath, "w") as f:
                await f.write(f"# {parts[-1].title()}\n\n")
                await f.write(f"Category: `{category_path}`\n\n")
                await f.write("## Summary\n\n(Auto-generated summary will appear here)\n\n")
                await f.write("## Memories\n\n")
        
        return filepath
    
    async def append_to_category(
        self,
        category_path: str,
        content: str,
        memory_type: str,
        timestamp: datetime,
    ) -> None:
        """
        Append a memory to a category file.
        """
        filepath = await self.ensure_category_file(category_path)
        
        # Sanitize content
        safe_content = self.sanitizer.sanitize(content)
        
        # Format entry
        type_emoji = {
            "fact": "📝",
            "preference": "⭐",
            "event": "📅",
            "plan": "🎯",
        }.get(memory_type, "📝")
        
        entry = f"- {type_emoji} [{timestamp.strftime('%Y-%m-%d')}] {safe_content}\n"
        
        async with aiofiles.open(filepath, "a") as f:
            await f.write(entry)
    
    async def read_category_file(self, category_path: str) -> Optional[str]:
        """
        Read the contents of a category file.
        """
        filepath = self.memory_path / f"{category_path}.md"
        
        if not filepath.exists():
            return None
        
        async with aiofiles.open(filepath, "r") as f:
            return await f.read()
    
    async def update_category_summary(
        self,
        category_path: str,
        summary: str,
    ) -> None:
        """
        Update the summary section of a category file.
        """
        filepath = await self.ensure_category_file(category_path)
        
        async with aiofiles.open(filepath, "r") as f:
            content = await f.read()
        
        # Replace summary section
        safe_summary = self.sanitizer.sanitize(summary)
        
        # Find and replace summary section
        if "## Summary" in content:
            parts = content.split("## Summary")
            before = parts[0]
            after_parts = parts[1].split("##", 1)
            after = "##" + after_parts[1] if len(after_parts) > 1 else ""
            
            new_content = f"{before}## Summary\n\n{safe_summary}\n\n{after}"
        else:
            new_content = content
        
        async with aiofiles.open(filepath, "w") as f:
            await f.write(new_content)
    
    async def archive_items(
        self,
        category_path: str,
        summary: str,
        original_count: int,
    ) -> None:
        """
        Archive summarized items.
        """
        archive_dir = self.memory_path / "archived"
        archive_dir.mkdir(exist_ok=True)
        
        filepath = archive_dir / f"{category_path.replace('/', '_')}.md"
        
        safe_summary = self.sanitizer.sanitize(summary)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        entry = f"\n## Archive - {timestamp}\n\n"
        entry += f"Summarized {original_count} items:\n\n{safe_summary}\n"
        
        async with aiofiles.open(filepath, "a") as f:
            await f.write(entry)
    
    async def get_profile(self) -> str:
        """Get the user profile content."""
        filepath = self.memory_path / "profile.md"
        if filepath.exists():
            async with aiofiles.open(filepath, "r") as f:
                return await f.read()
        return ""
    
    async def update_profile(self, section: str, content: str) -> None:
        """Update a section in the user profile."""
        profile = await self.get_profile()
        safe_content = self.sanitizer.sanitize(content)
        
        # Simple append for now
        async with aiofiles.open(self.memory_path / "profile.md", "a") as f:
            await f.write(f"\n## {section}\n{safe_content}\n")
