import os
import sqlite3
import time
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cortex_memory_vsa.db")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def typewriter_print(text, delay=0.02):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def main():
    clear_screen()
    typewriter_print(">>> INITIATING CORTEX-PERSIST MEMORY GENESIS <<<", 0.03)
    typewriter_print("[C5-REAL] Establishing zero-entropy developer context.", 0.03)
    print()
    time.sleep(0.5)
    
    typewriter_print("Your AI assistant has Alzheimer's. You start from zero every morning.")
    typewriter_print("Let's fix that. Forever.\n")
    
    stack = input("[?] What is your immutable tech stack? (e.g., FastAPI, TS, React, Postgres)\n> ")
    avoid = input("\n[?] What architectural patterns or tools do you absolutely AVOID? (e.g., Mongo, Kubernetes, Redux)\n> ")
    style = input("\n[?] What is your preferred code style? (e.g., 'zero-fluff, type-hint everything', 'OOP only')\n> ")
    
    print("\n[!] Crystallizing context into CORTEX-Persist Substrate...")
    time.sleep(1.0)
    
    # Store locally to SQLite Memory
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            knowledge_payload = f"Immutable Tech Stack: {stack}\nAvoids: {avoid}\nCode Style: {style}"
            
            # Using INSERT OR REPLACE to update if it already exists
            cursor.execute(
                "INSERT OR REPLACE INTO cortex_knowledge (ki_id, summary, content) VALUES (?, ?, ?)",
                ("dev_genesis_profile", "Persistent Dev Companion Core Identity", knowledge_payload)
            )
            
            # Optional: inject into the Swarm Queue so agents immediately index it
            cursor.execute(
                "INSERT INTO cortex_swarm_queue (timestamp, agent, payload, status) VALUES (?, ?, ?, ?)",
                (time.monotonic(), "SYSTEM", '{"event": "genesis_profile_updated"}', "PENDING")
            )
            
            conn.commit()
            
        typewriter_print("\n[OK] Memory Genesis sealed. CORTEX now remembers your stack.")
        typewriter_print("From now on, every AI interaction defaults to this architecture. No generic answers.")
        typewriter_print("\nWelcome to the post-stateless era.")
        
    except Exception as e:
        print(f"\n[ERROR] Entropy Detected during CORTEX sealing: {e}")

if __name__ == "__main__":
    main()
