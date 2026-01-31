"""
User Model Management

Manages agent/USER.md as a CURATED understanding of the user.
Only stores long-term valuable insights, not transient conversations.

Following OpenClaw's philosophy:
- Quality threshold: confidence >= 0.7, evidence >= 3
- Daily reflection (not every conversation)
- Backups stored in agent/backups/ (keep 7 most recent)
"""

from pathlib import Path
from typing import Optional, List
from datetime import datetime
import yaml
import aiofiles
import logging

logger = logging.getLogger("eternal_memory.agent.user_model")


class UserModel:
    """
    Manages the curated USER.md file.
    
    Unlike timeline logs (which store everything), this file contains
    only distilled, long-term valuable insights about the user.
    
    Quality Threshold:
        - Confidence >= 0.7 (70%+ certainty)
        - Evidence >= 3 (observed 3+ times)
    
    Backup Policy:
        - Backups stored in agent/backups/
        - Keep 7 most recent backups (1 week worth)
    """
    
    # Quality thresholds (configurable)
    MIN_CONFIDENCE = 0.7
    MIN_EVIDENCE = 3
    MAX_BACKUPS = 7
    
    # Valid sections in USER.md
    VALID_SECTIONS = [
        "Core Identity",
        "Established Preferences",
        "Work Patterns",
        "Communication Style",
        "Technical Context",
        "Constraints"
    ]
    
    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize UserModel.
        
        Args:
            base_path: Path to agent directory. Defaults to ./agent
        """
        if base_path is None:
            base_path = Path.cwd() / "agent"
        
        self.base_path = Path(base_path)
        self.user_file = self.base_path / "USER.md"
        self.backup_dir = self.base_path / "backups"
        
    async def initialize(self) -> None:
        """Create agent/ directory, backups/, and initial USER.md if not exists."""
        # Create agent directory with restricted permissions
        self.base_path.mkdir(exist_ok=True, mode=0o700)
        
        # Create backups directory
        self.backup_dir.mkdir(exist_ok=True, mode=0o700)
        
        if not self.user_file.exists():
            await self._create_initial_user_file()
            logger.info(f"Created initial USER.md at {self.user_file}")
    
    async def _create_initial_user_file(self) -> None:
        """Create initial USER.md template."""
        template = f"""---
version: "1.0.0"
last_updated: "{datetime.now().isoformat()}"
total_updates: 0
---

# User Profile

> 이 파일은 에이전트가 사용자에 대해 학습한 **장기적으로 중요한** 정보만 포함합니다.
> 일상적인 대화는 timeline/ 로그를 참조하세요.

## Core Identity
- Timezone: (학습 중)
- Communication Language: (학습 중)
- Role/Occupation: (학습 중)

## Established Preferences
(장기간 반복 확인된 선호도만 기록)

## Work Patterns
(일관되게 관찰된 작업 패턴만 기록)

## Communication Style
(사용자가 선호하는 소통 방식)

## Technical Context
(현재 프로젝트, 사용 기술 스택)

## Constraints
(사용자가 명시한 제약 사항)
"""
        
        async with aiofiles.open(self.user_file, 'w') as f:
            await f.write(template)
    
    async def read(self) -> str:
        """
        Read entire USER.md content.
        
        Returns:
            Full USER.md content including frontmatter
        """
        if not self.user_file.exists():
            await self.initialize()
        
        async with aiofiles.open(self.user_file, 'r') as f:
            return await f.read()
    
    async def get_metadata(self) -> dict:
        """
        Extract and parse YAML frontmatter.
        
        Returns:
            Dictionary with version, last_updated, total_updates
        """
        content = await self.read()
        
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter_yaml = parts[1]
                return yaml.safe_load(frontmatter_yaml) or {}
        
        return {
            "version": "1.0.0",
            "last_updated": datetime.now().isoformat(),
            "total_updates": 0
        }
    
    async def _create_backup(self) -> Optional[Path]:
        """
        Create a backup of USER.md before modification.
        
        Returns:
            Path to backup file, or None if no backup needed
        """
        if not self.user_file.exists():
            return None
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(exist_ok=True, mode=0o700)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.backup_dir / f"USER_{timestamp}.md"
        
        async with aiofiles.open(self.user_file, 'r') as src:
            content = await src.read()
        async with aiofiles.open(backup_path, 'w') as dst:
            await dst.write(content)
        
        logger.debug(f"Created backup: {backup_path}")
        return backup_path
    
    async def cleanup_old_backups(self) -> int:
        """
        Remove old backups, keeping only MAX_BACKUPS most recent.
        
        Returns:
            Number of backups deleted
        """
        if not self.backup_dir.exists():
            return 0
        
        backups = sorted(
            self.backup_dir.glob("USER_*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        deleted = 0
        for backup in backups[self.MAX_BACKUPS:]:
            backup.unlink()
            deleted += 1
            logger.debug(f"Deleted old backup: {backup}")
        
        return deleted
    
    async def batch_update(self, insights: List[dict]) -> int:
        """
        Batch update USER.md with multiple insights.
        
        Creates ONE backup before all updates, then adds all insights.
        This is the recommended method for profile_reflection job.
        
        Args:
            insights: List of dicts with keys:
                - section: Section name (e.g., "Established Preferences")
                - content: The insight content
                - confidence: Confidence score (0.0-1.0)
                - evidence_count: Number of supporting observations
        
        Returns:
            Number of insights successfully added
        """
        if not insights:
            return 0
        
        # Filter insights by quality threshold
        valid_insights = [
            ins for ins in insights
            if ins.get("confidence", 0) >= self.MIN_CONFIDENCE
            and ins.get("evidence_count", 0) >= self.MIN_EVIDENCE
            and ins.get("section") in self.VALID_SECTIONS
            and ins.get("content")
        ]
        
        if not valid_insights:
            logger.info("No insights met quality threshold")
            return 0
        
        # Create ONE backup before all updates
        await self._create_backup()
        
        # Read current content
        current_content = await self.read()
        
        # Parse frontmatter and body
        if current_content.startswith("---"):
            parts = current_content.split("---", 2)
            frontmatter = yaml.safe_load(parts[1]) if len(parts) > 1 else {}
            body = parts[2] if len(parts) > 2 else ""
        else:
            frontmatter = {"version": "1.0.0", "total_updates": 0}
            body = current_content
        
        # Add all insights
        added = 0
        timestamp = datetime.now().strftime("%Y-%m-%d")
        
        for insight in valid_insights:
            section = insight["section"]
            content = insight["content"]
            confidence = insight["confidence"]
            evidence_count = insight["evidence_count"]
            
            section_marker = f"## {section}"
            new_item = f"- [{timestamp}] {content} (confidence: {confidence:.2f}, evidence: {evidence_count})"
            
            # Insert into body
            if section_marker not in body:
                body += f"\n\n{section_marker}\n{new_item}\n"
            else:
                lines = body.split('\n')
                new_lines = []
                found_section = False
                inserted = False
                
                for line in lines:
                    new_lines.append(line)
                    if line.strip() == section_marker:
                        found_section = True
                    elif found_section and line.startswith("## ") and not inserted:
                        new_lines.insert(-1, new_item)
                        inserted = True
                        found_section = False
                
                if found_section and not inserted:
                    new_lines.append(new_item)
                
                body = '\n'.join(new_lines)
            
            added += 1
        
        # Update metadata
        frontmatter["last_updated"] = datetime.now().isoformat()
        frontmatter["total_updates"] = frontmatter.get("total_updates", 0) + added
        
        # Reconstruct and write file
        final_content = f"""---
{yaml.dump(frontmatter, default_flow_style=False)}---
{body}
"""
        
        async with aiofiles.open(self.user_file, 'w') as f:
            await f.write(final_content)
        
        logger.info(f"Added {added} insights to USER.md")
        
        # Cleanup old backups
        await self.cleanup_old_backups()
        
        return added
    
    async def append_insight(
        self, 
        section: str, 
        content: str,
        confidence: float = 0.8,
        evidence_count: int = 1
    ) -> None:
        """
        Append a single HIGH-VALUE insight to USER.md.
        
        Note: For batch updates, use batch_update() instead.
        This method creates a backup for each call.
        
        Args:
            section: Section name (e.g., "Established Preferences")
            content: The insight content
            confidence: Confidence score (0.0-1.0)
            evidence_count: Number of supporting observations
        
        Raises:
            ValueError: If section is invalid or quality threshold not met
        """
        # Validate quality threshold
        if confidence < self.MIN_CONFIDENCE:
            raise ValueError(f"Confidence {confidence} below threshold {self.MIN_CONFIDENCE}")
        if evidence_count < self.MIN_EVIDENCE:
            raise ValueError(f"Evidence count {evidence_count} below threshold {self.MIN_EVIDENCE}")
        
        # Validate section
        if section not in self.VALID_SECTIONS:
            raise ValueError(f"Invalid section '{section}'. Must be one of: {self.VALID_SECTIONS}")
        
        # Use batch_update for single insight
        await self.batch_update([{
            "section": section,
            "content": content,
            "confidence": confidence,
            "evidence_count": evidence_count
        }])
    
    async def get_context_string(self) -> str:
        """
        Get USER.md content formatted for system prompt injection.
        
        Returns:
            Markdown-formatted user context (without frontmatter)
        """
        content = await self.read()
        
        # Remove YAML frontmatter for cleaner prompt
        if content.startswith("---"):
            parts = content.split("---", 2)
            return parts[2].strip() if len(parts) > 2 else content
        
        return content
