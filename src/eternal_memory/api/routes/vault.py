"""
Vault API Routes

Endpoints for browsing and editing the Memory Vault.
"""

import os
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from eternal_memory.vault.markdown_vault import MarkdownVault

router = APIRouter()

# Default vault path
VAULT_BASE = Path.home() / ".openclaw"


class FileContent(BaseModel):
    """File content for reading/writing."""
    content: str


class FileNode(BaseModel):
    """File tree node."""
    name: str
    path: str
    is_directory: bool
    children: Optional[list["FileNode"]] = None


def build_file_tree(directory: Path, base: Path) -> list[FileNode]:
    """Build a file tree structure."""
    nodes = []
    
    try:
        for item in sorted(directory.iterdir()):
            relative_path = str(item.relative_to(base))
            
            if item.is_dir():
                children = build_file_tree(item, base)
                nodes.append(FileNode(
                    name=item.name,
                    path=relative_path,
                    is_directory=True,
                    children=children,
                ))
            elif item.suffix == ".md":
                nodes.append(FileNode(
                    name=item.name,
                    path=relative_path,
                    is_directory=False,
                ))
    except PermissionError:
        pass
    
    return nodes


@router.get("/tree")
async def get_file_tree():
    """
    Get the file tree structure of the Memory Vault.
    
    Returns a hierarchical structure of all directories
    and Markdown files in ~/.openclaw/memory/
    """
    memory_path = VAULT_BASE / "memory"
    
    if not memory_path.exists():
        vault = MarkdownVault()
        await vault.initialize()
    
    tree = build_file_tree(memory_path, VAULT_BASE)
    
    return {
        "root": str(VAULT_BASE),
        "tree": tree,
    }


@router.get("/file/{file_path:path}")
async def read_file(file_path: str):
    """
    Read the content of a Markdown file.
    
    Args:
        file_path: Relative path from ~/.openclaw/
    """
    full_path = VAULT_BASE / file_path
    
    # Security check: prevent path traversal
    try:
        full_path.resolve().relative_to(VAULT_BASE.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    if not full_path.suffix == ".md":
        raise HTTPException(status_code=400, detail="Only .md files allowed")
    
    async with aiofiles.open(full_path, "r") as f:
        content = await f.read()
    
    return {
        "path": file_path,
        "content": content,
        "name": full_path.name,
    }


@router.put("/file/{file_path:path}")
async def write_file(file_path: str, file_content: FileContent):
    """
    Update the content of a Markdown file.
    
    After updating, the vector index should be refreshed
    (handled by the consolidation pipeline).
    """
    full_path = VAULT_BASE / file_path
    
    # Security check
    try:
        full_path.resolve().relative_to(VAULT_BASE.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not full_path.suffix == ".md":
        raise HTTPException(status_code=400, detail="Only .md files allowed")
    
    # Ensure parent directory exists
    full_path.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiofiles.open(full_path, "w") as f:
        await f.write(file_content.content)
    
    return {
        "success": True,
        "path": file_path,
        "message": "File updated. Vector index will be refreshed on next consolidation.",
    }


@router.get("/search")
async def search_vault(q: str):
    """
    Full-text search across the Memory Vault.
    
    Searches all Markdown files for the given query.
    """
    memory_path = VAULT_BASE / "memory"
    results = []
    
    if not memory_path.exists():
        return {"query": q, "results": []}
    
    for md_file in memory_path.rglob("*.md"):
        try:
            async with aiofiles.open(md_file, "r") as f:
                content = await f.read()
            
            if q.lower() in content.lower():
                # Find matching lines
                lines = content.split("\n")
                matches = [
                    {"line": i + 1, "content": line.strip()}
                    for i, line in enumerate(lines)
                    if q.lower() in line.lower()
                ][:5]  # Limit to 5 matches per file
                
                results.append({
                    "path": str(md_file.relative_to(VAULT_BASE)),
                    "name": md_file.name,
                    "matches": matches,
                })
        except Exception:
            continue
    
    return {
        "query": q,
        "results": results,
        "total_files": len(results),
    }
