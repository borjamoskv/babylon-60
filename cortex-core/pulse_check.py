import sqlite3
import os
import sys

# Add project root to sys.path
sys.path.append("/Users/borjafernandezangulo/Cortex-Persist")
from cortex.config import DB_PATH

def pulse_check():
    """Reads the last 10 signals from the Sovereign Memory Registry."""
    if not os.path.exists(DB_PATH):
        print(f"❌ Substrate Missing: {DB_PATH}")
        return

    print(f"🧠 CORTEX Sovereign Memory Pulse Check: {DB_PATH}")
    print("-" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, event_type, source, created_at, payload 
            FROM signals 
            ORDER BY id DESC 
            LIMIT 10
        """)
        rows = cursor.fetchall()
        
        if not rows:
            print("📭 Ledger empty. Waiting for pulse...")
            return
            
        print(f"{'ID':<4} | {'Event Type':<15} | {'Source':<10} | {'Created At':<20} | {'Payload'}")
        print("-" * 80)
        for r in rows:
            print(f"{r[0]:<4} | {r[1]:<15} | {r[2]:<10} | {r[3]:<20} | {r[4][:60]}...")
            
    except Exception as e:
        print(f"❌ Pulse Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    pulse_check()
