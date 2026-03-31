"""CORTEX v6.0 — TurboQuant L2 Projection.

Transforms raw L1 JSON bytes (Swarm-100 `_cortex_void_ptr` un-serialized payloads)
into stable 8192-dimensional UINT8 sparse representations. This allows Qdrant semantic
searches (Hamming distance / Dot product) over raw tensors without invoking an LLM embedder.
"""

import hashlib


def project_to_uint8(tensor_bytes: bytes, dim: int = 8192) -> list[int]:
    """Mock TurboQuant deterministically mapping bytes to a fixed-size binary tensor.

    In reality, a True 3-bit activation cache is sparse. We simulate this by hashing
    the byte representation into a seeded deterministic array.

    Args:
        tensor_bytes: Raw L1 cache bytes.
        dim: The VOID_DIM size in Qdrant.

    Returns:
        List of uint8 integers [0-255].
    """
    if not isinstance(tensor_bytes, bytes):
        tensor_bytes = str(tensor_bytes).encode("utf-8")

    # Seed an md5 hash with the input bytes
    base_hash = hashlib.md5(tensor_bytes).digest()

    out = []
    # Generate exactly `dim` bytes by repeatedly hashing
    current = base_hash
    while len(out) < dim:
        out.extend(list(current))
        current = hashlib.md5(current).digest()

    return out[:dim]


def compute_node_id(void_hash: str) -> int:
    """Generate a consistent 64-bit uint node_id from the 32-char L1 pointer hash."""
    # Takes the first 15 hex chars (60 bits) to fit safely in an INT64
    # and avoiding Postgres integer overflow issues during L2 sync.
    return int(void_hash[:15], 16)
