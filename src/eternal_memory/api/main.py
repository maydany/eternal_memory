"""
Eternal Memory API Server

FastAPI application that exposes the Eternal Memory System
through REST API endpoints.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from eternal_memory.config import load_config
from eternal_memory.engine.memory_engine import EternalMemorySystem


# Load .env file at startup
def load_env_file():
    """Load environment variables from ~/.openclaw/.env if it exists."""
    env_path = Path.cwd() / "setting" / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


load_env_file()


# Global memory system instance (lazy initialized)
memory_system: Optional[EternalMemorySystem] = None
_initialization_attempted = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler - doesn't require initialization at startup."""
    # We'll initialize lazily when first request comes in
    yield
    
    # Cleanup on shutdown
    global memory_system
    if memory_system:
        await memory_system.close()
        memory_system = None


app = FastAPI(
    title="Eternal Memory API",
    description="API for the OpenClaw Eternal Memory System",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_memory_system() -> EternalMemorySystem:
    """Get the global memory system instance, initializing if needed."""
    global memory_system, _initialization_attempted
    
    if memory_system is not None:
        return memory_system
    
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="API key not configured. Please set OPENAI_API_KEY or configure via Settings."
        )
    
    if not _initialization_attempted:
        _initialization_attempted = True
        try:
            config = load_config()
            memory_system = EternalMemorySystem(config)
            await memory_system.initialize()
        except Exception as e:
            _initialization_attempted = False
            raise HTTPException(status_code=500, detail=f"Failed to initialize memory system: {e}")
    
    if memory_system is None:
        raise HTTPException(status_code=503, detail="Memory system not initialized")
    
    return memory_system


# Import and include routers
from eternal_memory.api.routes import chat, vault, settings, database, schedule, timeline, metrics, buffer, triples


def get_system() -> EternalMemorySystem:
    """Get the global memory system instance for dependency injection."""
    if memory_system is None:
        raise HTTPException(status_code=503, detail="Memory system not initialized")
    return memory_system

app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(vault.router, prefix="/api/vault", tags=["Vault"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])
app.include_router(database.router, prefix="/api/database", tags=["Database"])
app.include_router(schedule.router, prefix="/api/schedule", tags=["Schedule"])
app.include_router(timeline.router, prefix="/api/timeline", tags=["Timeline"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["Metrics"])
app.include_router(buffer.router, prefix="/api/buffer", tags=["Buffer"])
app.include_router(triples.router, tags=["Triples"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Eternal Memory API"}


@app.get("/api/stats")
async def get_stats():
    """Get memory system statistics."""
    try:
        system = await get_memory_system()
        return await system.get_stats()
    except HTTPException:
        # Return empty stats if not initialized
        return {"resources": 0, "categories": 0, "memory_items": 0, "initialized": False}

