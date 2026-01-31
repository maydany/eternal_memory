"""
Pipeline Hook System

Provides before/after hook support for pipeline stages,
enabling observability, logging, and custom logic injection.
"""

import logging
from typing import Callable, Dict, List, Any, Optional
import asyncio

logger = logging.getLogger("eternal_memory.hooks")


class PipelineHookManager:
    """
    Manages hooks (callbacks) for pipeline stages.
    
    Hooks can be registered to run before or after specific pipeline stages,
    enabling custom logic injection without modifying core pipeline code.
    
    Features:
    - Before/After hooks for any stage
    - Wildcard support ("*") for all stages
    - Async hook execution
    - Context passing between hooks and pipeline
    
    Example:
        >>> hooks = PipelineHookManager()
        >>> 
        >>> @hooks.before("extract")
        >>> async def log_extraction(context):
        >>>     print(f"Extracting from: {context['text'][:50]}")
        >>> 
        >>> await hooks.execute_before("extract", {"text": "..."})
    """
    
    def __init__(self):
        self.before_hooks: Dict[str, List[Callable]] = {}
        self.after_hooks: Dict[str, List[Callable]] = {}
    
    def register_before(self, stage: str, hook: Callable) -> None:
        """
        Register a hook to run before a pipeline stage.
        
        Args:
            stage: Stage name (e.g., "extract", "store") or "*" for all stages
            hook: Async callable that accepts context dict
        """
        if stage not in self.before_hooks:
            self.before_hooks[stage] = []
        self.before_hooks[stage].append(hook)
        logger.debug(f"Registered before hook for stage: {stage}")
    
    def register_after(self, stage: str, hook: Callable) -> None:
        """
        Register a hook to run after a pipeline stage.
        
        Args:
            stage: Stage name (e.g., "extract", "store") or "*" for all stages
            hook: Async callable that accepts context dict
        """
        if stage not in self.after_hooks:
            self.after_hooks[stage] = []
        self.after_hooks[stage].append(hook)
        logger.debug(f"Registered after hook for stage: {stage}")
    
    def before(self, stage: str):
        """
        Decorator for registering before hooks.
        
        Example:
            >>> @hooks.before("extract")
            >>> async def my_hook(context):
            >>>     print("Before extraction!")
        """
        def decorator(func: Callable) -> Callable:
            self.register_before(stage, func)
            return func
        return decorator
    
    def after(self, stage: str):
        """
        Decorator for registering after hooks.
        
        Example:
            >>> @hooks.after("store")
            >>> async def my_hook(context):
            >>>     print(f"Stored {len(context['items'])} items")
        """
        def decorator(func: Callable) -> Callable:
            self.register_after(stage, func)
            return func
        return decorator
    
    async def execute_before(self, stage: str, context: Dict[str, Any]) -> None:
        """
        Execute all before hooks for a stage.
        
        Runs hooks in registration order. Wildcard hooks ("*") run first.
        
        Args:
            stage: Current pipeline stage
            context: Mutable context dict shared across hooks and pipeline
        """
        # Execute wildcard hooks first
        for hook in self.before_hooks.get("*", []):
            try:
                await hook(stage, context)
            except Exception as e:
                logger.error(f"Before hook failed for stage '{stage}': {e}", exc_info=True)
        
        # Execute stage-specific hooks
        for hook in self.before_hooks.get(stage, []):
            try:
                await hook(context)
            except Exception as e:
                logger.error(f"Before hook failed for stage '{stage}': {e}", exc_info=True)
    
    async def execute_after(self, stage: str, context: Dict[str, Any]) -> None:
        """
        Execute all after hooks for a stage.
        
        Runs hooks in registration order. Stage-specific hooks run before wildcards.
        
        Args:
            stage: Current pipeline stage
            context: Mutable context dict shared across hooks and pipeline
        """
        # Execute stage-specific hooks first
        for hook in self.after_hooks.get(stage, []):
            try:
                await hook(context)
            except Exception as e:
                logger.error(f"After hook failed for stage '{stage}': {e}", exc_info=True)
        
        # Execute wildcard hooks last
        for hook in self.after_hooks.get("*", []):
            try:
                await hook(stage, context)
            except Exception as e:
                logger.error(f"After hook failed for stage '{stage}': {e}", exc_info=True)
    
    def clear_hooks(self, stage: Optional[str] = None) -> None:
        """
        Clear hooks for a specific stage or all hooks.
        
        Args:
            stage: Stage to clear, or None to clear all hooks
        """
        if stage:
            self.before_hooks.pop(stage, None)
            self.after_hooks.pop(stage, None)
        else:
            self.before_hooks.clear()
            self.after_hooks.clear()
    
    def get_hook_count(self, stage: Optional[str] = None) -> Dict[str, int]:
        """Get count of registered hooks."""
        if stage:
            return {
                "before": len(self.before_hooks.get(stage, [])),
                "after": len(self.after_hooks.get(stage, [])),
            }
        else:
            total_before = sum(len(hooks) for hooks in self.before_hooks.values())
            total_after = sum(len(hooks) for hooks in self.after_hooks.values())
            return {
                "before": total_before,
                "after": total_after,
                "total": total_before + total_after,
            }
