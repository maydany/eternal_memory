#!/usr/bin/env python3
"""
Buffer Persistence Test Script

Tests the buffer persistence system:
1. Buffer file storage
2. Buffer search integration  
3. Crash recovery simulation
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eternal_memory import EternalMemorySystem


async def test_buffer_persistence():
    """Test buffer file persistence."""
    print("\n🧪 Test 1: Buffer File Persistence")
    print("=" * 60)
    
    system = EternalMemorySystem()
    await system.initialize()
    
    # Add messages to buffer
    await system.add_to_buffer("user", "나는 사과를 좋아해")
    await system.add_to_buffer("assistant", "좋습니다! 사과 취향을 기억하겠습니다.")
    
    # Check buffer file exists
    if system.buffer_file.exists():
        print("✅ Buffer file created:")
        print(f"   {system.buffer_file}")
        
        # Read file content
        content = system.buffer_file.read_text()
        print(f"\n📄 Buffer file content:")
        for i, line in enumerate(content.strip().split('\n'), 1):
            print(f"   Line {i}: {line[:80]}...")
    else:
        print("❌ Buffer file NOT created")
        return False
    
    await system.close()
    return True


async def test_buffer_search():
    """Test buffer search integration."""
    print("\n\n🧪 Test 2: Buffer Search Integration")
    print("=" * 60)
    
    system = EternalMemorySystem()
    await system.initialize()
    
    # Add conversation to buffer (not yet flushed to DB)
    await system.add_to_buffer("user", "나는 사과를 좋아해")
    await system.add_to_buffer("assistant", "좋습니다! 사과를 기억하겠습니다.")
    
    print(f"📦 Buffer contains {len(system.conversation_buffer)} messages (not in DB yet)")
    
    # Try to retrieve - should find in buffer
    result = await system.retrieve("무슨 과일을 좋아한다고?", mode="fast")
    
    print(f"\n🔍 Search Query: '무슨 과일을 좋아한다고?'")
    print(f"   Found {len(result.items)} items in DB")
    
    if "사과" in result.suggested_context:
        print("✅ Buffer search working! Found '사과' in suggested context:")
        print(f"   {result.suggested_context[:200]}...")
    else:
        print("❌ Buffer search NOT working - '사과' not found in context")
        print(f"   Context: {result.suggested_context}")
        return False
    
    await system.close()
    return True


async def test_crash_recovery():
    """Test crash recovery by simulating unexpected shutdown."""
    print("\n\n🧪 Test 3: Crash Recovery Simulation")
    print("=" * 60)
    
    # Step 1: Create system and add messages WITHOUT closing gracefully
    print("📝 Step 1: Adding messages and simulating crash...")
    system1 = EternalMemorySystem()
    await system1.initialize()
    
    await system1.add_to_buffer("user", "테스트 메시지 1")
    await system1.add_to_buffer("assistant", "응답 1")
    
    buffer_file = system1.buffer_file
    
    print(f"   Buffer file exists: {buffer_file.exists()}")
    print(f"   Buffer has {len(system1.conversation_buffer)} messages")
    
    # Simulate crash - don't call close()
    await system1.repository.disconnect()
    del system1
    
    print("💥 Simulated crash (did not call close)")
    
    # Step 2: Start new system - should restore buffer
    print("\n🔄 Step 2: Restarting system...")
    
    if buffer_file.exists():
        print(f"✅ Buffer file still exists (survived crash)")
    else:
        print(f"❌ Buffer file missing after crash")
        return False
    
    system2 = EternalMemorySystem()
    await system2.initialize()
    
    # Buffer should be empty (auto-flushed on restore)
    if len(system2.conversation_buffer) == 0:
        print(f"✅ Buffer auto-flushed on restore")
    else:
        print(f"⚠️  Buffer still has {len(system2.conversation_buffer)} messages")
    
    # Buffer file should be deleted after flush
    if not buffer_file.exists():
        print(f"✅ Buffer file cleaned up after auto-flush")
    else:
        print(f"⚠️  Buffer file still exists: {buffer_file}")
    
    await system2.close()
    return True


async def test_graceful_shutdown():
    """Test graceful shutdown flushes buffer."""
    print("\n\n🧪 Test 4: Graceful Shutdown")
    print("=" * 60)
    
    system = EternalMemorySystem()
    await system.initialize()
    
    # Add messages
    await system.add_to_buffer("user", "종료 테스트")
    await system.add_to_buffer("assistant", "확인했습니다")
    
    print(f"📦 Added {len(system.conversation_buffer)} messages to buffer")
    
    buffer_file = system.buffer_file
    print(f"   Buffer file exists: {buffer_file.exists()}")
    
    # Graceful shutdown - should auto-flush
    print("\n🛑 Calling close() for graceful shutdown...")
    await system.close()
    
    # Buffer should be empty
    if len(system.conversation_buffer) == 0:
        print("✅ Buffer flushed on shutdown")
    else:
        print(f"❌ Buffer still has {len(system.conversation_buffer)} messages")
        return False
    
    # File should be cleaned up
    if not buffer_file.exists():
        print("✅ Buffer file cleaned up")
    else:
        print(f"⚠️  Buffer file still exists")
    
    return True


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("🚀 BUFFER PERSISTENCE VERIFICATION TESTS")
    print("=" * 60)
    
    results = {}
    
    try:
        results["persistence"] = await test_buffer_persistence()
    except Exception as e:
        print(f"❌ Test 1 failed with error: {e}")
        results["persistence"] = False
    
    try:
        results["search"] = await test_buffer_search()
    except Exception as e:
        print(f"❌ Test 2 failed with error: {e}")
        results["search"] = False
    
    try:
        results["recovery"] = await test_crash_recovery()
    except Exception as e:
        print(f"❌ Test 3 failed with error: {e}")
        results["recovery"] = False
    
    try:
        results["shutdown"] = await test_graceful_shutdown()
    except Exception as e:
        print(f"❌ Test 4 failed with error: {e}")
        results["shutdown"] = False
    
    # Summary
    print("\n\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    total = len(results)
    passed = sum(results.values())
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
