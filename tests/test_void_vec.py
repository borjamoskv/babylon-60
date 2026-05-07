from __future__ import annotations

import numpy as np

from cortex.utils import void_vec


def test_pack_void_bit_thresholds_positive_values_and_packs_bits() -> None:
    packed = void_vec.pack_void_bit([-1.0, 0.0, 0.1, 2.0, -0.5, 1.0, 0.0, 3.0])

    assert packed == bytes([0b00110101])


def test_pack_void_bit_pads_to_byte_boundary_and_unpack_restores_signs() -> None:
    packed = void_vec.pack_void_bit([1.0, -1.0, 2.0])

    assert len(packed) == 1
    np.testing.assert_array_equal(
        void_vec.unpack_void_bit(packed, dim=3),
        np.array([1.0, -1.0, 1.0], dtype=np.float32),
    )


def test_void_hamming_dist_and_batch_fallback(monkeypatch) -> None:
    monkeypatch.setattr(void_vec, "_accel", None)
    monkeypatch.setattr(void_vec, "_accel_func", None)

    assert void_vec.void_hamming_dist(bytes([0b11110000]), bytes([0b00001111])) == 8
    assert void_vec.void_batch_hamming_dist(
        bytes([0b11110000]),
        [bytes([0b11110000]), bytes([0b00001111])],
    ) == [0, 8]


def test_void_similarity_normalizes_hamming_distance(monkeypatch) -> None:
    monkeypatch.setattr(void_vec, "_accel", None)
    monkeypatch.setattr(void_vec, "_accel_func", None)

    assert void_vec.void_similarity(bytes([0b11110000]), bytes([0b11000000]), total_dim=8) == 0.75
