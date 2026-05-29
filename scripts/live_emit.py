#!/usr/bin/env python3
"""
CORTEX LIVE Emitter for Antigravity (C5-REAL)
Allows Antigravity 2.0.6 to push state mutations directly into the 
Aether Matrix SSE bus for real-time visual/audio reactivity.
"""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

# Ensure cortex is in path if run standalone
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cortex import config
from cortex.extensions.signals.bus import SignalBus


def main():
    parser = argparse.ArgumentParser(description="Emit C5-REAL payload to CORTEX LIVE")
    parser.add_argument("payload", help="The payload string (JSON or raw text) to emit")
    parser.add_argument("--source", default="antigravity_2.0.6", help="Source of the emission")
    parser.add_argument("--type", default="exergy.live.payload", help="Event type")
    
    args = parser.parse_args()
    
    # Try parsing payload as JSON, otherwise wrap in content dict
    try:
        payload_data = json.loads(args.payload)
    except json.JSONDecodeError:
        payload_data = {"content": args.payload}
        
    db_path = config.DB_PATH
    if not os.path.exists(db_path):
        sys.stderr.write(f"ERROR: Cortex Database not found at {db_path}\n")
        sys.exit(1)
        
    try:
        conn = sqlite3.connect(db_path)
        bus = SignalBus(conn)
        
        signal_id = bus.emit(
            event_type=args.type,
            payload=payload_data,
            source=args.source
        )
        sys.stdout.write(f"C5-REAL: Pulse emitted to CORTEX LIVE. Signal ID: {signal_id}\n")
        sys.exit(0)
    except Exception as e:
        sys.stderr.write(f"ERROR: Failed to emit signal: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
