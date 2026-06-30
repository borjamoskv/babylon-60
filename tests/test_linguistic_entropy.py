# [C5-REAL] Exergy-Maximized
"""
Unit tests for LinguisticEntropyDetector.
"""

import pytest
from babylon60.utils.linguistic_entropy import LinguisticEntropyDetector


def test_calculate_char_entropy() -> None:
    detector = LinguisticEntropyDetector()
    entropy_empty = detector.calculate_char_entropy("")
    assert entropy_empty == 0.0

    # High redundancy text -> low entropy
    redundant_text = "aaaa"
    entropy_redundant = detector.calculate_char_entropy(redundant_text)
    assert entropy_redundant == 0.0

    # Normal text
    normal_text = "abcdef"
    entropy_normal = detector.calculate_char_entropy(normal_text)
    assert entropy_normal > 1.5


def test_calculate_word_entropy() -> None:
    detector = LinguisticEntropyDetector()
    entropy_empty = detector.calculate_word_entropy("")
    assert entropy_empty == 0.0

    redundant_text = "word word word word"
    entropy_redundant = detector.calculate_word_entropy(redundant_text)
    assert entropy_redundant == 0.0

    diverse_text = "one two three four"
    entropy_diverse = detector.calculate_word_entropy(diverse_text)
    assert entropy_diverse > 1.0


def test_calculate_ttr() -> None:
    detector = LinguisticEntropyDetector()
    ttr_empty = detector.calculate_ttr("")
    assert ttr_empty == 0.0

    text = "one two one two"
    # 2 unique words / 4 total words = 0.5 TTR
    assert detector.calculate_ttr(text) == 0.5


def test_detect_slop() -> None:
    detector = LinguisticEntropyDetector()
    text_with_slop = "Aquí tienes el código para la función. Espero que esto ayude."
    slop_results = detector.detect_slop(text_with_slop)
    assert len(slop_results) == 2
    assert slop_results[0]["pattern"] == "Aquí tienes el código"
    assert slop_results[1]["pattern"] == "Espero que esto ayude"


def test_analyze() -> None:
    detector = LinguisticEntropyDetector()
    clean_text = "Este es un texto limpio y con alta exergía conceptual para verificar el comportamiento del analizador."
    analysis = detector.analyze(clean_text)
    assert analysis["exergy_score"] == 1.0
    assert analysis["slop_instances_count"] == 0

    slop_text = "Aquí tienes el código. Espero que esto ayude. Aquí tienes el código."
    slop_analysis = detector.analyze(slop_text)
    assert slop_analysis["exergy_score"] < 0.8
    assert slop_analysis["slop_instances_count"] == 3
