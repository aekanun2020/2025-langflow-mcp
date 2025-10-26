import requests
import os
import json
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import threading

try:
    api_key = os.environ["LANGFLOW_API_KEY"]
except KeyError:
    raise ValueError("LANGFLOW_API_KEY environment variable not found.")

FLOW_IDS = [
    "d29ded11-0b13-4f7b-9616-bf789ac308c1",  # Flow 1
    "ef7a48a6-d502-408c-b945-2285f204addc",  # Flow 2
    "ad4f9e7b-a7fd-4272-a169-31e51a001cc1",  # Flow 3
]

BASE_URL = "http://localhost:7860/api/v1/run"


def extract_message_from_response(response_data):
    try:
        return response_data["outputs"][0]["outputs"][0]["results"]["message"]["text"]
    except (KeyError, IndexError, TypeError):
        return ""


def call_single_flow_with_delay(flow_id, input_message, session_id, delay_seconds, 
                                 winner_event=None):
    """
    เรียก flow เดียว โดยรอ delay_seconds ก่อนเริ่มทำงาน
    
    Args:
        delay_seconds: จำนวนวินาทีที่จะรอก่อนเริ่ม
        winner_event: threading.Event เพื่อ check ว่ามี winner แล้วหรือยัง
    """
    
    # รอตาม delay ที่กำหนด
    if delay_seconds > 0:
        print(f"   ⏳ Flow {flow_id[:8]}... waiting {delay_seconds}s before start")
        
        # แทนที่จะ sleep ตลอด ให้ check winner_event ทุก 0.5 วินาที
        waited = 0
        while waited < delay_seconds:
            if winner_event and winner_event.is_set():
                # มี winner แล้ว! ไม่ต้องเริ่มทำงาน
                print(f"   🛑 Flow {flow_id[:8]}... cancelled (winner found during delay)")
                return (False, flow_id, "", 0, True)  # cancelled=True
            
            time.sleep(min(0.5, delay_seconds - waited))
            waited += 0.5
    
    # เริ่มทำงานจริง
    url = f"{BASE_URL}/{flow_id}"
    
    payload = {
        "output_type": "chat",
        "input_type": "chat",
        "input_value": input_message,
        "session_id": session_id
    }
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }
    
    start_time = time.time()
    
    try:
        print(f"   🚀 Flow {flow_id[:8]}... sending request (after {delay_seconds}s delay)")
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        elapsed = time.time() - start_time
        response_data = response.json()
        message_text = extract_message_from_response(response_data)
        
        if message_text and message_text.strip():
            print(f"   ✅ Flow {flow_id[:8]}... success ({elapsed:.2f}s execution + {delay_seconds}s delay)")
            return (True, flow_id, message_text, elapsed, False)  # cancelled=False
        else:
            print(f"   ⚠️  Flow {flow_id[:8]}... empty response ({elapsed:.2f}s)")
            return (False, flow_id, "", elapsed, False)
            
    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"   ⏱️  Flow {flow_id[:8]}... timeout ({elapsed:.2f}s)")
        return (False, flow_id, "", elapsed, False)
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"   ❌ Flow {flow_id[:8]}... error: {str(e)[:50]}")
        return (False, flow_id, "", elapsed, False)


def call_langflow_staggered_race(input_message, stagger_delay=7,  
                                  max_retries=3, retry_delay=2):
    """
    🏁 STAGGERED RACE MODE with FALLBACK
    
    Strategy:
    1. Flow 1 เริ่มทันที (delay 0s)
    2. Flow 2 เริ่มหลัง 7s
    3. Flow 3 เริ่มหลัง 14s
    4. ใช้คำตอบแรกที่ได้ cancel ที่เหลือทันที
    5. ถ้าทุกตัว empty → retry ทั้งหมด
    
    Args:
        stagger_delay: ระยะห่างระหว่างการเริ่ม flow แต่ละตัว (วินาที)
    """
    
    session_id = str(uuid.uuid4())
    
    for attempt in range(1, max_retries + 1):
        print(f"\n🏁 Attempt {attempt}/{max_retries}: Staggered Racing {len(FLOW_IDS)} flows")
        print(f"   ⏱️  Stagger delay: {stagger_delay}s between each flow\n")
        
        overall_start = time.time()
        winner_event = threading.Event()  # ใช้ signal ว่ามี winner แล้ว
        all_results = []
        winner_found = False
        
        with ThreadPoolExecutor(max_workers=len(FLOW_IDS)) as executor:
            # Submit flows พร้อม delay ที่ต่างกัน
            futures = {}
            for idx, flow_id in enumerate(FLOW_IDS):
                delay = idx * stagger_delay  # 0s, 7s, 14s, 21s, ...
                
                future = executor.submit(
                    call_single_flow_with_delay,
                    flow_id,
                    input_message,
                    session_id,
                    delay,
                    winner_event
                )
                futures[future] = (flow_id, delay)
            
            # รับผลลัพธ์ตามที่เสร็จ (as_completed)
            for future in as_completed(futures):
                flow_id, delay = futures[future]
                success, flow_id, message, elapsed, cancelled = future.result()
                
                if cancelled:
                    # ถูก cancel ก่อนเริ่มทำงาน
                    continue
                
                all_results.append({
                    "flow_id": flow_id,
                    "success": success,
                    "message": message,
                    "elapsed": elapsed,
                    "delay": delay,
                    "total_time": elapsed + delay
                })
                
                if success and not winner_found:
                    # ✅ ได้ winner แล้ว!
                    winner_found = True
                    winner_event.set()  # บอก threads อื่นว่ามี winner แล้ว
                    
                    overall_elapsed = time.time() - overall_start
                    
                    print(f"\n🏆 Winner: {flow_id[:8]}...")
                    print(f"   ⏱️  Delay before start: {delay}s")
                    print(f"   ⚡ Execution time: {elapsed:.2f}s")
                    print(f"   📊 Total time: {overall_elapsed:.2f}s")
                    print(f"   💰 Flows executed: {len([r for r in all_results if not r.get('cancelled', False)])}")
                    
                    # รอให้ threads ที่กำลัง delay อยู่ได้ check winner_event
                    time.sleep(0.5)
                    
                    return message, flow_id, overall_elapsed
        
        # ถ้าถึงตรงนี้ = ทุก flow ล้มเหลว/empty ในรอบนี้
        overall_elapsed = time.time() - overall_start
        success_count = sum(1 for r in all_results if r['success'])
        
        print(f"\n⚠️  Attempt {attempt} failed:")
        print(f"   📊 Results: {success_count}/{len(all_results)} succeeded")
        print(f"   ⏱️  Total time: {overall_elapsed:.2f}s")
        
        # แสดงรายละเอียด
        print(f"\n   Flow Details:")
        for result in sorted(all_results, key=lambda x: x['delay']):
            status = "✅" if result['success'] else "❌"
            print(f"   {status} {result['flow_id'][:8]}... - "
                  f"Delay: {result['delay']}s, "
                  f"Execution: {result['elapsed']:.2f}s, "
                  f"Total: {result['total_time']:.2f}s")
        
        # ถ้ายังมี retry เหลือ
        if attempt < max_retries:
            print(f"\n⏳ Waiting {retry_delay}s before retry {attempt + 1}...")
            time.sleep(retry_delay)
            session_id = str(uuid.uuid4())
        else:
            print(f"\n💥 All {max_retries} attempts exhausted")
    
    raise Exception(
        f"All flows failed after {max_retries} attempts. "
        f"Total flows tried: {len(FLOW_IDS)} x {max_retries} = {len(FLOW_IDS) * max_retries}"
    )


def main():
    """Main interactive loop"""
    
    print("=" * 70)
    print("🏁 Langflow Chat Interface (STAGGERED RACE MODE)")
    print("=" * 70)
    print(f"⚡ Strategy: Staggered start with 7s delay between flows")
    print(f"🎯 First valid response wins")
    print(f"💡 Benefits:")
    print(f"   • Reduces load spike on server")
    print(f"   • Avoids rate limiting")
    print(f"   • Saves resources if first flow succeeds")
    print("=" * 70)
    
    stagger_delay = 7  # วินาที
    
    for i, flow_id in enumerate(FLOW_IDS, 1):
        delay = (i - 1) * stagger_delay
        print(f"   Flow {i}: {flow_id[:12]}... (starts after {delay}s)")
    print("=" * 70)
    print()
    
    stats = {
        "total_queries": 0,
        "successful_queries": 0,
        "total_time": 0
    }
    
    while True:
        try:
            user_input = input("👤 คุณ: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'q', 'ออก']:
                if stats["total_queries"] > 0:
                    print("\n📊 Session Statistics:")
                    print(f"   Total queries: {stats['total_queries']}")
                    print(f"   Successful: {stats['successful_queries']}")
                    success_rate = (stats['successful_queries'] / stats['total_queries']) * 100
                    print(f"   Success rate: {success_rate:.1f}%")
                    avg_time = stats['total_time'] / stats['total_queries']
                    print(f"   Average response time: {avg_time:.2f}s")
                print("\n👋 ขอบคุณที่ใช้บริการ!")
                break
            
            elif user_input.lower() in ['config', 'c', 'ตั้งค่า']:
                print("\n⚙️  Current Configuration:")
                print(f"   Stagger delay: {stagger_delay}s")
                
                new_delay = input("   New delay (seconds, Enter to keep current): ").strip()
                if new_delay:
                    try:
                        stagger_delay = int(new_delay)
                        print(f"   ✅ Updated stagger delay to {stagger_delay}s\n")
                    except ValueError:
                        print("   ❌ Invalid input, keeping current value\n")
                continue
            
            if not user_input:
                print("⚠️  กรุณาพิมพ์คำถาม\n")
                continue
            
            # เรียก API แบบ staggered race
            stats["total_queries"] += 1
            query_start = time.time()
            
            try:
                message, winner_flow, elapsed = call_langflow_staggered_race(
                    user_input,
                    stagger_delay=stagger_delay,  # 7 วินาที
                    max_retries=3,
                    retry_delay=2
                )
                
                stats["successful_queries"] += 1
                stats["total_time"] += elapsed
                
                print(f"\n🤖 AI: {message}")
                print("\n" + "-" * 70 + "\n")
                
            except Exception as e:
                print(f"\n💥 Final Error: {e}")
                print("\n💡 Suggestions:")
                print("   • ตรวจสอบว่า flows ทั้งหมดทำงานปกติ")
                print("   • ลองถามคำถามที่ชัดเจนขึ้น")
                print("   • พิมพ์ 'config' เพื่อปรับ stagger delay")
                print("\n" + "-" * 70 + "\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 ขอบคุณที่ใช้บริการ!")
            break


if __name__ == "__main__":
    main()
