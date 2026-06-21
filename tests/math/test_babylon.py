from cortex.math.babylon import Babylon60Vector, manhattan_distance, causal_distance, hash_distance_calculation
from cortex.embeddings.quantizer import AutocrystallizerQuantizationEdge
import pytest

def test_babylon_vector_strict_integer():
    v1 = Babylon60Vector([1, 2, 3])
    assert len(v1) == 3
    
    with pytest.raises(ValueError, match="BABYLON-60 violation"):
        Babylon60Vector([1.5, 2, 3])

def test_manhattan_distance():
    v1 = Babylon60Vector([100, 200, 300])
    v2 = Babylon60Vector([150, 200, 250])
    dist = manhattan_distance(v1, v2)
    assert dist == 100
    assert isinstance(dist, int)

def test_quantizer_edge():
    edge = AutocrystallizerQuantizationEdge(scaling_factor=1000)
    float_emb = [0.1234, -0.5678, 0.9999]
    int_vec = edge.quantize(float_emb)
    
    assert int_vec[0] == 123
    assert int_vec[1] == -568
    assert int_vec[2] == 1000
    
def test_merkle_distance_hash():
    query_hash = "QHASH123"
    target_hash = "THASH456"
    dist = 847
    
    h1 = hash_distance_calculation(query_hash, target_hash, dist)
    h2 = hash_distance_calculation(query_hash, target_hash, dist)
    
    assert h1 == h2
    assert isinstance(h1, str)
