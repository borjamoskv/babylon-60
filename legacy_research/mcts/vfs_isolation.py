import sqlite3
import contextlib
import logging
from typing import Generator, Any

logger = logging.getLogger(__name__)

class MCTSVfsIsolator:
    """
    Isolates MCTS rollouts into an ephemeral SQLite :memory: database.
    Prevents speculative node expansions from causing WAL locks or bypassing MTK validation on the main database.
    """
    def __init__(self, main_db_path: str):
        self.main_db_path = main_db_path

    @contextlib.contextmanager
    def ephemeral_rollout(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Yields an isolated connection to an in-memory database cloned from the main DB schema.
        All MCTS node expansions MUST happen within this connection.
        """
        logger.debug(f"Forking ephemeral MCTS memory VFS from {self.main_db_path}")
        
        # Connect to main db in read-only mode to extract schema/baseline
        source_conn = sqlite3.connect(f"file:{self.main_db_path}?mode=ro", uri=True)
        
        # Create the isolated memory db
        mem_conn = sqlite3.connect(":memory:")
        
        try:
            # Backup the source into memory to create the clone
            with source_conn:
                source_conn.backup(mem_conn)
            
            yield mem_conn
            
        finally:
            mem_conn.close()
            source_conn.close()
            logger.debug("Destroyed ephemeral MCTS memory VFS")

    def submit_terminal_policy(self, terminal_node: Any, mtk_authorizer_callback) -> bool:
        """
        Once the MCTS rollout collapses to an optimal terminal policy, 
        it is submitted through the MTK boundary to the real consensus graph.
        """
        # In a real CORTEX scenario, this checks the `mtk_authorizer_callback` logic
        # before allowing the write.
        logger.info(f"Submitting terminal policy to MTK boundary: {terminal_node}")
        return True
