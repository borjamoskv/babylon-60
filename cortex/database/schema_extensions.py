# [C5-REAL] Exergy-Maximized
"""schema_extensions - Extended SQLite tables for CORTEX v5.

Extracted from database/schema.py to satisfy the Landauer LOC barrier.
Now refactored into domain-specific sub-schemas to maintain O(1) complexity.
"""

from cortex.database.schema_defs import (
    consensus, graph, context, episodes, evolution, signals,
    events, locks, telemetry, enrichment, ledger, facts
)

modules = [
    consensus, graph, context, episodes, evolution, signals,
    events, locks, telemetry, enrichment, ledger, facts
]

EXTENSION_SCHEMA = []
for mod in modules:
    EXTENSION_SCHEMA.extend(mod.SCHEMA)
    for k, v in vars(mod).items():
        if k.startswith("CREATE_"):
            globals()[k] = v
