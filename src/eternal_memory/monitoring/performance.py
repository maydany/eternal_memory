"""
Performance Monitoring System

Collects and logs pipeline performance metrics using hooks.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import deque
import statistics


class PerformanceMonitor:
    """
    Monitors and logs pipeline performance metrics.
    
    Features:
    - Stage-level timing
    - Embedding performance tracking
    - Cache statistics
    - JSON-formatted logs
    - In-memory recent metrics
    """
    
    def __init__(self, log_dir: str = "logs", max_recent: int = 100):
        """
        Initialize performance monitor.
        
        Args:
            log_dir: Directory for log files
            max_recent: Max number of recent metrics to keep in memory
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory metrics (for UI)
        self.recent_metrics: deque = deque(maxlen=max_recent)
        
        # Aggregated stats
        self.stats = {
            "total_pipelines": 0,
            "total_facts": 0,
            "total_embeddings": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }
        
        # Setup JSON logger
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup JSON logger for metrics."""
        self.logger = logging.getLogger("eternal_memory.metrics")
        self.logger.setLevel(logging.INFO)
        
        # Daily rotating file handler
        log_file = self.log_dir / f"metrics_{datetime.now().strftime('%Y%m%d')}.jsonl"
        handler = logging.FileHandler(log_file)
        handler.setLevel(logging.INFO)
        
        # No formatting - we'll write JSON directly
        handler.setFormatter(logging.Formatter('%(message)s'))
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()
        self.logger.addHandler(handler)
        self.logger.propagate = False
    
    async def record_pipeline_execution(self, context: Dict[str, Any]):
        """
        Record a complete pipeline execution.
        
        Called by hook after pipeline completes.
        """
        # Extract metrics from context
        stage_timers = context.get("stage_timers", {})
        extracted_facts = context.get("extracted_facts", [])
        created_items = context.get("created_items", [])
        batch_embeddings = context.get("batch_embeddings", [])
        
        # Calculate durations
        total_duration = time.time() - context.get("start_time", time.time())
        
        # Build metric record
        metric = {
            "timestamp": datetime.now().isoformat(),
            "type": "pipeline_execution",
            "total_duration": round(total_duration, 3),
            "stages": {
                stage: round(time.time() - start, 3)
                for stage, start in stage_timers.items()
            },
            "facts": {
                "extracted": len(extracted_facts),
                "stored": len(created_items),
            },
            "embeddings": {
                "count": len(batch_embeddings) if batch_embeddings else 0,
                "batched": bool(batch_embeddings),
            },
            "text_length": len(context.get("text", "")),
        }
        
        # Update stats
        self.stats["total_pipelines"] += 1
        self.stats["total_facts"] += len(created_items)
        self.stats["total_embeddings"] += metric["embeddings"]["count"]
        
        # Store in memory
        self.recent_metrics.append(metric)
        
        # Log to file
        self.logger.info(json.dumps(metric))
    
    async def record_embedding_performance(self, context: Dict[str, Any]):
        """Record embedding-specific performance metrics."""
        batch_embeddings = context.get("batch_embeddings", [])
        
        if not batch_embeddings:
            return
        
        metric = {
            "timestamp": datetime.now().isoformat(),
            "type": "embedding_batch",
            "count": len(batch_embeddings),
            "stage": "store",
        }
        
        self.logger.info(json.dumps(metric))
    
    def get_recent_metrics(self, limit: Optional[int] = None) -> List[Dict]:
        """Get recent metrics from memory."""
        metrics = list(self.recent_metrics)
        if limit:
            metrics = metrics[-limit:]
        return metrics
    
    def get_summary(self) -> Dict[str, Any]:
        """Get aggregated performance summary."""
        recent = list(self.recent_metrics)
        
        if not recent:
            return {
                "total_pipelines": self.stats["total_pipelines"],
                "total_facts": self.stats["total_facts"],
                "total_embeddings": self.stats["total_embeddings"],
                "avg_duration": 0,
                "avg_facts_per_pipeline": 0,
            }
        
        # Calculate averages from recent metrics
        durations = [m["total_duration"] for m in recent if "total_duration" in m]
        facts_per_pipeline = [m["facts"]["stored"] for m in recent if "facts" in m]
        
        return {
            "total_pipelines": self.stats["total_pipelines"],
            "total_facts": self.stats["total_facts"],
            "total_embeddings": self.stats["total_embeddings"],
            "recent_count": len(recent),
            "avg_duration": round(statistics.mean(durations), 3) if durations else 0,
            "avg_facts_per_pipeline": round(statistics.mean(facts_per_pipeline), 2) if facts_per_pipeline else 0,
            "p95_duration": round(statistics.quantiles(durations, n=20)[18], 3) if len(durations) > 10 else 0,
        }
    
    def get_log_files(self) -> List[str]:
        """Get list of available log files."""
        return sorted([
            f.name for f in self.log_dir.glob("metrics_*.jsonl")
        ], reverse=True)
    
    def read_log_file(self, filename: str, limit: Optional[int] = None) -> List[Dict]:
        """Read metrics from a log file."""
        log_file = self.log_dir / filename
        
        if not log_file.exists():
            return []
        
        metrics = []
        with open(log_file, 'r') as f:
            for line in f:
                try:
                    metrics.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
        
        if limit:
            metrics = metrics[-limit:]
        
        return metrics


# Global monitor instance
_monitor: Optional[PerformanceMonitor] = None


def get_monitor(log_dir: str = "logs") -> PerformanceMonitor:
    """Get or create global monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = PerformanceMonitor(log_dir=log_dir)
    return _monitor
