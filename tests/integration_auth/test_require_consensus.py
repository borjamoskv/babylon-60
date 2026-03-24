from __future__ import annotations

from cortex.auth.deps import require_consensus
from cortex.crypto import get_default_encrypter


async def _insert_claim_fact(
    engine,
    *,
    tenant_id: str,
    claim: str,
    consensus_score: float,
    project: str = "auth",
) -> int:
    enc = get_default_encrypter()
    async with engine.session() as conn:
        cursor = await conn.execute(
            """
            INSERT INTO facts (
                tenant_id, project, content, fact_type, tags, metadata, confidence, consensus_score
            ) VALUES (?, ?, ?, 'knowledge', '[]', ?, 'verified', ?)
            """,
            (
                tenant_id,
                project,
                enc.encrypt_str(claim, tenant_id=tenant_id),
                enc.encrypt_json({"claim": True}, tenant_id=tenant_id),
                consensus_score,
            ),
        )
        await conn.commit()
        return int(cursor.lastrowid)


async def test_require_consensus_resolves_encrypted_claims_per_tenant(async_engine) -> None:
    claim = "Permission delete:facts granted to api-key-alpha"
    await _insert_claim_fact(async_engine, tenant_id="tenant_a", claim=claim, consensus_score=1.9)
    await _insert_claim_fact(async_engine, tenant_id="tenant_b", claim=claim, consensus_score=0.2)

    assert await require_consensus(
        claim,
        min_score=1.6,
        engine=async_engine,
        tenant_id="tenant_a",
    )
    assert not await require_consensus(
        claim,
        min_score=1.6,
        engine=async_engine,
        tenant_id="tenant_b",
    )


async def test_require_consensus_returns_false_when_claim_missing(async_engine) -> None:
    assert not await require_consensus(
        "Permission purge:data granted to api-key-missing",
        min_score=1.6,
        engine=async_engine,
        tenant_id="tenant_a",
    )
