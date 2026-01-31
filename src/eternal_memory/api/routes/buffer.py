"""
Buffer API Routes

Endpoints for managing the conversation buffer.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException

from eternal_memory.api.main import get_memory_system

router = APIRouter()


@router.get("/status")
async def get_buffer_status():
    """
    Get current buffer status.
    
    Returns:
        - message_count: Number of messages in buffer
        - estimated_tokens: Estimated token count
        - threshold_tokens: Flush threshold
        - fill_percentage: How full the buffer is (0-100)
        - auto_flush_enabled: Whether auto-flush is enabled
    """
    try:
        system = await get_memory_system()
        buffer = system.conversation_buffer
        threshold = system.FLUSH_THRESHOLD_TOKENS
        
        # Estimate tokens (same logic as in check_and_flush)
        total_chars = sum(len(m.get("content", "")) for m in buffer)
        estimated_tokens = int(total_chars / 2)
        
        fill_percentage = min(100, int((estimated_tokens / threshold) * 100)) if threshold > 0 else 0
        
        return {
            "message_count": len(buffer),
            "estimated_tokens": estimated_tokens,
            "threshold_tokens": threshold,
            "fill_percentage": fill_percentage,
            "auto_flush_enabled": True,  # Currently always enabled
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages")
async def get_buffer_messages(limit: Optional[int] = 20):
    """
    Get messages currently in the buffer.
    
    Args:
        limit: Maximum number of messages to return (most recent first)
    """
    try:
        system = await get_memory_system()
        buffer = system.conversation_buffer
        
        # Return most recent messages first
        messages = list(reversed(buffer[-limit:] if limit else buffer))
        
        return {
            "messages": messages,
            "total": len(buffer),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/flush")
async def flush_buffer():
    """
    Manually trigger buffer flush.
    
    This processes all buffered messages and stores extracted
    facts in permanent memory.
    """
    try:
        system = await get_memory_system()
        
        message_count = len(system.conversation_buffer)
        if message_count == 0:
            return {
                "success": True,
                "message": "Buffer was already empty",
                "items_created": 0,
            }
        
        items = await system.flush_buffer()
        
        return {
            "success": True,
            "message": f"Flushed {message_count} messages",
            "items_created": len(items),
            "items": [
                {
                    "id": str(item.id),
                    "content": item.content,
                    "category_path": item.category_path,
                }
                for item in items
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
