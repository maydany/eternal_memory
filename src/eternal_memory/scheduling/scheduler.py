"""
Cron Scheduler

A lightweight asyncio-based scheduler for background tasks.
"""

import asyncio
import logging
import time
from typing import Callable, Coroutine, List, NamedTuple, Optional

logger = logging.getLogger("eternal_memory.scheduling")

class CronJob(NamedTuple):
    name: str
    interval_seconds: int
    coroutine_func: Callable[[], Coroutine]
    last_run: float = 0.0

class CronScheduler:
    """
    Manages periodic background tasks.
    """
    
    def __init__(self):
        self._jobs: List[CronJob] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
    def add_job(self, name: str, interval_seconds: int, func: Callable[[], Coroutine]):
        """Register a new background job."""
        job = CronJob(name, interval_seconds, func, 0.0)
        self._jobs.append(job)
        logger.info(f"Scheduled job '{name}' every {interval_seconds}s")
        
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
            for i, job in enumerate(self._jobs):
                # Check if due
                if now - job.last_run >= job.interval_seconds:
                    try:
                        logger.info(f"Running job: {job.name}")
                        await job.coroutine_func()
                        # Update last run
                        self._jobs[i] = job._replace(last_run=time.time())
                        logger.info(f"Job finished: {job.name}")
                    except Exception as e:
                        logger.error(f"Job '{job.name}' failed: {str(e)}")
            
            # Check every second
            await asyncio.sleep(1)
