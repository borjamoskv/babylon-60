import pytest
import logging
from cortex.guards.contradiction_guard.detector import detect_contradictions

pytestmark = pytest.mark.asyncio


async def test_detect_contradictions_happy_path(fts5_db_path, caplog):
    """Happy Path: valid input with no contradictions passes cleanly."""
    with caplog.at_level(logging.WARNING):
        report = await detect_contradictions(
            new_content="We are adopting RabbitMQ for message queues.",
            new_project="projA",
            db_path=fts5_db_path,
        )
    assert not report.has_conflicts
    assert report.severity == "clean"
    assert "Contradiction scan failed" not in caplog.text


async def test_detect_contradictions_rejection(fts5_db_path, caplog):
    """Rejection/Warning: input directly contradicts an existing decision."""
    with caplog.at_level(logging.WARNING):
        report = await detect_contradictions(
            new_content="We decided to never use Redis for caching anymore.",
            new_project="projA",
            db_path=fts5_db_path,
        )
    assert report.has_conflicts
    assert len(report.candidates) > 0
    assert report.candidates[0].conflict_type == "negation"
    assert "Contradiction scan failed" not in caplog.text


async def test_detect_contradictions_boundary(fts5_db_path, caplog):
    """Boundary Condition: Noise input or very short input should bypass scanning."""
    with caplog.at_level(logging.WARNING):
        report = await detect_contradictions(
            new_content="ok", new_project="projA", db_path=fts5_db_path
        )
    assert not report.has_conflicts

    with caplog.at_level(logging.WARNING):
        report_noise = await detect_contradictions(
            new_content="MAILTV-1: ARCHIVE some text", new_project="projA", db_path=fts5_db_path
        )
    assert not report_noise.has_conflicts
    assert "Contradiction scan failed" not in caplog.text
