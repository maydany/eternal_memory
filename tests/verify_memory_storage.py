import requests
import time
import json
import sys

BASE_URL = "http://localhost:8000"

def test_memory_persistence():
    print("1. Checking initial database state...")
    try:
        initial_items = requests.get(f"{BASE_URL}/api/database/items").json()
        initial_count = initial_items.get("total", 0)
        print(f"   Initial item count: {initial_count}")
    except Exception as e:
        print(f"   Failed to connect to backend: {e}")
        return

    # User message that definitely contains durable facts
    message = "나는 풋사과를 좋아하며 포켓몬스터도 좋아해, 포켓몬스터에서 제일 좋아하는건 피카츄, 그리고 유튜브 보는 것도 엄청나게 좋아해, 우버 드라이버는 친절한 경우 좋아해"
    
    print(f"\n2. Sending message: '{message[:30]}...'")
    payload = {
        "message": message,
        "mode": "fast"
    }
    
    try:
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/api/chat/conversation", json=payload)
        elapsed = time.time() - start_time
        print(f"   Response status: {response.status_code}")
        print(f"   Response time: {elapsed:.2f}s")
        
        if response.status_code != 200:
            print(f"   Error: {response.text}")
            return
            
        data = response.json()
        print(f"   AI Response: {data.get('response')[:50]}...")
    except Exception as e:
        print(f"   Failed to send message: {e}")
        return

    print("\n3. Waiting for background flush (10 seconds)...")
    time.sleep(10)

    print("\n4. Checking database for new items...")
    try:
        final_items = requests.get(f"{BASE_URL}/api/database/items?size=50").json()
        final_count = final_items.get("total", 0)
        print(f"   Final item count: {final_count}")
        
        new_items_count = final_count - initial_count
        print(f"   New items found: {new_items_count}")
        
        if new_items_count > 0:
            print("\n   Newest items:")
            for item in final_items["items"][:new_items_count]:
                print(f"   - [{item['type']}] {item['content']} (Score: {item['importance']})")
                
            # Verify specific keywords
            contents = [item['content'] for item in final_items["items"][:new_items_count]]
            joined_content = " ".join(contents)
            keywords = ["풋사과", "피카츄", "유튜브", "우버"]
            found = [kw for kw in keywords if kw in joined_content]
            print(f"\n   Keywords found: {found}")
        else:
            print("\n   ❌ No new items stored.")
            
    except Exception as e:
        print(f"   Failed to check database: {e}")

if __name__ == "__main__":
    test_memory_persistence()
