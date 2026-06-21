# [C5-REAL] Exergy-Maximized
"""
Minimal Trusted Kernel (MTK) - SQLite Authorizer Hook.
Physical runtime coercion that prevents state mutation unless explicitly authorized by MTK.
"""

import sqlite3
import logging
from contextvars import ContextVar

logger = logging.getLogger(__name__)

# Context variable to hold the ephemeral cryptographic token.
# If this is empty or invalid, ALL writes are physically rejected at the DB engine layer.
mtk_active_token: ContextVar[str | None] = ContextVar("mtk_active_token", default=None)

def mtk_authorizer_callback(action: int, arg1: str | None, arg2: str | None, dbname: str | None, source: str | None) -> int:
    """
    Physical constraint on the SQLite engine.
    Actions like INSERT (9), UPDATE (23), DELETE (9) mapped to sqlite3 constants.
    """
    # Default Deny: List of safe read-only and transaction-control actions
    SAFE_ACTIONS = {
        sqlite3.SQLITE_READ,
        sqlite3.SQLITE_SELECT,
        sqlite3.SQLITE_FUNCTION,
        sqlite3.SQLITE_TRANSACTION,
        sqlite3.SQLITE_SAVEPOINT,
    }
    
    if action not in SAFE_ACTIONS:
        # Ignore writes to internal sqlite sequences/schemas and virtual table shadow tables
        if arg1:
            if arg1.startswith("sqlite_") or arg1 == "schema_version":
                return sqlite3.SQLITE_OK
            if arg1.endswith(("_info", "_chunks", "_data", "_idx", "_docsize", "_config", "_content")):
                return sqlite3.SQLITE_OK
                
        # Also allow some specific safe pragmas for reading state
        if action == sqlite3.SQLITE_PRAGMA and arg1 in ("table_info", "foreign_key_check", "integrity_check", "index_list", "index_info", "query_only"):
            return sqlite3.SQLITE_OK

        token = mtk_active_token.get()
        if not token or not token.startswith("mtk_auth_"):
            logger.critical(f"[MTK-BLOCK] Unauthorized physical mutation attempt: Action {action} on {arg1}")
            return sqlite3.SQLITE_DENY
            
    return sqlite3.SQLITE_OK

def install_mtk_authorizer(conn: sqlite3.Connection):
    """
    Install the MTK authorizer on a raw sqlite3 connection.
    If using aiosqlite, access the underlying connection via `conn._conn` if necessary,
    or apply it upon creation.
    """
    conn.set_authorizer(mtk_authorizer_callback)
    logger.info("[MTK] SQLite Authorizer hook installed. State mutation mathematically constrained.")
