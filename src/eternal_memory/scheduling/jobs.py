"""
Standard Cron Jobs

Defines the background tasks for the eternal memory system.
"""

import datetime
from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from eternal_memory.engine.memory_engine import EternalMemorySystem

logger = logging.getLogger("eternal_memory.jobs")

async def job_daily_reflection(system: "EternalMemorySystem"):
    """
    Daily Reflection Job.
    
    Summarizes the day's memories and creates a 'Daily Reflection' entry.
    """
    logger.info("Executing Daily Reflection...")
    
    # 1. Retrieve memories from the last 24 hours (Mock logic for now, as retrieval by date isn't extensive yet)
    # Ideally we'd query the DB for items created > now - 24h
    # For this MVP, we'll ask the LLM to reflect on "Recent events" using the deep retrieval mode.
    
    try:
        # Ask system to retrieve recent context
        query = "What happened today? Recent events and important facts."
        result = await system.retrieve(query, mode="fast")
        
        if not result.items:
            logger.info("No recent memories to reflect on.")
            return

        context = "\n".join([f"- {item.content}" for item in result.items])
        
        # 2. Generate Reflection (using direct LLM call via Memorize pipeline logic or similar)
        # We'll use a direct memorize call with a special prefix "Daily Reflection:"
        
        reflection_prompt = f"""Based on these recent memories, write a brief 'Daily Reflection' summary.
Focus on key insights about the user.

Memories:
{context}

Summary:"""
        
        # We can reuse the predict logic or just store it. 
        # For simplicity, we'll just store a specialized memory.
        now = datetime.datetime.now().strftime("%Y-%m-%d")
        summary = f"Daily Reflection ({now}): Processed {len(result.items)} items."
        
        # In a real implementation we would call LLM here. 
        # For MVP speed, we store the metadata.
        
        await system.memorize(summary, {"date": now, "type": "daily_reflection"})
        logger.info(f"Daily Reflection stored: {summary}")
        
    except Exception as e:
        logger.error(f"Daily Reflection failed: {e}")

async def job_maintenance(system: "EternalMemorySystem"):
    """
    Periodic Maintenance Job.
    Runs consolidation pipeline.
    """
    logger.info("Executing Maintenance/Consolidation...")
    try:
        await system.consolidate()
        logger.info("Maintenance complete.")
    except Exception as e:
        logger.error(f"Maintenance failed: {e}")
