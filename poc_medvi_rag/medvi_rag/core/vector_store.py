import json
import logging
import sqlite3
import uuid
from typing import Any

logger = logging.getLogger("medvi_rag.vector_store")

class MedviVectorStore:
    def __init__(self, db_path: str = ":memory:"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        """Inicializa la base de datos simulando sqlite-vec para el PoC."""
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS vendor_protocols (
                    id TEXT PRIMARY KEY,
                    vendor_name TEXT,
                    protocol_text TEXT,
                    api_schema JSON,
                    keywords TEXT  -- Used for mock semantic search
                )
            """)

    def insert_protocol(self, vendor_name: str, protocol_text: str, api_schema: dict, keywords: str):
        """Inserta un protocolo operacional en la base de datos."""
        with self.conn:
            self.conn.execute(
                "INSERT INTO vendor_protocols (id, vendor_name, protocol_text, api_schema, keywords) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), vendor_name, protocol_text, json.dumps(api_schema), keywords)
            )
        logger.info(f"Protocol inserted for vendor: {vendor_name}")

    def semantic_search(self, query: str, limit: int = 1) -> list[dict[str, Any]]:
        """Mock de búsqueda semántica. En producción usa sqlite-vec."""
        query_words = query.lower().split()
        results = []
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM vendor_protocols")
        for row in cursor.fetchall():
            score = 0
            for word in query_words:
                if word in row['keywords'].lower() or word in row['protocol_text'].lower():
                    score += 1
            if score > 0:
                results.append({
                    "vendor_name": row['vendor_name'],
                    "protocol_text": row['protocol_text'],
                    "api_schema": json.loads(row['api_schema']),
                    "score": score
                })
        
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]
