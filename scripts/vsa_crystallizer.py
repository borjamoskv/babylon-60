#!/usr/bin/env python3
import os
import sys
import subprocess
import json
from pathlib import Path

# Add the cortex directory to path to import the engine
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from cortex.vsa_engine import VSAEngine

def get_last_commit_data():
    """Extract metadata and diff from the last commit."""
    try:
        msg = subprocess.check_output(["git", "log", "-1", "--pretty=%B"], text=True).strip()
        author = subprocess.check_output(["git", "log", "-1", "--pretty=%an"], text=True).strip()
        files = subprocess.check_output(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], text=True).strip().split("\n")
        diff = subprocess.check_output(["git", "show", "--pretty=format:", "HEAD"], text=True).strip()
        return {
            "message": msg,
            "author": author,
            "files": files,
            "diff_summary": diff[:5000] # Cap for VSA encoding
        }
    except Exception as e:
        print(f"[VSA] Error getting git data: {e}")
        return None

def main():
    repo_root = Path(__file__).parent.parent
    vsa_path = repo_root / "data" / "vsa" / "history.vsa"
    
    print(f"∴ Crystallizing commit into VSA substrate...")
    
    engine = VSAEngine(D=10000, algebra="HRR", seed=42)
    if vsa_path.exists():
        try:
            engine.load(str(vsa_path))
        except Exception as e:
            print(f"[VSA] Warning: Could not load existing history, starting fresh: {e}")

    data = get_last_commit_data()
    if not data:
        return

    # Create a record for the state
    record = {
        "event": "git_commit",
        "author": data["author"],
        "message": data["message"],
        "files_count": len(data["files"])
    }
    
    # 1. Encode the record (structure)
    state_vec = engine.encode_record(record)
    
    # 2. Encode the diff content as a text hypervector (semantics)
    content_vec = engine.encode_text(data["diff_summary"])
    
    # 3. Bundle them (Context Collapse)
    event_vec = engine.bundle([state_vec, content_vec])
    
    # 4. Bind with commit key (hash)
    commit_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    key_vec = engine.encode_text(commit_hash)
    
    # 5. Memorize (with Ebbinghaus decay set to 0 to preserve forever)
    engine.memorize(key_vec, event_vec, decay_lambda=0.0)
    
    # 6. Persist
    engine.save(str(vsa_path))
    
    print(f"∴ Successfully crystallized commit {commit_hash[:8]} into O(1) VSA memory.")
    print(f"   SNR: {engine.snr:.2f} | Items: {engine.item_count}")

if __name__ == "__main__":
    main()
