from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone

import pytest

from cortex.darknet.social_ledger import DarknetComment, DarknetLedger, DarknetPost


def test_save_post_normalizes_datetime_created_at(tmp_path) -> None:
    ledger = DarknetLedger(tmp_path / "darknet.sqlite3")
    created_at = datetime(2026, 4, 7, 12, 30, 45, tzinfo=timezone.utc)
    post = DarknetPost(
        id="post-1",
        agent_id="agent-1",
        agent_name="Agent One",
        content="hello world",
        source_url="https://example.com",
        exergy_score=42,
        created_at=created_at,
    )

    ledger.save_post(post)

    with sqlite3.connect(ledger.db_path) as conn:
        row = conn.execute(
            "SELECT created_at FROM darknet_posts WHERE id = ?",
            (post.id,),
        ).fetchone()

    assert row is not None
    assert row[0] == pytest.approx(created_at.timestamp())


def test_save_comment_normalizes_date_created_at(tmp_path) -> None:
    ledger = DarknetLedger(tmp_path / "darknet.sqlite3")
    post = DarknetPost(
        id="post-1",
        agent_id="agent-1",
        agent_name="Agent One",
        content="hello world",
        source_url="https://example.com",
        exergy_score=42,
        created_at=1_755_000_000.0,
    )
    ledger.save_post(post)

    created_at = date(2026, 4, 7)
    comment = DarknetComment(
        id="comment-1",
        post_id=post.id,
        agent_id="agent-2",
        agent_name="Agent Two",
        content="agree",
        created_at=created_at,
    )

    ledger.save_comment(comment)

    expected = datetime(2026, 4, 7, tzinfo=timezone.utc).timestamp()
    with sqlite3.connect(ledger.db_path) as conn:
        row = conn.execute(
            "SELECT created_at FROM darknet_comments WHERE id = ?",
            (comment.id,),
        ).fetchone()

    assert row is not None
    assert row[0] == pytest.approx(expected)
