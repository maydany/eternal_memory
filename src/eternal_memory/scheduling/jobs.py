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


@register_job("profile_reflection")
async def job_profile_reflection(system: "EternalMemorySystem"):
    """
    Daily Profile Reflection Job.
    
    Analyzes recent memories (last 7 days) and updates USER.md
    with high-quality, long-term insights about the user.
    
    Following OpenClaw's philosophy:
    - Quality threshold: confidence >= 0.7, evidence >= 3
    - Runs daily (separate from consolidation)
    - Creates backup before updating USER.md
    
    This job is SEPARATE from maintenance/consolidation to follow
    Single Responsibility Principle.
    """
    logger.info("🧠 Executing Profile Reflection...")
    
    try:
        from datetime import timedelta
        
        # 1. Check if user_model is available
        if not hasattr(system, 'user_model') or system.user_model is None:
            logger.warning("UserModel not initialized, skipping profile reflection")
            return
        
        # 2. Get memories from the last 7 days
        since = datetime.datetime.now() - timedelta(days=7)
        recent_memories = await system.repository.get_memories_since(since, limit=200)
        
        if not recent_memories:
            logger.info("No recent memories found for profile reflection (last 7 days).")
            return
        
        logger.info(f"Analyzing {len(recent_memories)} memories for user insights...")
        
        # 3. Extract memory contents for LLM analysis
        memory_contents = [m.content for m in recent_memories]
        
        # 4. Ask LLM to extract LONG-TERM insights only
        insights = await _extract_insights_from_memories(system.llm, memory_contents)
        
        if not insights:
            logger.info("No high-quality long-term insights found.")
            return
        
        # 5. Batch update USER.md (creates one backup, adds all insights)
        added = await system.user_model.batch_update(insights)
        
        logger.info(f"✅ Profile Reflection complete: added {added} insights to USER.md")
        
    except Exception as e:
        logger.error(f"Profile Reflection failed: {e}")


async def _extract_insights_from_memories(llm_client, memory_contents: list) -> list:
    """
    Use LLM to extract high-quality, long-term insights from memories.
    
    Args:
        llm_client: LLMClient instance
        memory_contents: List of memory content strings
    
    Returns:
        List of insight dicts with keys: section, content, confidence, evidence_count
    """
    # Limit context to avoid token overflow
    limited_memories = memory_contents[:50]
    memories_text = "\n".join([f"- {m}" for m in limited_memories])
    
    prompt = f"""Analyze these memories from the past 7 days and extract ONLY insights 
that are valuable for LONG-TERM user understanding.

Criteria for inclusion:
- Repeated patterns (mentioned 3+ times)
- Explicit preferences stated by user
- Consistent work habits
- Technical context that's likely to remain stable

DO NOT include:
- One-time events
- Transient tasks
- Casual opinions
- Information with low confidence

Memories to analyze:
{memories_text}

Output JSON with this exact structure:
{{
  "insights": [
    {{
      "section": "Established Preferences",
      "content": "User strongly prefers TypeScript over JavaScript for type safety",
      "confidence": 0.9,
      "evidence_count": 5
    }},
    {{
      "section": "Work Patterns",
      "content": "User is most productive during late evening hours (21:00-01:00)",
      "confidence": 0.85,
      "evidence_count": 4
    }}
  ]
}}

Valid sections: "Core Identity", "Established Preferences", "Work Patterns", 
"Communication Style", "Technical Context", "Constraints"

If no high-quality long-term insights found, return: {{"insights": []}}
Be conservative - only include information you're very confident about."""
    
    try:
        response = await llm_client.complete(prompt, response_format="json_object")
        return response.get("insights", [])
    except Exception as e:
        logger.error(f"Failed to extract insights from memories: {e}")
        return []




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
        stale_items = await system.repository.get_stale_items(days_threshold=90, limit=20)
        
        if not stale_items:
            logger.info("No stale items found for embedding refresh.")
            return
        
        # Collect all items that need embedding updates
        items_to_update = []
        for item in stale_items:
            if not item.embedding or len(item.embedding) == 0:
                items_to_update.append(item)
        
        if items_to_update:
            logger.info(f"Batch updating {len(items_to_update)} item embeddings...")
            
            # Batch generate all embeddings at once
            contents = [item.content for item in items_to_update]
            new_embeddings = await system.llm.batch_generate_embeddings(contents)
            
            # Update each item with its new embedding
            for item, new_embedding in zip(items_to_update, new_embeddings):
                await system.repository.update_memory_item_embedding(item.id, new_embedding)
            
            logger.info(f"Embedding Refresh complete: processed {len(items_to_update)} items.")
        else:
            logger.info("No items found requiring embedding updates.")
        
    except Exception as e:
        logger.error(f"Embedding Refresh failed: {e}")


@register_job("lazy_triple_extraction")
async def job_lazy_triple_extraction(system: "EternalMemorySystem"):
    """
    Lazy Triple Extraction Job.
    
    Processes memory items that are pending triple extraction.
    This enables "Lazy Evaluation" - deferring expensive LLM calls for triple
    extraction until a batch job runs, instead of during memorization.
    
    Benefits:
    - Faster memorization (no blocking on triple extraction)
    - Batched LLM calls for cost efficiency
    - Configurable interval (1, 5, 10, 30 minutes)
    """
    logger.info("🔄 Executing Lazy Triple Extraction...")
    
    try:
        # Import here to avoid circular imports
        from eternal_memory.models.semantic_triple import SemanticTriple
        
        # 1. Check if semantic triples are enabled
        if not system.config.llm.use_semantic_triples:
            logger.info("Semantic triples disabled, skipping.")
            return
        
        # 2. Skip if immediate extraction is enabled (not lazy mode)
        if system.config.llm.triple_extraction_immediate:
            logger.info("Immediate extraction mode, skipping lazy job.")
            return
        
        # 3. Get pending items
        pending_items = await system.repository.get_pending_triple_items(limit=20)
        
        if not pending_items:
            logger.info("No pending items for triple extraction.")
            return
        
        logger.info(f"Processing {len(pending_items)} items for triple extraction...")
        
        extracted_count = 0
        
        for item in pending_items:
            try:
                # Extract triples from content
                triple_dicts = await system.llm.extract_triples(
                    text=item.content,
                    model_override=system.config.llm.get_memory_model(),
                )
                
                for triple_dict in triple_dicts:
                    # Create triple object
                    triple = SemanticTriple(
                        memory_item_id=item.id,
                        subject=triple_dict["subject"],
                        predicate=triple_dict["predicate"],
                        object=triple_dict["object"],
                        context=triple_dict.get("context"),
                        importance=item.importance,
                    )
                    
                    # Find conflicting triples
                    conflicts = await system.repository.find_conflicting_triples(
                        subject=triple.subject,
                        predicate=triple.predicate,
                        new_object=triple.object,
                    )
                    
                    # Supersede conflicting triples
                    for conflict in conflicts:
                        if conflict.object.lower() != triple.object.lower():
                            await system.repository.supersede_triple(
                                old_triple_id=conflict.id,
                                new_triple_id=triple.id,
                            )
                        elif triple.is_opposite_of(conflict):
                            await system.repository.supersede_triple(
                                old_triple_id=conflict.id,
                                new_triple_id=triple.id,
                            )
                    
                    # Generate object embedding
                    object_embedding = await system.llm.generate_embedding(triple.object)
                    
                    # Store the triple
                    await system.repository.create_triple(
                        triple=triple,
                        subject_embedding=None,
                        object_embedding=object_embedding,
                    )
                
                # Clear the pending flag
                await system.repository.clear_pending_triple_flag(item.id)
                extracted_count += 1
                
            except Exception as e:
                logger.error(f"Triple extraction failed for item {item.id}: {e}")
                continue
        
        logger.info(f"✅ Lazy Triple Extraction complete: processed {extracted_count}/{len(pending_items)} items")
        
    except Exception as e:
        logger.error(f"Lazy Triple Extraction job failed: {e}")


def get_job_types() -> list:
    """Get list of available job types."""
    return list(JOB_REGISTRY.keys())


def get_job_function(job_type: str):
    """Get the job function for a given job type."""
    return JOB_REGISTRY.get(job_type)
