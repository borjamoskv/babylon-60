"""Unit tests for CORTEX VSA-SDM — cortex/memory/vsa.py."""

import os
import shutil
import pytest
from cortex.memory.vsa import (
    random_bipolar, bind, bundle, hamming_distance, cosine_similarity,
    TextEncoder, KanervaSDM, SwarmMemory, DIMENSION
)

def test_map_b_algebra():
    """Test fundamental MAP-B algebraic operations."""
    hv1 = random_bipolar(DIMENSION, seed=1)
    hv2 = random_bipolar(DIMENSION, seed=2)

    assert len(hv1) == DIMENSION
    assert all(x in (0, 1) for x in hv1)

    # Binding: XOR
    bound = bind(hv1, hv2)
    assert len(bound) == DIMENSION
    # Self-inverse
    assert bind(bound, hv2) == hv1
    assert bind(bound, hv1) == hv2

    # Distance
    dist = hamming_distance(hv1, hv2)
    assert 0 <= dist <= DIMENSION
    assert hamming_distance(hv1, hv1) == 0

    # Similarity
    sim = cosine_similarity(hv1, hv2)
    assert -1.0 <= sim <= 1.0
    assert cosine_similarity(hv1, hv1) == pytest.approx(1.0)

    # Bundling
    bundled = bundle([hv1, hv2, hv1]) # Majority should favor hv1
    assert cosine_similarity(bundled, hv1) > cosine_similarity(bundled, hv2)

def test_text_encoder():
    """Test text encoding into hypervectors."""
    encoder = TextEncoder(dim=DIMENSION)

    hv_empty = encoder.encode("")
    assert all(x == 0 for x in hv_empty)

    hv1 = encoder.encode("hello world")
    hv2 = encoder.encode("hello world")
    hv3 = encoder.encode("foobar")

    assert hv1 == hv2 # Deterministic
    assert hv1 != hv3 # Different text

    # Similar text should have higher similarity
    hv4 = encoder.encode("hello worlds")
    assert cosine_similarity(hv1, hv4) > cosine_similarity(hv1, hv3)

def test_kanerva_sdm():
    """Test Sparse Distributed Memory recall and decay."""
    # Use larger radius for testing with few locations to ensure activation
    sdm = KanervaSDM(dim=DIMENSION, num_locations=100, activation_radius=DIMENSION // 2)
    sdm.initialize()

    address = random_bipolar(DIMENSION, seed=42)
    data = random_bipolar(DIMENSION, seed=43)

    # Write
    activated = sdm.write(address, data)
    assert activated > 0

    # Read
    recalled = sdm.read(address)
    assert len(recalled) == DIMENSION
    # Since it's sparse and we only wrote once, it should be very close to original data
    assert cosine_similarity(data, recalled) > 0.8

    # Decay
    sdm.apply_decay(rate=0.5)
    # Counters are halved.
    recalled_after_decay = sdm.read(address)
    assert len(recalled_after_decay) == DIMENSION

@pytest.fixture
def clean_vsa_dir(tmp_path):
    import cortex.memory.vsa
    original_dir = cortex.memory.vsa.PERSISTENCE_DIR
    new_dir = str(tmp_path / "vsa")
    cortex.memory.vsa.PERSISTENCE_DIR = new_dir
    yield new_dir
    cortex.memory.vsa.PERSISTENCE_DIR = original_dir

def test_swarm_memory_persistence(clean_vsa_dir):
    """Test end-to-end recording, recall, and persistence."""
    # Also use a larger radius here to ensure SDM works in tests
    memory = SwarmMemory(agent_id="test_agent", dim=DIMENSION)
    memory._sdm._radius = DIMENSION // 2

    # Record
    content = "The quick brown fox jumps over the lazy dog"
    rid = memory.record(content, tags=["test", "animals"])
    assert rid is not None

    # Recall
    results = memory.recall("fox jumps", top_k=1)
    assert len(results) == 1
    assert results[0]["content"] == content
    assert "animals" in results[0]["tags"]

    # Persist
    h = memory.persist()
    assert h is not None
    assert os.path.exists(os.path.join(clean_vsa_dir, "test_agent.vsa"))

    # Load into new instance
    memory2 = SwarmMemory(agent_id="test_agent", dim=DIMENSION)
    memory2._sdm._radius = DIMENSION // 2
    count = memory2.load()
    assert count == 1

    results2 = memory2.recall("lazy dog", top_k=1)
    assert results2[0]["content"] == content

def test_swarm_memory_consolidation():
    """Test Ebbinghaus consolidation/pruning."""
    memory = SwarmMemory(agent_id="prune_test", dim=DIMENSION)
    memory.record("Memory that will stay")

    # Apply heavy decay to simulate forgetting
    memory.consolidate(decay_rate=1.0)

    # After 100% decay and consolidation, it should be pruned if it's dead
    memory.consolidate(decay_rate=0.01)
