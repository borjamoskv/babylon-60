"""initial_cortex_schema

Revision ID: f6db3d642a14
Revises:
Create Date: 2026-03-24 17:15:27.359183

"""
from collections.abc import Sequence

from alembic import op
from cortex.storage.pg_schema import PG_ALL_SCHEMA, PG_EXTENSIONS

# revision identifiers, used by Alembic.
revision: str = 'f6db3d642a14'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Extensions
    op.execute(PG_EXTENSIONS)

    # 2. Tables
    for stmt in PG_ALL_SCHEMA:
        op.execute(stmt)


def downgrade() -> None:
    """Downgrade schema."""
    # Basic drop (dangerous in prod, but fine for initial revision logic)
    # Order matters for FKs
    tables = [
        "entity_events", "signals", "evolution_state", "tenants",
        "threat_intel", "episodes", "context_snapshots", "compaction_log",
        "ghosts", "consensus_outcomes", "trust_edges", "vote_merkle_roots",
        "vote_ledger", "consensus_votes_v2", "agents", "consensus_votes",
        "cortex_meta", "time_entries", "heartbeats", "merkle_roots",
        "facts", "transactions", "sessions"
    ]
    for table in tables:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
