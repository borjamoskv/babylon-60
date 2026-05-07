from __future__ import annotations

import pytest

from cortex.utils import compression


def test_quantize_int8_round_trips_embedding_with_expected_shape() -> None:
    embedding = [-1.0, -0.5, 0.0, 0.5, 1.0]

    packed = compression.quantize_int8(embedding)
    restored = compression.dequantize_int8(packed)

    assert len(packed) == 4 + len(embedding)
    assert len(restored) == len(embedding)
    assert restored == pytest.approx(embedding, abs=0.01)


def test_quantize_int8_handles_all_zero_embedding() -> None:
    packed = compression.quantize_int8([0.0, 0.0, 0.0])

    assert compression.dequantize_int8(packed) == [0.0, 0.0, 0.0]


def test_quantize_int8_requires_numpy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(compression, "_NP_AVAILABLE", False)

    with pytest.raises(RuntimeError, match="numpy required"):
        compression.quantize_int8([1.0])

    with pytest.raises(RuntimeError, match="numpy required"):
        compression.dequantize_int8(b"\x00" * 5)


def test_compression_ratio_reports_expected_sizes() -> None:
    ratio = compression.compression_ratio(dim=4)

    assert ratio == {
        "dim": 4,
        "float32_bytes": 16,
        "json_approx_bytes": 28,
        "int8_bytes": 8,
        "ratio_vs_float32": 2.0,
        "ratio_vs_json": 3.5,
    }
