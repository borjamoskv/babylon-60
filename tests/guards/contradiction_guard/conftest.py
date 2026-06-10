import pytest
import aiosqlite
import tempfile
import os

@pytest.fixture
async def fts5_db_path():
    """Provides a temporary FTS5-enabled SQLite database path."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    async with aiosqlite.connect(path) as db:
        await db.execute("""
            CREATE TABLE facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project TEXT,
                content TEXT,
                fact_type TEXT,
                created_at TEXT
            )
        """)
        await db.execute("""
            CREATE VIRTUAL TABLE facts_fts USING fts5(
                content,
                content='facts',
                content_rowid='id'
            )
        """)
        await db.execute("""
            CREATE TRIGGER facts_ai AFTER INSERT ON facts BEGIN
                INSERT INTO facts_fts(rowid, content) VALUES (new.id, new.content);
            END;
        """)

        # Insert some test data
        await db.execute("""
            INSERT INTO facts (project, content, fact_type, created_at)
            VALUES
            ('projA', 'We decided to use Redis for caching.', 'decision', '2023-10-01'),
            ('projA', 'PostgreSQL will be our primary database.', 'decision', '2023-10-02'),
            ('projB', 'Never use global variables in this project.', 'decision', '2023-10-03'),
            ('projA', 'MAILTV-1: ARCHIVE ignored decision', 'decision', '2023-10-04')
        """)
        await db.commit()

    yield path
    os.remove(path)
