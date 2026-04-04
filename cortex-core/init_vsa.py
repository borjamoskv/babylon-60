import sqlite3
import os
import sys
import logging

# Add project root to sys.path
sys.path.append("/Users/borjafernandezangulo/Cortex-Persist")

from cortex.config import DB_PATH
from cortex.extensions.signals.bus import SignalBus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cortex.init_vsa")

def initialize_substrate():
    """Guarantees the Sovereign Memory schema (V5)."""
    logger.info("Initializing Sovereign Memory Substrate: %s", DB_PATH)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    try:
        # 1. Initialize SignalBus (signals table)
        bus = SignalBus(conn)
        bus.ensure_table()
        logger.info("SignalBus schema verified.")
        
        # 2. Initialize Knowledge Table (FTS5)
        conn.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS cortex_knowledge USING fts5(
                ki_id, 
                summary, 
                content
            )
        ''')
        conn.commit()
        logger.info("Knowledge FTS5 schema verified.")
        
    except Exception as e:
        logger.error("Initialization Failed: %s", e)
    finally:
        conn.close()

if __name__ == "__main__":
    initialize_substrate()
