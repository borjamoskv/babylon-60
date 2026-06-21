import hashlib
from typing import List, Tuple

class Babylon60Vector:
    """
    BABYLON-60 Epistemology C5-REAL Integer Vector.
    Strictly forbids float32/float64 instantiation.
    """
    def __init__(self, data: List[int]):
        for val in data:
            if not isinstance(val, int):
                raise ValueError(f"BABYLON-60 violation: Non-integer scalar detected in vector. Type: {type(val)}")
        self.data = tuple(data)
        
    def __len__(self) -> int:
        return len(self.data)
        
    def __getitem__(self, idx: int) -> int:
        return self.data[idx]

def manhattan_distance(a: Babylon60Vector, b: Babylon60Vector) -> int:
    """
    Calculates L1 Manhattan distance in strict integer bounds.
    """
    if len(a) != len(b):
        raise ValueError("Vector dimension mismatch.")
    return sum(abs(x - y) for x, y in zip(a.data, b.data))

def causal_distance(a: Babylon60Vector, b: Babylon60Vector, time_delta: int) -> int:
    """
    Custom causal distance metric combining spatial Manhattan distance
    with temporal causal offset, ensuring deterministic integer scaling.
    time_delta must be an integer (e.g., milliseconds elapsed).
    """
    spatial = manhattan_distance(a, b)
    # Scaling factor 60 follows BABYLON-60 base.
    return (spatial * 60) + abs(time_delta)

def hash_distance_calculation(query_hash: str, target_hash: str, distance: int) -> str:
    """
    Produces an irreversible, deterministic hash of a distance calculation
    for ingestion into a Merkle Cognition Tree (MCT).
    """
    payload = f"{query_hash}:{target_hash}:{distance}"
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()
