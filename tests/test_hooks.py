"""
Tests for Pipeline Hook System
"""
import asyncio
import pytest
from eternal_memory.pipelines.hooks import PipelineHookManager


@pytest.mark.asyncio
async def test_hook_registration():
    """Test basic hook registration."""
    hooks = PipelineHookManager()
    
    executed = []
    
    @hooks.before("test_stage")
    async def before_hook(context):
        executed.append("before")
    
    @hooks.after("test_stage")
    async def after_hook(context):
        executed.append("after")
    
    context = {}
    await hooks.execute_before("test_stage", context)
    await hooks.execute_after("test_stage", context)
    
    assert executed == ["before", "after"]


@pytest.mark.asyncio
async def test_wildcard_hooks():
    """Test wildcard hooks execute for all stages."""
    hooks = PipelineHookManager()
    
    executed = []
    
    @hooks.before("*")
    async def wildcard_before(stage, context):
        executed.append(f"before:{stage}")
    
    @hooks.after("*")
    async def wildcard_after(stage, context):
        executed.append(f"after:{stage}")
    
    context = {}
    await hooks.execute_before("extract", context)
    await hooks.execute_after("extract", context)
    
    await hooks.execute_before("store", context)
    await hooks.execute_after("store", context)
    
    assert executed == [
        "before:extract",
        "after:extract",
        "before:store",
        "after:store",
    ]


@pytest.mark.asyncio
async def test_context_mutation():
    """Test that hooks can modify context dict."""
    hooks = PipelineHookManager()
    
    @hooks.before("process")
    async def add_data(context):
        context["added_by_hook"] = True
    
    context = {}
    await hooks.execute_before("process", context)
    
    assert context["added_by_hook"] is True


@pytest.mark.asyncio
async def test_hook_error_handling():
    """Test that hook errors don't crash pipeline."""
    hooks = PipelineHookManager()
    
    executed = []
    
    @hooks.before("test")
    async def failing_hook(context):
        raise ValueError("Hook error")
    
    @hooks.before("test")
    async def succeeding_hook(context):
        executed.append("success")
    
    context = {}
    # Should not raise despite error in first hook
    await hooks.execute_before("test", context)
    
    # Second hook should still execute
    assert "success" in executed


@pytest.mark.asyncio
async def test_performance_tracking():
    """Test performance tracking with hooks."""
    hooks = PipelineHookManager()
    
    import time
    
    @hooks.before("*")
    async def start_timer(stage, context):
        if "timers" not in context:
            context["timers"] = {}
        context["timers"][stage] = time.time()
    
    @hooks.after("*")
    async def end_timer(stage, context):
        if "timers" in context and stage in context["timers"]:
            elapsed = time.time() - context["timers"][stage]
            context[f"{stage}_duration"] = elapsed
    
    context = {}
    
    await hooks.execute_before("extract", context)
    await asyncio.sleep(0.1)  # Simulate work
    await hooks.execute_after("extract", context)
    
    assert "extract_duration" in context
    assert context["extract_duration"] >= 0.1


@pytest.mark.asyncio
async def test_hook_count():
    """Test getting hook counts."""
    hooks = PipelineHookManager()
    
    @hooks.before("extract")
    async def hook1(context):
        pass
    
    @hooks.after("extract")
    async def hook2(context):
        pass
    
    @hooks.before("*")
    async def hook3(stage, context):
        pass
    
    counts = hooks.get_hook_count()
    assert counts["total"] == 3
    
    extract_counts = hooks.get_hook_count("extract")
    assert extract_counts["before"] == 1
    assert extract_counts["after"] == 1


@pytest.mark.asyncio
async def test_clear_hooks():
    """Test clearing hooks."""
    hooks = PipelineHookManager()
    
    @hooks.before("test")
    async def hook1(context):
        pass
    
    assert hooks.get_hook_count("test")["before"] == 1
    
    hooks.clear_hooks("test")
    assert hooks.get_hook_count("test")["before"] == 0
    
    # Add more hooks
    @hooks.before("a")
    async def hook2(context):
        pass
    
    @hooks.after("b")
    async def hook3(context):
        pass
    
    hooks.clear_hooks()  # Clear all
    assert hooks.get_hook_count()["total"] == 0


if __name__ == "__main__":
    # Run tests manually
    asyncio.run(test_hook_registration())
    asyncio.run(test_wildcard_hooks())
    asyncio.run(test_context_mutation())
    asyncio.run(test_hook_error_handling())
    asyncio.run(test_performance_tracking())
    asyncio.run(test_hook_count())
    asyncio.run(test_clear_hooks())
    print("✅ All hook system tests passed!")
