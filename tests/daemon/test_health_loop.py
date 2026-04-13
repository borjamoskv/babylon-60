"""Tests for cortex.daemon.health_loop — autonomous health monitoring."""

from __future__ import annotations

from cortex.extensions.daemon.health_loop import HealthLoop
from cortex.extensions.health.models import Grade, HealthScore, MetricSnapshot


class TestHealthLoop:
    """Tests for HealthLoop tick and alerting logic."""

    def test_tick_returns_data(self):
        """Tick should return a health data dict."""
        loop = HealthLoop(db_path="/tmp/nonexistent.db")
        data = loop.tick()
        assert data is not None
        assert "score" in data
        assert "grade" in data
        assert "healthy" in data
        assert isinstance(data["score"], float)

    def test_tick_grade_stored(self):
        """After tick, last_grade should be updated."""
        loop = HealthLoop(db_path="/tmp/nonexistent.db")
        loop.tick()
        assert isinstance(loop._last_grade, Grade)

    def test_healthy_boolean(self):
        """Healthy should be True when score >= 40."""
        loop = HealthLoop(db_path="/tmp/nonexistent.db")
        data = loop.tick()
        assert data is not None
        if data["score"] >= 40.0:
            assert data["healthy"] is True
        else:
            assert data["healthy"] is False

    def test_grade_change_detection(self, monkeypatch):
        """Grade change should emit a notification on downgrade."""
        notifications: list[str] = []

        def fake_notify(title, body):
            notifications.append(title)

        scores = iter(
            [
                HealthScore(score=96.0, grade=Grade.SOVEREIGN),
                HealthScore(score=42.0, grade=Grade.DEGRADED),
            ]
        )
        monkeypatch.setattr(
            "cortex.extensions.daemon.health_loop.HealthCollector.collect_all",
            lambda self: [MetricSnapshot(name="db", value=0.9)],
        )
        monkeypatch.setattr(
            "cortex.extensions.daemon.health_loop.HealthScorer.score",
            lambda metrics: next(scores),
        )

        loop = HealthLoop(
            db_path="/tmp/nonexistent.db",
            notify_fn=fake_notify,
        )

        loop.tick()
        loop.tick()

        assert notifications

    def test_persist_snapshot_noop_without_engine(self):
        """persist_snapshot should be no-op when engine lacks store_sync."""
        loop = HealthLoop(db_path="/tmp/nonexistent.db")
        data = loop.tick()
        assert data is not None

        class MockEngine:
            def store_sync(self, *args, **kwargs):
                pass

        loop.persist_snapshot(MockEngine(), data)

    def test_interval_default(self):
        """Default interval should be 300 seconds."""
        loop = HealthLoop()
        assert loop._interval == 300

    def test_custom_interval(self):
        """Custom interval should be respected."""
        loop = HealthLoop(interval=60)
        assert loop._interval == 60

    def test_metrics_in_tick(self):
        """Tick results should include metrics list."""
        loop = HealthLoop(db_path="/tmp/nonexistent.db")
        data = loop.tick()
        assert data is not None
        assert "metrics" in data
        assert isinstance(data["metrics"], list)
        for metric in data["metrics"]:
            assert "name" in metric
            assert "value" in metric
            assert "status" in metric

    def test_multiple_ticks_stable(self):
        """Multiple ticks should be stable (no crash)."""
        loop = HealthLoop(db_path="/tmp/nonexistent.db")
        for _ in range(5):
            data = loop.tick()
            assert data is not None

    def test_tick_exposes_component_details(self):
        """Tick should return per-component severity details."""
        loop = HealthLoop(db_path="/tmp/nonexistent.db")
        data = loop.tick()

        assert data is not None
        assert "components" in data
        assert "component_details" in data
        assert "degraded_features" in data

    def test_degraded_alert_mentions_component_names(self, monkeypatch):
        """Degradation alerts should name the affected components."""
        notifications: list[tuple[str, str]] = []

        def fake_notify(title, body):
            notifications.append((title, body))

        monkeypatch.setattr(
            "cortex.extensions.daemon.health_loop.HealthCollector.collect_all",
            lambda self: [
                MetricSnapshot(name="db", value=0.1, weight=1.5),
                MetricSnapshot(name="ledger", value=0.2, weight=1.2),
            ],
        )

        loop = HealthLoop(db_path="/tmp/nonexistent.db", notify_fn=fake_notify)
        data = loop.tick()

        assert data is not None
        assert data["status"] == "blocked"
        assert "db" in data["degraded_features"]
        assert notifications
        assert "db" in notifications[0][1]

    def test_persist_snapshot_includes_degraded_components(self):
        """Persisted snapshot content should mention degraded components when present."""
        captured: dict[str, object] = {}

        class MockEngine:
            def store_sync(self, *args, **kwargs):
                captured["kwargs"] = kwargs

        loop = HealthLoop(db_path="/tmp/nonexistent.db")
        loop.persist_snapshot(
            MockEngine(),
            {
                "score": 42.0,
                "grade": "D",
                "degraded_features": ["db", "wal"],
            },
        )

        assert "db" in str(captured["kwargs"]["content"])

    def test_degrading_trend_alerts_even_when_grade_stays_good(self, monkeypatch):
        """A degrading trend should surface as degraded and notify even before grade collapse."""
        notifications: list[tuple[str, str]] = []

        def fake_notify(title, body):
            notifications.append((title, body))

        monkeypatch.setattr(
            "cortex.extensions.daemon.health_loop.HealthCollector.collect_all",
            lambda self: [MetricSnapshot(name="db", value=0.9, weight=1.0)],
        )
        monkeypatch.setattr(
            "cortex.extensions.daemon.health_loop.HealthScorer.score",
            lambda metrics: HealthScore(score=82.0, grade=Grade.GOOD),
        )
        monkeypatch.setattr(
            "cortex.extensions.daemon.health_loop.TrendDetector.detect_drift",
            lambda self: "degrading",
        )

        loop = HealthLoop(db_path="/tmp/nonexistent.db", notify_fn=fake_notify)
        data = loop.tick()

        assert data is not None
        assert data["status"] == "degraded"
        assert notifications
        assert "trend" in notifications[0][1].lower() or "threshold" in notifications[0][1].lower()
