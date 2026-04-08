"""CORTEX v7 — Sovereign Cognitive Ingestion Package.

Unified entry point for the 3 ingestion paradigms:
  - ASTIngestor: Deterministic code parsing (zero LLM cost)
  - PrefixIngestor: Document-to-GPU prefix caching
  - VisionIngestor: Sub-symbolic visual extraction
"""

from cortex.memory.ingestion.ast_ingestor import ASTIngestor

__all__ = [
    "ASTIngestor",
]
