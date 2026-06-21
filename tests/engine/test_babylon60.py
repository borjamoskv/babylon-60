import math
import pytest
try:
    from hypothesis import given, settings
    import hypothesis.strategies as st
    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False

import cortex_rs
from cortex.engine.entropy_core import calculate_entropy_b60

def _compute_entropy_py(data: bytes) -> int:
    counts = [0] * 256
    for b in data:
        counts[b] += 1
    
    entropy_py = 0.0
    for c in counts:
        if c > 0:
            p = c / len(data)
            entropy_py -= p * math.log2(p)
            
    # Scale to Babylon60 format
    return int(round(entropy_py * 216000))

def test_rust_ffi_entropy_b60_contract_basic():
    """
    Test Rust FFI contract comparing Python and Rust BABYLON-60 outputs on standard input.
    """
    data = b"cortex-persist physical enforcement"
    expected_b60_value = _compute_entropy_py(data)
    b60_rust = calculate_entropy_b60(data)
    assert b60_rust.get_value() == expected_b60_value

if HAS_HYPOTHESIS:
    @given(data=st.binary(min_size=1, max_size=10000))
    @settings(max_examples=100)
    def test_rust_ffi_entropy_b60_property(data):
        """
        Property-based testing of Rust FFI contract comparing Python and Rust BABYLON-60 outputs.
        Ensures mathematical equivalence across a wide spectrum of random byte distributions.
        """
        expected_b60_value = _compute_entropy_py(data)
        b60_rust = calculate_entropy_b60(data)
        
        # Due to floating point precision differences between Rust f64 and Python float,
        # the rounding might differ by 1 unit at the boundary. We allow an epsilon of 1.
        assert abs(b60_rust.get_value() - expected_b60_value) <= 1
else:
    @pytest.mark.skip(reason="Hypothesis not installed")
    def test_rust_ffi_entropy_b60_property():
        pass
