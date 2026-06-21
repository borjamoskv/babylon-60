import json
import os
import yaml
from typing import List, Dict, Any

from .database import get_connection, init_db
from .engine import calculate_hash, generate_10k_events, audit_chain

def export_to_jsonl(filepath: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, type, actor, payload, parent_event, prev_hash, event_hash FROM events ORDER BY id ASC")
    rows = cursor.fetchall()
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        for row in rows:
            event = {
                "id": row[0],
                "timestamp": row[1],
                "type": row[2],
                "actor": row[3],
                "payload": json.loads(row[4]),
                "parent_event": row[5],
                "prev_hash": row[6],
                "event_hash": row[7]
            }
            f.write(json.dumps(event) + '\n')
    conn.close()
    return len(rows)

def replay_from_jsonl(filepath: str):
    # Clear DB first
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM events")
    
    events_to_insert = []
    with open(filepath, 'r') as f:
        for line in f:
            event = json.loads(line)
            events_to_insert.append((
                event["timestamp"],
                event["type"],
                event["actor"],
                json.dumps(event["payload"], sort_keys=True),
                event["parent_event"],
                event["prev_hash"],
                event["event_hash"]
            ))
            
    cursor.executemany("""
        INSERT INTO events (timestamp, type, actor, payload, parent_event, prev_hash, event_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, events_to_insert)
    
    conn.commit()
    conn.close()
    return len(events_to_insert)

def generate_golden_artifacts():
    # 1. Initialize and generate events
    init_db()
    generate_10k_events()
    
    # Define paths
    artifacts_dir = os.path.join(os.path.dirname(__file__), "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    
    jsonl_path = os.path.join(artifacts_dir, "events.jsonl")
    audit_path = os.path.join(artifacts_dir, "audit_report.yaml")
    merkle_path = os.path.join(artifacts_dir, "merkle_root.txt")
    
    # 2. Export to events.jsonl
    export_to_jsonl(jsonl_path)
    
    # 3. Generate Audit Report
    audit_res = audit_chain()
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT event_hash FROM events ORDER BY id DESC LIMIT 1")
    merkle_root = cursor.fetchone()[0]
    conn.close()
    
    report = {
        "cortex_demo_artifact": {
            "input": "events.jsonl",
            "output": [
                "causal_demo.db",
                "audit_report.yaml",
                "merkle_root.txt"
            ],
            "metrics": {
                "total_events": audit_res["events"],
                "broken_hashes": audit_res["broken_hashes"],
                "integrity_status": audit_res["integrity"]
            },
            "merkle_root": merkle_root
        }
    }
    
    with open(audit_path, "w") as f:
        yaml.dump(report, f, default_flow_style=False, sort_keys=False)
        
    with open(merkle_path, "w") as f:
        f.write(merkle_root)
        
    print(f"Golden Artifacts generated in {artifacts_dir}. Merkle Root: {merkle_root}")
    return merkle_root

def test_replay_invariance():
    artifacts_dir = os.path.join(os.path.dirname(__file__), "artifacts")
    merkle_path = os.path.join(artifacts_dir, "merkle_root.txt")
    jsonl_path = os.path.join(artifacts_dir, "events.jsonl")
    
    # Read the golden merkle root
    with open(merkle_path, "r") as f:
        original_root = f.read().strip()
        
    # Replay from JSONL
    print("Replaying from JSONL...")
    replay_from_jsonl(jsonl_path)
    
    # Re-audit
    audit_res = audit_chain()
    assert audit_res["integrity"] == "valid", "Integrity failed after replay"
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT event_hash FROM events ORDER BY id DESC LIMIT 1")
    new_root = cursor.fetchone()[0]
    conn.close()
    
    assert original_root == new_root, f"Merkle root mismatch! {original_root} != {new_root}"
    print("Replay Invariance Test: PASSED. Merkle Root is identical.")

if __name__ == "__main__":
    generate_golden_artifacts()
    test_replay_invariance()
