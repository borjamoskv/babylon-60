from __future__ import annotations

from decimal import Decimal

from cortex.consensus.merkle import MerkleTree as VoteMerkleTree
from cortex.consensus.vote_ledger import ImmutableVoteLedger
from cortex.engine.postgres_primary import PostgresPrimaryEngine


def test_vote_hash_parity_between_postgres_and_sqlite() -> None:
    """
    Ensure the vote block hashing logic is completely identical between the SQLite
    ImmutableVoteLedger and PostgresPrimaryEngine, preventing multi-engine forks.
    """
    sqlite_ledger = ImmutableVoteLedger(None)

    # 1. Provide identical mock parameters
    prev_hash = "0" * 64
    fact_id = 101
    agent_id = "agent-x"
    vote = 1
    weight_dec = Decimal("1.75")
    weight_float = 1.75
    timestamp = "2026-03-24T18:15:00+00:00"

    # 2. Compute via SQLite reference engine
    sqlite_hash = sqlite_ledger._compute_hash(
        prev_hash=prev_hash,
        fact_id=fact_id,
        agent_id=agent_id,
        vote=vote,
        weight=weight_dec,
        ts=timestamp,
    )

    # 3. Compute via Postgres engine (passing float for weight)
    pg_hash = PostgresPrimaryEngine._compute_vote_hash(  # type: ignore[call-arg]
        prev_hash=prev_hash,
        fact_id=fact_id,
        agent_id=agent_id,
        value=vote,
        vote_weight=weight_float,
        timestamp=timestamp,
    )

    assert sqlite_hash == pg_hash, "Hash algorithms diverged between SQLite and Postgres!"

def test_vote_merkle_parity() -> None:
    """
    Ensure postgres implementation using VoteMerkleTree behaves as expected.
    """
    hashes = [
        "a" * 64,
        "b" * 64,
        "c" * 64,
        "d" * 64,
    ]
    tree = VoteMerkleTree(hashes)
    assert len(tree.root) == 64
