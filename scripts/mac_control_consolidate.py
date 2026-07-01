# [C5-REAL] Exergy-Maximized
"""
Consolidates Mac-Control-Ω daemon databases.
Purges old logs/history and vacuums SQLite databases.
"""

import os
import sqlite3
import subprocess
import sys
import time

DB_DIR = "/Users/borjafernandezangulo/.gemini/config/skills/Mac-Control-Ω/scripts"
DB_FILES = {
    "exergy_ledger": os.path.join(DB_DIR, "exergy_ledger.db"),
    "hitl": os.path.join(DB_DIR, "hitl.db"),
    "rules": os.path.join(DB_DIR, "rules.db")
}

def get_file_size(path):
    if os.path.exists(path):
        return os.path.getsize(path)
    return 0

def purge_old_data(db_path):
    """Purges events and executions older than 7 days."""
    if not os.path.exists(db_path):
        return 0, 0
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 7 days limit in seconds (relative to current system time ~1782929473)
    seven_days_ago = time.time() - (7 * 24 * 3600)
    
    # Check rows before
    cursor.execute("SELECT count(*) FROM events WHERE ts < ?", (seven_days_ago,))
    purged_events = cursor.fetchone()[0]
    
    cursor.execute("SELECT count(*) FROM executions WHERE ts < ?", (seven_days_ago,))
    purged_executions = cursor.fetchone()[0]
    
    # Delete
    cursor.execute("DELETE FROM events WHERE ts < ?", (seven_days_ago,))
    cursor.execute("DELETE FROM executions WHERE ts < ?", (seven_days_ago,))
    
    conn.commit()
    conn.close()
    
    return purged_events, purged_executions

def vacuum_db(db_path):
    if not os.path.exists(db_path):
        return False
    conn = sqlite3.connect(db_path)
    conn.execute("VACUUM;")
    conn.close()
    return True

def check_sentinel():
    try:
        res = subprocess.run(
            ["pgrep", "-f", "anti_friction_sentinel.py"],
            capture_output=True,
            text=True,
            check=False
        )
        pids = res.stdout.strip().split()
        return pids if pids else []
    except Exception:
        return []

def main():
    print("[C5-REAL] Starting Mac-Control-Ω Consolidation Protocol...")
    
    results = {}
    
    for name, db_path in DB_FILES.items():
        if not os.path.exists(db_path):
            print(f"[WARNING] Database {name} not found at {db_path}")
            continue
            
        size_before = get_file_size(db_path)
        
        purged_ev, purged_ex = 0, 0
        if name == "exergy_ledger":
            purged_ev, purged_ex = purge_old_data(db_path)
            
        vacuum_db(db_path)
        size_after = get_file_size(db_path)
        
        results[name] = {
            "size_before_bytes": size_before,
            "size_after_bytes": size_after,
            "purged_events": purged_ev,
            "purged_executions": purged_ex
        }
        
        print(f"[{name.upper()}] Size: {size_before} -> {size_after} bytes | Purged: {purged_ev} ev, {purged_ex} ex")

    pids = check_sentinel()
    sentinel_status = f"RUNNING (PID: {', '.join(pids)})" if pids else "STOPPED"
    print(f"[SENTINEL] Status: {sentinel_status}")
    
    print("[SUCCESS] Consolidation completed successfully.")

if __name__ == "__main__":
    main()
