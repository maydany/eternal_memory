"""
Chat Sessions API Routes

Server-side session persistence for cross-device access.
Replaces localStorage-based session storage in frontend.
"""

import json
import os
from datetime import datetime
from typing import Optional
from uuid import UUID

import asyncpg
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["sessions"])


def parse_messages(messages_data) -> list[dict]:
    """Parse messages field from JSONB - asyncpg may return str or list."""
    if isinstance(messages_data, str):
        return json.loads(messages_data)
    elif isinstance(messages_data, list):
        return messages_data
    else:
        return []


# --- Pydantic Models ---

class MessageModel(BaseModel):
    """Chat message model."""
    id: str
    role: str  # 'user' | 'assistant' | 'system'
    content: str
    timestamp: str  # ISO string
    memoriesRetrieved: Optional[list] = None
    memoriesStored: Optional[list] = None
    processingInfo: Optional[dict] = None


class SessionCreate(BaseModel):
    """Request model for creating a new session."""
    name: str = "New Chat"


class SessionUpdate(BaseModel):
    """Request model for updating a session."""
    name: Optional[str] = None
    messages: Optional[list[dict]] = None
    mode: Optional[str] = None
    context_summary: Optional[str] = None
    summarized_count: Optional[int] = None
    selected_message_id: Optional[str] = None


class SessionResponse(BaseModel):
    """Response model for a session."""
    id: str
    name: str
    messages: list[dict]
    mode: str
    context_summary: Optional[str] = None
    summarized_count: int = 0
    selected_message_id: Optional[str] = None
    created_at: str
    last_active_at: str


class SessionListItem(BaseModel):
    """Minimal session info for listing."""
    id: str
    name: str
    mode: str
    message_count: int
    created_at: str
    last_active_at: str


# --- Helper Functions ---

async def get_db_connection():
    """Get database connection."""
    return await asyncpg.connect(
        os.getenv("DATABASE_URL", "postgresql://localhost/eternal_memory")
    )


# --- API Endpoints ---

@router.get("", response_model=list[SessionListItem])
async def list_sessions():
    """
    List all chat sessions (without full message content).
    Returns sessions ordered by last_active_at descending.
    """
    conn = await get_db_connection()
    try:
        rows = await conn.fetch("""
            SELECT 
                id, name, mode, 
                jsonb_array_length(messages) as message_count,
                created_at, last_active_at
            FROM chat_sessions
            ORDER BY last_active_at DESC
        """)
        
        return [
            SessionListItem(
                id=str(row["id"]),
                name=row["name"],
                mode=row["mode"],
                message_count=row["message_count"],
                created_at=row["created_at"].isoformat(),
                last_active_at=row["last_active_at"].isoformat(),
            )
            for row in rows
        ]
    finally:
        await conn.close()


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: UUID):
    """
    Get a specific session with full message content.
    """
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("""
            SELECT * FROM chat_sessions WHERE id = $1
        """, session_id)
        
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return SessionResponse(
            id=str(row["id"]),
            name=row["name"],
            messages=parse_messages(row["messages"]),
            mode=row["mode"],
            context_summary=row["context_summary"],
            summarized_count=row["summarized_count"] or 0,
            selected_message_id=row["selected_message_id"],
            created_at=row["created_at"].isoformat(),
            last_active_at=row["last_active_at"].isoformat(),
        )
    finally:
        await conn.close()


@router.post("", response_model=SessionResponse)
async def create_session(request: SessionCreate):
    """
    Create a new chat session.
    Returns the created session with a welcome message.
    """
    conn = await get_db_connection()
    try:
        # Default welcome message
        welcome_message = {
            "id": "1",
            "role": "assistant",
            "content": "안녕하세요! 저는 당신의 대화를 기억하는 AI 어시스턴트입니다. 무엇이든 이야기해주세요. 중요한 정보는 자동으로 기억합니다. 🧠",
            "timestamp": datetime.now().isoformat(),
        }
        
        row = await conn.fetchrow("""
            INSERT INTO chat_sessions (name, messages, mode)
            VALUES ($1, $2::jsonb, 'fast')
            RETURNING *
        """, request.name, f'[{__import__("json").dumps(welcome_message)}]')
        
        return SessionResponse(
            id=str(row["id"]),
            name=row["name"],
            messages=parse_messages(row["messages"]),
            mode=row["mode"],
            context_summary=row["context_summary"],
            summarized_count=row["summarized_count"] or 0,
            selected_message_id=row["selected_message_id"],
            created_at=row["created_at"].isoformat(),
            last_active_at=row["last_active_at"].isoformat(),
        )
    finally:
        await conn.close()


@router.put("/{session_id}", response_model=SessionResponse)
async def update_session(session_id: UUID, request: SessionUpdate):
    """
    Update a session's fields (name, messages, mode, summary, etc.).
    Only provided fields are updated.
    """
    conn = await get_db_connection()
    try:
        # Build dynamic update query
        updates = []
        values = []
        param_idx = 2  # $1 is session_id
        
        if request.name is not None:
            updates.append(f"name = ${param_idx}")
            values.append(request.name)
            param_idx += 1
        
        if request.messages is not None:
            updates.append(f"messages = ${param_idx}::jsonb")
            values.append(__import__("json").dumps(request.messages))
            param_idx += 1
        
        if request.mode is not None:
            updates.append(f"mode = ${param_idx}")
            values.append(request.mode)
            param_idx += 1
        
        if request.context_summary is not None:
            updates.append(f"context_summary = ${param_idx}")
            values.append(request.context_summary)
            param_idx += 1
        
        if request.summarized_count is not None:
            updates.append(f"summarized_count = ${param_idx}")
            values.append(request.summarized_count)
            param_idx += 1
        
        if request.selected_message_id is not None:
            updates.append(f"selected_message_id = ${param_idx}")
            values.append(request.selected_message_id)
            param_idx += 1
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Always update last_active_at
        updates.append("last_active_at = NOW()")
        
        query = f"""
            UPDATE chat_sessions 
            SET {', '.join(updates)}
            WHERE id = $1
            RETURNING *
        """
        
        row = await conn.fetchrow(query, session_id, *values)
        
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return SessionResponse(
            id=str(row["id"]),
            name=row["name"],
            messages=parse_messages(row["messages"]),
            mode=row["mode"],
            context_summary=row["context_summary"],
            summarized_count=row["summarized_count"] or 0,
            selected_message_id=row["selected_message_id"],
            created_at=row["created_at"].isoformat(),
            last_active_at=row["last_active_at"].isoformat(),
        )
    finally:
        await conn.close()


@router.delete("/{session_id}")
async def delete_session(session_id: UUID):
    """
    Delete a chat session.
    """
    conn = await get_db_connection()
    try:
        result = await conn.execute("""
            DELETE FROM chat_sessions WHERE id = $1
        """, session_id)
        
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"status": "deleted", "id": str(session_id)}
    finally:
        await conn.close()


@router.post("/{session_id}/messages", response_model=SessionResponse)
async def add_message(session_id: UUID, message: dict):
    """
    Add a single message to a session.
    More efficient than updating the entire messages array.
    """
    conn = await get_db_connection()
    try:
        row = await conn.fetchrow("""
            UPDATE chat_sessions 
            SET 
                messages = messages || $2::jsonb,
                last_active_at = NOW()
            WHERE id = $1
            RETURNING *
        """, session_id, __import__("json").dumps([message]))
        
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return SessionResponse(
            id=str(row["id"]),
            name=row["name"],
            messages=parse_messages(row["messages"]),
            mode=row["mode"],
            context_summary=row["context_summary"],
            summarized_count=row["summarized_count"] or 0,
            selected_message_id=row["selected_message_id"],
            created_at=row["created_at"].isoformat(),
            last_active_at=row["last_active_at"].isoformat(),
        )
    finally:
        await conn.close()
