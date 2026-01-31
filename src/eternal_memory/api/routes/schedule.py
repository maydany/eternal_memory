"""
Schedule API Routes

Endpoints for managing scheduled tasks.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

router = APIRouter()


class ScheduledTaskCreate(BaseModel):
    """Request model for creating a scheduled task."""
    name: str
    job_type: str
    interval_seconds: int


class ScheduledTaskResponse(BaseModel):
    """Response model for a scheduled task."""
    id: str = None
    name: str
    job_type: str
    interval_seconds: int
    enabled: bool
    is_system: bool
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    next_run_in: Optional[float] = None
    running: bool = False
    created_at: Optional[str] = None


# Dependency to get the memory system
async def get_memory_system():
    from eternal_memory.api.main import get_system
    return get_system()


@router.get("/jobs", response_model=List[ScheduledTaskResponse])
async def list_scheduled_jobs(system=Depends(get_memory_system)):
    """
    List all scheduled jobs.
    
    Returns both in-memory scheduler jobs and database tasks, merged together.
    """
    # Get in-memory jobs from scheduler
    scheduler_jobs = system.scheduler.get_jobs()
    
    # Get database tasks
    db_tasks = await system.repository.get_scheduled_tasks()
    
    # Create a merged result (scheduler data takes precedence for runtime info)
    result = []
    seen_names = set()
    
    for job in scheduler_jobs:
        seen_names.add(job["name"])
        result.append(ScheduledTaskResponse(
            name=job["name"],
            job_type=job["job_type"],
            interval_seconds=job["interval_seconds"],
            enabled=job["enabled"],
            is_system=job["is_system"],
            next_run_in=job.get("next_run_in"),
            running=job.get("running", False),
        ))
    
    # Add any DB tasks not in scheduler (shouldn't happen normally)
    for task in db_tasks:
        if task["name"] not in seen_names:
            result.append(ScheduledTaskResponse(
                id=task["id"],
                name=task["name"],
                job_type=task["job_type"],
                interval_seconds=task["interval_seconds"],
                enabled=task["enabled"],
                is_system=task["is_system"],
                last_run=task.get("last_run"),
                next_run=task.get("next_run"),
                created_at=task.get("created_at"),
            ))
    
    return result


@router.get("/jobs/{name}", response_model=ScheduledTaskResponse)
async def get_scheduled_job(name: str, system=Depends(get_memory_system)):
    """
    Get details about a specific scheduled job.
    """
    # Try scheduler first
    job = system.scheduler.get_job(name)
    if job:
        return ScheduledTaskResponse(
            name=job["name"],
            job_type=job["job_type"],
            interval_seconds=job["interval_seconds"],
            enabled=job["enabled"],
            is_system=job["is_system"],
            next_run_in=job.get("next_run_in"),
            running=job.get("running", False),
        )
    
    # Fall back to database
    task = await system.repository.get_scheduled_task(name)
    if task:
        return ScheduledTaskResponse(
            id=task["id"],
            name=task["name"],
            job_type=task["job_type"],
            interval_seconds=task["interval_seconds"],
            enabled=task["enabled"],
            is_system=task["is_system"],
            last_run=task.get("last_run"),
            next_run=task.get("next_run"),
            created_at=task.get("created_at"),
        )
    
    raise HTTPException(status_code=404, detail=f"Job not found: {name}")


@router.post("/jobs", response_model=ScheduledTaskResponse)
async def create_scheduled_job(task: ScheduledTaskCreate, system=Depends(get_memory_system)):
    """
    Create a new scheduled job.
    
    The job will be saved to the database and registered with the scheduler.
    """
    from eternal_memory.scheduling.jobs import get_job_function, get_job_types
    
    # Validate job type
    available_types = get_job_types()
    if task.job_type not in available_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid job_type: {task.job_type}. Available types: {available_types}"
        )
    
    # Validate interval
    if task.interval_seconds < 60:
        raise HTTPException(
            status_code=400,
            detail="Interval must be at least 60 seconds"
        )
    
    # Check if job already exists
    existing = await system.repository.get_scheduled_task(task.name)
    if existing:
        raise HTTPException(status_code=409, detail=f"Job already exists: {task.name}")
    
    # Save to database
    saved_task = await system.repository.save_scheduled_task(
        name=task.name,
        job_type=task.job_type,
        interval_seconds=task.interval_seconds,
        enabled=True,
        is_system=False,
    )
    
    # Register with scheduler
    job_func = get_job_function(task.job_type)
    if job_func:
        system.scheduler.add_job(
            name=task.name,
            interval_seconds=task.interval_seconds,
            func=lambda f=job_func: f(system),
            job_type=task.job_type,
            is_system=False,
        )
    
    return ScheduledTaskResponse(
        id=saved_task["id"],
        name=saved_task["name"],
        job_type=saved_task["job_type"],
        interval_seconds=saved_task["interval_seconds"],
        enabled=saved_task["enabled"],
        is_system=saved_task["is_system"],
        created_at=saved_task.get("created_at"),
    )


@router.delete("/jobs/{name}")
async def delete_scheduled_job(name: str, system=Depends(get_memory_system)):
    """
    Delete a scheduled job.
    
    System jobs cannot be deleted.
    """
    # Check if it's a system job
    task = await system.repository.get_scheduled_task(name)
    if task and task["is_system"]:
        raise HTTPException(status_code=403, detail="Cannot delete system job")
    
    # Remove from scheduler
    removed_from_scheduler = system.scheduler.remove_job(name)
    
    # Remove from database
    removed_from_db = await system.repository.delete_scheduled_task(name)
    
    if not removed_from_scheduler and not removed_from_db:
        raise HTTPException(status_code=404, detail=f"Job not found: {name}")
    
    return {"success": True, "message": f"Job deleted: {name}"}


@router.post("/jobs/{name}/trigger")
async def trigger_scheduled_job(name: str, system=Depends(get_memory_system)):
    """
    Manually trigger a job to run immediately.
    """
    success = await system.scheduler.trigger_job(name)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Job not found or disabled: {name}")
    
    # Update last_run in database
    await system.repository.update_task_last_run(name)
    
    return {"success": True, "message": f"Job triggered: {name}"}


@router.get("/job-types")
async def list_job_types():
    """
    List available job types that can be scheduled.
    """
    from eternal_memory.scheduling.jobs import get_job_types, JOB_REGISTRY
    
    types = []
    for job_type in get_job_types():
        func = JOB_REGISTRY.get(job_type)
        doc = func.__doc__.strip().split('\n')[0] if func and func.__doc__ else ""
        types.append({
            "type": job_type,
            "description": doc,
        })
    
    return {"job_types": types}
