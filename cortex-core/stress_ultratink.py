import os
import time
import uuid
import threading
from persistence import LedgerManager, ZeroCopyRingBuffer

def stress_run():
    ledger = LedgerManager()
    ring = ZeroCopyRingBuffer(capacity=100000)
    
    agent_id = uuid.uuid4().bytes[:64].ljust(64, b"\x00")
    payload = b"STRESS_TEST_PAYLOAD"[:183].ljust(183, b"\x00")
    
    NUM_THREADS = 50
    TASKS_PER_THREAD = 1000
    TOTAL = NUM_THREADS * TASKS_PER_THREAD
    
    def worker():
        for _ in range(TASKS_PER_THREAD):
            ring.enqueue(agent_id, payload)
            ledger.append("STRESS_TEST", "VECTOR_OMEGA", 1.5)
            
    start = time.monotonic()
    
    threads = [threading.Thread(target=worker) for _ in range(NUM_THREADS)]
    for t in threads: t.start()
    for t in threads: t.join()
    
    # Wait for the signer queue to drain
    while not ledger._tx_queue.empty():
        time.sleep(0.01)
        
    ledger.close()  # Ensures final flush to AOF
    
    duration = time.monotonic() - start
    
    total_yield = ledger.get_total_yield("VECTOR_OMEGA")
    aof_size = os.path.getsize(ledger.aof_path) if hasattr(ledger, 'aof_path') and os.path.exists(ledger.aof_path) else 0
    
    print(f"--- C5-REAL ULTRATINK STRESS TEST ---")
    print(f"Operations: {TOTAL} Ring Enqueues + {TOTAL} Ledger ZK-Seals")
    print(f"Duration: {duration:.4f} seconds")
    print(f"Throughput: {(TOTAL * 2) / duration:.2f} OPS/sec")
    print(f"AOF Ledger Size: {aof_size / 1024 / 1024:.2f} MB")
    print(f"Total Yield Tracked: {total_yield:.2f}")

if __name__ == "__main__":
    stress_run()
