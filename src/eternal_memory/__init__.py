"""
Eternal Memory System

OpenClaw-style eternal memory implementation with hierarchical storage,
hybrid retrieval, and proactive context prediction.
"""

from eternal_memory.engine.memory_engine import EternalMemorySystem
from eternal_memory.models.memory_item import MemoryItem
from eternal_memory.models.retrieval import RetrievalResult

__version__ = "0.1.0"
__all__ = ["EternalMemorySystem", "MemoryItem", "RetrievalResult"]
