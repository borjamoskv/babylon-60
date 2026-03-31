import logging
import sqlite3

from cortex.search.fts_index import plaintext_from_stored_content, replace_fact_fts_sync

logger = logging.getLogger("cortex")


def _drop_legacy_fts_triggers(conn: sqlite3.Connection) -> None:
    """Remove any trigger that still tries to synchronize `facts_fts` automatically."""
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'trigger'
          AND sql IS NOT NULL
          AND (
              sql LIKE '%facts_fts%'
              OR name IN (
                  'facts_ai',
                  'facts_ad',
                  'facts_au',
                  'trg_facts_fts_insert',
                  'trg_facts_fts_update',
                  'trg_facts_fts_delete'
              )
          )
        """
    ).fetchall()
    for (name,) in rows:
        quoted = name.replace('"', '""')
        conn.execute(f'DROP TRIGGER IF EXISTS "{quoted}"')


def _migration_017_fts_decouple(conn: sqlite3.Connection):
    """
    Decouple facts_fts from the facts table to support encrypted facts
    without creating a plaintext side-channel for encrypted rows.
    Drops trigger-based synchronization and recreates facts_fts as a standalone
    FTS5 table, then repopulates it using the same manual plaintext policy
    used by the runtime write path.
    """
    try:
        # 1. Drop ALL triggers that propagate content to FTS.
        _drop_legacy_fts_triggers(conn)

        # 2. Drop the existing virtual table (which is tied to facts)
        conn.execute("DROP TABLE IF EXISTS facts_fts")

        # 3. Create the new standalone FTS5 table
        conn.execute(
            "CREATE VIRTUAL TABLE facts_fts USING fts5(    content, project, tags, fact_type)"
        )
        logger.info("Migration 017: Recreated facts_fts as a standard FTS5 table")

        # 4. Repopulate facts_fts using the canonical manual plaintext policy.
        cursor = conn.execute(
            "SELECT id, content, project, tags, fact_type FROM facts WHERE valid_until IS NULL"
        )
        rows = cursor.fetchall()

        insert_count = 0
        for row in rows:
            fact_id, stored_content, project, tags_str, fact_type = row
            if replace_fact_fts_sync(
                conn,
                fact_id,
                plaintext=plaintext_from_stored_content(stored_content),
                project=project,
                tags_json=tags_str,
                fact_type=fact_type,
            ):
                insert_count += 1

        logger.info(
            "Migration 017: Successfully repopulated facts_fts with %s plaintext facts",
            insert_count,
        )

    except sqlite3.OperationalError as e:
        logger.warning("Migration 017: Operational error during FTS decoupling: %s", e)
        raise
