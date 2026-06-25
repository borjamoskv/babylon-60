# [C5-REAL] Exergy-Maximized
"""
cortex_rs.py
Strict Native Bridge to cortex_core_rs.
C4-SIM is strictly prohibited. If Rust bindings fail to load, the system hard-fails.
"""


from cortex_core_rs import (
    ASTProjector,
    CognitiveState,
    ExergyRouter,
    Fixed60,
    MTKAuthorizer,
    batch_merkle_root,
    execute_mee_transfer,
    hash_ast,
    ingest_reality_claim,
    init_c5_gate_1_schema,
    validate_exergy_mutation,
    validate_metric_json,
    verify_causal_assertion,
    verify_ephemeral_token,
)
from cortex_core_rs import (
    calculate_entropy_b60 as _calc_entropy_rust,
)

__all__ = [
    "ASTProjector",
    "CognitiveState",
    "ExergyRouter",
    "Fixed60",
    "MTKAuthorizer",
    "batch_merkle_root",
    "execute_mee_transfer",
    "hash_ast",
    "ingest_reality_claim",
    "init_c5_gate_1_schema",
    "validate_exergy_mutation",
    "validate_metric_json",
    "verify_causal_assertion",
    "verify_ephemeral_token",
    "calculate_entropy_b60",
    "Babylon60",
]


# Keep the Python wrapper for Cortex/Babylon60 to provide Pythonic dunder methods
# utilizing the rust backend for pure entropy math
class Cortex:
    def __init__(self, value):
        if isinstance(value, Fixed60):
            self.value = getattr(value, "raw_value", 0)
        else:
            self.value = value
            
    @classmethod
    def from_int(cls, value):
        return cls(value * 216000)
        
    @classmethod
    def from_float(cls, value):
        return cls(int(round(value * 216000)))
        
    def __add__(self, other):
        return Cortex(self.value + other.value)
        
    def __sub__(self, other):
        return Cortex(self.value - other.value)
        
    def __mul__(self, other):
        return Cortex(int((self.value * other.value) / 216000))
        
    def mul(self, other):
        return self * other
        
    def __truediv__(self, other):
        return Cortex(int((self.value * 216000) / other.value))
        
    def __eq__(self, other):
        return self.value == getattr(other, "value", other)
        
    def __lt__(self, other):
        return self.value < other.value
        
    def __le__(self, other):
        return self.value <= other.value
        
    def __hash__(self):
        return hash(self.value)
        
    def __float__(self):
        return self.value / 216000.0
        
    def __int__(self):
        return int(self.value / 216000)
        
    def get_value(self):
        return self.value

def calculate_entropy_b60(data: bytes) -> Cortex:
    """Wrapper to return the Python-friendly Cortex object from Rust Fixed60."""
    return Cortex(_calc_entropy_rust(data))

Babylon60 = Cortex



