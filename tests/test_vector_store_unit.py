import pytest
from cortex.memory.sqlite_vec_store import cortex_decay


def test_cortex_decay_diamond():
    # Diamonds shouldn't decay
    assert cortex_decay(1, 0, 1000, 7 * 24 * 3600) == 1.0


def test_cortex_decay_future_timestamp():
    # Negative age shouldn't result in > 1 decay multiplier
    assert cortex_decay(0, 1000, 0, 7 * 24 * 3600) == 1.0


def test_cortex_decay_half_life():
    half_life = 7 * 24 * 3600
    timestamp = 1000
    current_time = timestamp + half_life
    assert cortex_decay(0, timestamp, current_time, half_life) == 0.5

    current_time_two_halves = timestamp + (2 * half_life)
    assert cortex_decay(0, timestamp, current_time_two_halves, half_life) == 0.25
