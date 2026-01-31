"""
Standard Cron Jobs

Defines the background tasks for the eternal memory system.
"""

import datetime
import shutil
from pathlib import Path
from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from eternal_memory.engine.memory_engine import EternalMemorySystem

logger = logging.getLogger("eternal_memory.jobs")


# ========== Job Registry ==========
# Maps job_type strings to coroutine factory functions

JOB_REGISTRY = {}


def register_job(name: str):
    """Decorator to register a job function."""
    def decorator(func):
        JOB_REGISTRY[name] = func
        return func
    return decorator


@register_job("daily_reflection")
async def job_daily_reflection(system: "EternalMemorySystem"):
    """
    Daily Reflection Job.
    
    Summarizes the day's memories and creates a structured 'Daily Reflection' entry.
    Uses LLM to generate insights, key events, and sentiment analysis.
    """
    logger.info("Executing Daily Reflection...")
    
    try:
        # 1. Get memories from the last 24 hours
        from datetime import timedelta
        since = datetime.datetime.now() - timedelta(hours=24)
        recent_memories = await system.repository.get_memories_since(since, limit=100)
        
        if not recent_memories:
            logger.info("No recent memories to reflect on (last 24 hours).")
            return
        
        # 2. Prepare memory contents for LLM
        memory_contents = [item.content for item in recent_memories]
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # 3. Generate structured reflection using LLM
        reflection = await system.llm.generate_daily_reflection(
            memory_items=memory_contents,
            date_str=today_str,
        )
        
        # 4. Format the reflection for storage
        key_events_str = ", ".join(reflection["key_events"]) if reflection["key_events"] else "None"
        
        reflection_content = (
            f"[Daily Reflection - {today_str}]\n"
            f"Summary: {reflection['summary']}\n"
            f"Key Events: {key_events_str}\n"
            f"Sentiment: {reflection['sentiment']}\n"
            f"Insights: {reflection['insights']}\n"
            f"(Based on {len(recent_memories)} memories)"
        )
        
        # 5. Store as a memory item in timeline/daily_reflection category
        await system.memorize(
            reflection_content,
            {
                "date": today_str,
                "type": "daily_reflection",
                "memory_count": len(recent_memories),
                "sentiment": reflection["sentiment"],
            }
        )
        
        logger.info(f"Daily Reflection stored: {reflection['summary'][:100]}...")
        
    except Exception as e:
        logger.error(f"Daily Reflection failed: {e}")


@register_job("maintenance")
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


@register_job("vault_backup")
async def job_vault_backup(system: "EternalMemorySystem"):
    """
    Vault Backup Job.
    Creates a dated backup of the markdown vault.
    """
    logger.info("Executing Vault Backup...")
    try:
        vault_path = Path(system.vault.root_path)
        if not vault_path.exists():
            logger.warning("Vault path does not exist, skipping backup.")
            return
            
        backup_dir = vault_path.parent / "vault_backups"
        backup_dir.mkdir(exist_ok=True)
        
        now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"vault_backup_{now}"
        
        shutil.copytree(vault_path, backup_path, dirs_exist_ok=True)
        logger.info(f"Vault backed up to: {backup_path}")
        
    except Exception as e:
        logger.error(f"Vault Backup failed: {e}")


@register_job("weekly_summary")
async def job_weekly_summary(system: "EternalMemorySystem"):
    """
    Weekly Summary Job.
    
    Aggregates the past 7 days of Daily Reflections into a weekly summary.
    """
    logger.info("Executing Weekly Summary...")
    
    try:
        from datetime import timedelta
        
        # 1. Get daily reflections from the past 7 days
        since = datetime.datetime.now() - timedelta(days=7)
        daily_reflections = await system.repository.get_reflections_by_type(
            reflection_type="timeline/daily",
            since=since,
            limit=7,
        )
        
        if not daily_reflections:
            logger.info("No daily reflections found for weekly summary (last 7 days).")
            return
        
        # 2. Extract content
        reflection_contents = [item.content for item in daily_reflections]
        
        # 3. Calculate week identifier (ISO week)
        now = datetime.datetime.now()
        week_str = now.strftime("%Y-W%W")
        
        # 4. Generate summary using LLM
        summary = await system.llm.generate_weekly_summary(
            daily_reflections=reflection_contents,
            week_str=week_str,
        )
        
        # 5. Format and store
        themes_str = ", ".join(summary["themes"]) if summary["themes"] else "None"
        achievements_str = ", ".join(summary["achievements"]) if summary["achievements"] else "None"
        
        summary_content = (
            f"[Weekly Summary - {week_str}]\n"
            f"Summary: {summary['summary']}\n"
            f"Themes: {themes_str}\n"
            f"Patterns: {summary['patterns']}\n"
            f"Achievements: {achievements_str}\n"
            f"Advice: {summary['advice']}\n"
            f"(Based on {len(daily_reflections)} daily reflections)"
        )
        
        await system.memorize(
            summary_content,
            {
                "week": week_str,
                "type": "weekly_summary",
                "reflection_count": len(daily_reflections),
            }
        )
        
        logger.info(f"Weekly Summary stored: {summary['summary'][:100]}...")
        
    except Exception as e:
        logger.error(f"Weekly Summary failed: {e}")


@register_job("monthly_summary")
async def job_monthly_summary(system: "EternalMemorySystem"):
    """
    Monthly Summary Job.
    
    Aggregates the past 4-5 weeks of Weekly Summaries into a monthly summary.
    """
    logger.info("Executing Monthly Summary...")
    
    try:
        from datetime import timedelta
        
        # 1. Get weekly summaries from the past ~30 days
        since = datetime.datetime.now() - timedelta(days=35)
        weekly_summaries = await system.repository.get_reflections_by_type(
            reflection_type="timeline/weekly",
            since=since,
            limit=5,
        )
        
        if not weekly_summaries:
            logger.info("No weekly summaries found for monthly summary (last ~30 days).")
            return
        
        # 2. Extract content
        summary_contents = [item.content for item in weekly_summaries]
        
        # 3. Calculate month identifier
        now = datetime.datetime.now()
        month_str = now.strftime("%Y-%m")
        
        # 4. Generate summary using LLM
        summary = await system.llm.generate_monthly_summary(
            weekly_summaries=summary_contents,
            month_str=month_str,
        )
        
        # 5. Format and store
        keywords_str = ", ".join(summary["keywords"]) if summary["keywords"] else "None"
        goals_str = ", ".join(summary["goals"]) if summary["goals"] else "None"
        
        summary_content = (
            f"[Monthly Summary - {month_str}]\n"
            f"Summary: {summary['summary']}\n"
            f"Keywords: {keywords_str}\n"
            f"Trends: {summary['trends']}\n"
            f"Growth: {summary['growth']}\n"
            f"Goals: {goals_str}\n"
            f"(Based on {len(weekly_summaries)} weekly summaries)"
        )
        
        await system.memorize(
            summary_content,
            {
                "month": month_str,
                "type": "monthly_summary",
                "summary_count": len(weekly_summaries),
            }
        )
        
        logger.info(f"Monthly Summary stored: {summary['summary'][:100]}...")
        
    except Exception as e:
        logger.error(f"Monthly Summary failed: {e}")


# Memory cleanup removed to align with "Eternal Memory" philosophy.
# We do not delete memories, only consolidate/archive them via maintenance.


@register_job("stats_snapshot")
async def job_stats_snapshot(system: "EternalMemorySystem"):
    """
    Stats Snapshot Job.
    Logs system statistics periodically.
    """
    logger.info("Executing Stats Snapshot...")
    try:
        stats = await system.get_stats()
        
        log_entry = (
            f"[Stats Snapshot] "
            f"Resources: {stats.get('resources', 0)}, "
            f"Categories: {stats.get('categories', 0)}, "
            f"Memories: {stats.get('memory_items', 0)}, "
            f"DB Size: {stats.get('db_size', 'N/A')}"
        )
        
        logger.info(log_entry)
        
        # Optionally save to a stats file
        stats_file = Path.home() / ".openclaw" / "stats_log.txt"
        stats_file.parent.mkdir(parents=True, exist_ok=True)
        
        now = datetime.datetime.now().isoformat()
        with open(stats_file, "a") as f:
            f.write(f"{now}: {log_entry}\n")
        
    except Exception as e:
        logger.error(f"Stats Snapshot failed: {e}")


@register_job("embedding_refresh")
async def job_embedding_refresh(system: "EternalMemorySystem"):
    """
    Embedding Refresh Job.
    Re-generates embeddings for old items to use latest embedding model.
    """
    logger.info("Executing Embedding Refresh...")
    try:
        # Get oldest items (by created_at) that might have outdated embeddings
        # This is a placeholder - in production, you'd track embedding model versions
        old_items = await system.repository.get_stale_items(days_threshold=90, limit=20)
        
        refreshed_count = 0
        for item in old_items:
            # Re-generate embedding
            new_embedding = await system.llm.generate_embedding(item.content)
            
            # Update in database (would need a new method in repository)
            # For now, just log
            logger.debug(f"Would refresh embedding for item: {item.id}")
            refreshed_count += 1
        
        logger.info(f"Embedding Refresh complete: processed {refreshed_count} items.")
        
    except Exception as e:
        logger.error(f"Embedding Refresh failed: {e}")


def get_job_types() -> list:
    """Get list of available job types."""
    return list(JOB_REGISTRY.keys())


def get_job_function(job_type: str):
    """Get the job function for a given job type."""
    return JOB_REGISTRY.get(job_type)
