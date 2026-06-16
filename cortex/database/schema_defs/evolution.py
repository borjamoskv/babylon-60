# [C5-REAL] Exergy-Maximized
"""Evolution State (Continuous Improvement Engine) schema."""

CREATE_EVOLUTION_STATE = """
CREATE TABLE IF NOT EXISTS evolution_state (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle       INTEGER NOT NULL,
    agent_domain TEXT NOT NULL,
    agent_json  TEXT NOT NULL,
    saved_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

CREATE_EVOLUTION_STATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_evo_cycle ON evolution_state(cycle);
CREATE INDEX IF NOT EXISTS idx_evo_domain ON evolution_state(agent_domain);
"""

SCHEMA = [
    CREATE_EVOLUTION_STATE,
    CREATE_EVOLUTION_STATE_INDEX,
]
