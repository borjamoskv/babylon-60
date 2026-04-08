"""LinkedIn Publish Ledger — Auditable deduplication queue.

Tracks all publish attempts (dry-run and real) with dedup by content_hash.
No record = never published. Record + dry_run=1 = previewed only.
Record + dry_run=0 + success=1 = live on LinkedIn.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

from cortex.database.core import connect

logger = logging.getLogger("cortex.darknet.linkedin_ledger")


@dataclass
class PublishRecord:
    id: str                  # content_hash (16-char SHA256 prefix)
    source_file: str
    article_url: str
    title: str
    git_sha: str
    post_id: str             # LinkedIn post URN or "DRY-<hash>"
    post_url: str
    dry_run: int             # 0 or 1
    success: int             # 0 or 1
    error: str
    published_at: float


class LinkedInLedger:
    """SQLite ledger for LinkedIn publish history."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS linkedin_publishes (
                    id           TEXT PRIMARY KEY,   -- content_hash
                    source_file  TEXT NOT NULL,
                    article_url  TEXT NOT NULL,
                    title        TEXT NOT NULL,
                    git_sha      TEXT NOT NULL,
                    post_id      TEXT NOT NULL DEFAULT '',
                    post_url     TEXT NOT NULL DEFAULT '',
                    dry_run      INTEGER NOT NULL DEFAULT 1,
                    success      INTEGER NOT NULL DEFAULT 0,
                    error        TEXT NOT NULL DEFAULT '',
                    published_at REAL NOT NULL
                )
            """)
            conn.commit()

    def already_published(self, content_hash: str) -> bool:
        """True if a REAL (non dry-run) success record exists for this hash."""
        with connect(str(self.db_path)) as conn:
            row = conn.execute(
                "SELECT 1 FROM linkedin_publishes WHERE id = ? AND dry_run = 0 AND success = 1",
                (content_hash,),
            ).fetchone()
        return row is not None

    def record(
        self,
        content_hash: str,
        source_file: str,
        article_url: str,
        title: str,
        git_sha: str,
        post_id: str,
        post_url: str,
        dry_run: bool,
        success: bool,
        error: str = "",
    ) -> None:
        """Upsert a publish attempt into the ledger."""
        with connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT INTO linkedin_publishes
                    (id, source_file, article_url, title, git_sha,
                     post_id, post_url, dry_run, success, error, published_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    post_id      = excluded.post_id,
                    post_url     = excluded.post_url,
                    dry_run      = excluded.dry_run,
                    success      = excluded.success,
                    error        = excluded.error,
                    published_at = excluded.published_at
                """,
                (
                    content_hash,
                    source_file,
                    article_url,
                    title,
                    git_sha,
                    post_id,
                    post_url or "",
                    1 if dry_run else 0,
                    1 if success else 0,
                    error,
                    time.time(),
                ),
            )
            conn.commit()

    def fetch_history(self, limit: int = 20) -> list[PublishRecord]:
        """Return most recent publish records."""
        with connect(str(self.db_path)) as conn:
            rows = conn.execute(
                """
                SELECT id, source_file, article_url, title, git_sha,
                       post_id, post_url, dry_run, success, error, published_at
                FROM linkedin_publishes
                ORDER BY published_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            PublishRecord(
                id=r[0], source_file=r[1], article_url=r[2],
                title=r[3], git_sha=r[4], post_id=r[5],
                post_url=r[6], dry_run=r[7], success=r[8],
                error=r[9], published_at=r[10],
            )
            for r in rows
        ]
