from __future__ import annotations

import pytest

from cortex.storage.classifier import DataSensitivity, classify_content


def test_public_content_is_not_sensitive() -> None:
    result = classify_content("Release notes: improve latency and retry behavior.")

    assert isinstance(result, DataSensitivity)
    assert result.score == 0.0
    assert result.matches == []
    assert result.is_sensitive is False
    assert repr(result) == "DataSensitivity(score=0.0, matches=[])"


@pytest.mark.parametrize(
    ("content", "expected_match", "expected_score"),
    [
        ("-----BEGIN RSA PRIVATE KEY-----\nredacted\n-----END RSA PRIVATE KEY-----", "private_key", 1.0),
        ("postgresql://user:pass123@localhost:5432/cortex", "connection_string", 1.0),
        ("Contact owner@example.com before export.", "email_address", 0.9),
        ("token=ghp_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "github_token", 0.8),
        ("api_key = 'ABCDEFGHIJKLMNOPQRSTUVWX'", "generic_api_key", 0.7),
    ],
)
def test_classify_content_assigns_tiered_sensitivity_scores(
    content: str, expected_match: str, expected_score: float
) -> None:
    result = classify_content(content)

    assert result.is_sensitive is True
    assert result.score == expected_score
    assert expected_match in result.matches


def test_multiple_matches_keep_highest_score_and_all_categories() -> None:
    content = (
        "owner@example.com\n"
        "-----BEGIN OPENSSH PRIVATE KEY-----\nredacted\n-----END OPENSSH PRIVATE KEY-----"
    )

    result = classify_content(content)

    assert result.score == 1.0
    assert result.matches == ["private_key", "email_address"]
