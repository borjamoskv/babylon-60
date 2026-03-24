from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from cortex.auth.deps import require_verified_permission
from cortex.auth.models import AuthResult
from cortex.crypto import get_default_encrypter


async def _insert_permission_claim(engine, *, tenant_id: str, claim: str, consensus_score: float) -> None:
    enc = get_default_encrypter()
    async with engine.session() as conn:
        await conn.execute(
            """
            INSERT INTO facts (
                tenant_id, project, content, fact_type, tags, metadata, confidence, consensus_score
            ) VALUES (?, 'auth', ?, 'knowledge', '[]', ?, 'verified', ?)
            """,
            (
                tenant_id,
                enc.encrypt_str(claim, tenant_id=tenant_id),
                enc.encrypt_json({"gate": "verified"}, tenant_id=tenant_id),
                consensus_score,
            ),
        )
        await conn.commit()


def _build_request(engine) -> Request:
    app = SimpleNamespace(state=SimpleNamespace(async_engine=engine))
    scope = {
        "type": "http",
        "app": app,
        "headers": [(b"accept-language", b"en")],
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_verified_permission_accepts_consensus_backed_claim(async_engine) -> None:
    claim = "Permission delete:facts granted to api-key-alpha"
    await _insert_permission_claim(async_engine, tenant_id="tenant_a", claim=claim, consensus_score=1.8)

    checker = require_verified_permission("delete:facts", min_consensus=1.6)
    auth = AuthResult(
        authenticated=True,
        tenant_id="tenant_a",
        permissions=["delete:facts"],
        key_name="api-key-alpha",
    )

    result = await checker(_build_request(async_engine), auth)
    assert result is auth


@pytest.mark.asyncio
async def test_verified_permission_rejects_when_consensus_is_missing(async_engine) -> None:
    checker = require_verified_permission("delete:facts", min_consensus=1.6)
    auth = AuthResult(
        authenticated=True,
        tenant_id="tenant_a",
        permissions=["delete:facts"],
        key_name="api-key-alpha",
    )

    with pytest.raises(HTTPException) as exc:
        await checker(_build_request(async_engine), auth)

    assert exc.value.status_code == 403
    assert "requires consensus" in str(exc.value.detail)
