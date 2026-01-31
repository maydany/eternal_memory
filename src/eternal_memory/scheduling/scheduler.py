"""
Cron Scheduler

A lightweight asyncio-based scheduler for background tasks.
"""

import asyncio
import logging
import time
from typing import Callable, Coroutine, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("eternal_memory.scheduling")


@dataclass
class CronJob:
    """Represents a scheduled job."""
    name: str
    interval_seconds: int
    coroutine_func: Callable[[], Coroutine]
    job_type: str = "custom"
    is_system: bool = False
    last_run: float = 0.0
    enabled: bool = True


class CronScheduler:
    """
    Manages periodic background tasks.
    """
    
    def __init__(self):
        self._jobs: Dict[str, CronJob] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
    def add_job(
        self, 
        name: str, 
        interval_seconds: int, 
        func: Callable[[], Coroutine],
        job_type: str = "custom",
        is_system: bool = False,
    ):
        """Register a new background job."""
        job = CronJob(
            name=name,
            interval_seconds=interval_seconds,
            coroutine_func=func,
            job_type=job_type,
            is_system=is_system,
            last_run=0.0,
            enabled=True,
        )
        self._jobs[name] = job
        logger.info(f"Scheduled job '{name}' (type: {job_type}) every {interval_seconds}s")
    
    def remove_job(self, name: str) -> bool:
        """Remove a job by name. Returns True if removed."""
        job = self._jobs.get(name)
        if job is None:
            return False
        if job.is_system:
            logger.warning(f"Cannot remove system job: {name}")
            return False
        del self._jobs[name]
        logger.info(f"Removed job: {name}")
        return True
    
    def get_jobs(self) -> List[dict]:
        """Get information about all registered jobs."""
        now = time.time()
        result = []
        for name, job in self._jobs.items():
            next_run = None
            if job.last_run > 0:
                next_run = job.last_run + job.interval_seconds - now
                if next_run < 0:
                    next_run = 0  # Due now
            
            result.append({
                "name": job.name,
                "job_type": job.job_type,
                "interval_seconds": job.interval_seconds,
                "is_system": job.is_system,
                "enabled": job.enabled,
                "last_run": job.last_run if job.last_run > 0 else None,
                "next_run_in": next_run,
                "running": self._running,
            })
        return result
    
    def get_job(self, name: str) -> Optional[dict]:
        """Get information about a specific job."""
        job = self._jobs.get(name)
        if job is None:
            return None
        
        now = time.time()
        next_run = None
        if job.last_run > 0:
            next_run = job.last_run + job.interval_seconds - now
            if next_run < 0:
                next_run = 0
        
        return {
            "name": job.name,
            "job_type": job.job_type,
            "interval_seconds": job.interval_seconds,
            "is_system": job.is_system,
            "enabled": job.enabled,
            "last_run": job.last_run if job.last_run > 0 else None,
            "next_run_in": next_run,
            "running": self._running,
        }
    
    async def trigger_job(self, name: str) -> bool:
        """Manually trigger a job immediately. Returns True if executed."""
        job = self._jobs.get(name)
        if job is None:
            logger.warning(f"Cannot trigger unknown job: {name}")
            return False
        
        if not job.enabled:
            logger.warning(f"Cannot trigger disabled job: {name}")
            return False
        
        try:
            logger.info(f"Manually triggering job: {name}")
            await job.coroutine_func()
            job.last_run = time.time()
            logger.info(f"Manual trigger complete: {name}")
            return True
        except Exception as e:
            logger.error(f"Manual trigger failed for '{name}': {str(e)}")
            return False
    
    def enable_job(self, name: str) -> bool:
        """Enable a job."""
        job = self._jobs.get(name)
        if job:
            job.enabled = True
            return True
        return False
    
    def disable_job(self, name: str) -> bool:
        """Disable a job."""
        job = self._jobs.get(name)
        if job:
            job.enabled = False
            return True
        return False
        
    async def start(self):
        """Start the scheduler loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("CronScheduler started")
        
    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("CronScheduler stopped")
            
    async def _loop(self):
        """Main scheduling loop."""
        while self._running:
            now = time.time()
            for name, job in self._jobs.items():
                if not job.enabled:
                    continue
                    
                # Check if due
                if now - job.last_run >= job.interval_seconds:
                    try:
                        logger.info(f"Running job: {name}")
                        await job.coroutine_func()
                        # Update last run
                        job.last_run = time.time()
                        logger.info(f"Job finished: {name}")
                    except Exception as e:
                        logger.error(f"Job '{name}' failed: {str(e)}")
            
            # Check every second
            await asyncio.sleep(1)
