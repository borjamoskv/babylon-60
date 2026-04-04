"""Human Callback API — FastAPI sidecar for human-in-the-loop decisions.

Provides a REST + WebSocket interface for the daemon to request
human input and stream real-time events.

Endpoints:
    GET  /api/status                → daemon status + hot state metrics
    GET  /api/decisions/pending     → list pending decision requests
    POST /api/decisions             → daemon creates a decision request
    POST /api/decisions/{id}/resolve → human resolves a decision
    GET  /api/schedules             → list scheduled tasks
    GET  /api/state/{key}           → query hot state
    WS   /ws/events                 → real-time event stream

Runs on localhost:8741 by default. Same-process as daemon.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.daemon.api")

__all__ = ["HumanCallbackAPI", "DecisionRequest"]

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS decisions (
    id          TEXT PRIMARY KEY,
    question    TEXT NOT NULL,
    context     TEXT NOT NULL DEFAULT '{}',
    options     TEXT NOT NULL DEFAULT '[]',
    urgency     TEXT NOT NULL DEFAULT 'normal',
    status      TEXT NOT NULL DEFAULT 'pending',
    response    TEXT,
    created_at  TEXT NOT NULL,
    resolved_at TEXT,
    expires_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_decisions_status
    ON decisions(status, created_at);
"""


@dataclass
class DecisionRequest:
    """A human decision request from the daemon."""

    id: str = ""
    question: str = ""
    context: dict = field(default_factory=dict)
    options: list[str] = field(default_factory=list)
    urgency: str = "normal"  # low | normal | high | critical
    status: str = "pending"  # pending | resolved | expired
    response: str | None = None
    created_at: str = ""
    resolved_at: str | None = None
    expires_at: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.expires_at:
            self.expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()


class HumanCallbackAPI:
    """FastAPI sidecar for daemon ↔ human communication.

    Usage:
        api = HumanCallbackAPI(
            hot_state=state,
            scheduler=scheduler,
            event_bus=bus,
        )

        # Request a decision from the daemon side
        decision = await api.request_decision(
            question="Deploy to production?",
            options=["yes", "no", "delay_1h"],
            urgency="high",
        )

        # Start the HTTP server (blocks)
        await api.serve()
    """

    __slots__ = (
        "_app",
        "_db_path",
        "_event_bus",
        "_hot_state",
        "_port",
        "_scheduler",
        "_ws_clients",
    )

    def __init__(
        self,
        hot_state: Any | None = None,
        scheduler: Any | None = None,
        event_bus: Any | None = None,
        port: int = 8741,
        db_path: Path | str | None = None,
    ) -> None:
        if db_path is None:
            db_path = Path.home() / ".cortex" / "decisions.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._hot_state = hot_state
        self._scheduler = scheduler
        self._event_bus = event_bus
        self._port = port
        self._ws_clients: list[Any] = []
        self._app = None
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(_SCHEMA)

    # ─── Decision Management ──────────────────────────────────────

    async def request_decision(
        self,
        question: str,
        *,
        context: dict | None = None,
        options: list[str] | None = None,
        urgency: str = "normal",
        ttl_hours: float = 24.0,
    ) -> DecisionRequest:
        """Create a decision request and notify the human."""
        decision = DecisionRequest(
            question=question,
            context=context or {},
            options=options or [],
            urgency=urgency,
            expires_at=(datetime.now(timezone.utc) + timedelta(hours=ttl_hours)).isoformat(),
        )

        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO decisions
                    (id, question, context, options, urgency, status,
                     created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    decision.id,
                    decision.question,
                    json.dumps(decision.context),
                    json.dumps(decision.options),
                    decision.urgency,
                    decision.created_at,
                    decision.expires_at,
                ),
            )

        logger.info(
            "Decision requested [%s]: %s (urgency=%s)",
            decision.id,
            question,
            urgency,
        )

        # macOS notification
        self._send_notification(decision)

        # Broadcast to WebSocket clients
        await self._broadcast_ws(
            {
                "type": "decision.requested",
                "decision": asdict(decision),
            }
        )

        # Event bus
        if self._event_bus is not None:
            await self._event_bus.publish(
                "decision.needed",
                {"decision_id": decision.id, "question": question, "urgency": urgency},
            )

        return decision

    def resolve_decision(self, decision_id: str, response: str) -> DecisionRequest | None:
        """Resolve a pending decision with a human response."""
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM decisions WHERE id = ? AND status = 'pending'",
                (decision_id,),
            ).fetchone()
            if row is None:
                return None

            conn.execute(
                """
                UPDATE decisions
                SET status = 'resolved', response = ?, resolved_at = ?
                WHERE id = ?
                """,
                (response, now, decision_id),
            )
            row = conn.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,)).fetchone()

        decision = self._row_to_decision(row)
        logger.info("Decision resolved [%s]: %s", decision_id, response)
        return decision

    def list_pending(self) -> list[DecisionRequest]:
        """List all pending decisions."""
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            # Expire old decisions first
            conn.execute(
                """
                UPDATE decisions SET status = 'expired'
                WHERE status = 'pending' AND expires_at < ?
                """,
                (now,),
            )
            rows = conn.execute(
                "SELECT * FROM decisions WHERE status = 'pending' ORDER BY created_at DESC"
            ).fetchall()
        return [self._row_to_decision(r) for r in rows]

    def get_decision(self, decision_id: str) -> DecisionRequest | None:
        """Get a decision by ID."""
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_decision(row)

    # ─── Wait for Resolution ─────────────────────────────────────

    async def wait_for_decision(
        self,
        decision_id: str,
        timeout_s: float = 300.0,
        poll_interval: float = 2.0,
    ) -> str | None:
        """Block until a decision is resolved or timeout. Returns response."""
        deadline = asyncio.get_event_loop().time() + timeout_s
        while asyncio.get_event_loop().time() < deadline:
            decision = self.get_decision(decision_id)
            if decision and decision.status == "resolved":
                return decision.response
            await asyncio.sleep(poll_interval)
        return None

    # ─── FastAPI App Creation ─────────────────────────────────────

    def create_app(self):
        """Create the FastAPI application."""
        try:
            from fastapi import FastAPI, HTTPException
            from fastapi.middleware.cors import CORSMiddleware
            from pydantic import BaseModel
        except ImportError:
            logger.warning("FastAPI not installed — API sidecar disabled")
            return None

        app = FastAPI(
            title="CORTEX Daemon — Human Callback API",
            version="1.0.0",
        )
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        class ResolveBody(BaseModel):
            response: str

        class CreateDecisionBody(BaseModel):
            question: str
            context: dict = {}
            options: list[str] = []
            urgency: str = "normal"

        @app.get("/api/status")
        async def get_status():
            result: dict[str, Any] = {"daemon": "running", "port": self._port}
            if self._hot_state is not None:
                result["metrics"] = self._hot_state.metrics()
                result["state_size"] = len(self._hot_state)
            if self._scheduler is not None:
                result["schedules"] = len(self._scheduler.list_schedules())
            result["pending_decisions"] = len(self.list_pending())
            return result

        @app.get("/api/decisions/pending")
        async def get_pending():
            return [asdict(d) for d in self.list_pending()]

        @app.post("/api/decisions")
        async def create_decision(body: CreateDecisionBody):
            decision = await self.request_decision(
                question=body.question,
                context=body.context,
                options=body.options,
                urgency=body.urgency,
            )
            return asdict(decision)

        @app.post("/api/decisions/{decision_id}/resolve")
        async def resolve(decision_id: str, body: ResolveBody):
            result = self.resolve_decision(decision_id, body.response)
            if result is None:
                raise HTTPException(404, "Decision not found or already resolved")
            return asdict(result)

        @app.get("/api/schedules")
        async def get_schedules():
            if self._scheduler is None:
                return []
            return [asdict(s) for s in self._scheduler.list_schedules()]

        @app.get("/api/state/{key}")
        async def get_state(key: str):
            if self._hot_state is None:
                raise HTTPException(503, "Hot state not available")
            value = self._hot_state.get(key)
            if value is None:
                raise HTTPException(404, f"Key '{key}' not found")
            return {"key": key, "value": value}

        self._app = app
        return app

    async def serve(self) -> None:
        """Start the API server. Non-blocking (runs as asyncio task)."""
        app = self.create_app()
        if app is None:
            return

        try:
            import uvicorn

            config = uvicorn.Config(
                app,
                host="127.0.0.1",
                port=self._port,
                log_level="warning",
                access_log=False,
            )
            server = uvicorn.Server(config)
            logger.info("Human Callback API starting on http://127.0.0.1:%d", self._port)
            await server.serve()
        except ImportError:
            logger.warning("uvicorn not installed — API sidecar disabled")

    # ─── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _send_notification(decision: DecisionRequest) -> None:
        """Send macOS native notification for a decision request."""
        try:
            import subprocess
            import sys

            if sys.platform != "darwin":
                return

            title = f"CORTEX Decision [{decision.urgency.upper()}]"
            message = decision.question
            subprocess.Popen(
                [
                    "osascript",
                    "-e",
                    f'display notification "{message}" with title "{title}" sound name "Ping"',
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:  # noqa: BLE001
            pass

    async def _broadcast_ws(self, message: dict) -> None:
        """Broadcast a message to all connected WebSocket clients."""
        dead = []
        for ws in self._ws_clients:
            try:
                await ws.send_json(message)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            self._ws_clients.remove(ws)

    @staticmethod
    def _row_to_decision(row) -> DecisionRequest:
        return DecisionRequest(
            id=row["id"],
            question=row["question"],
            context=json.loads(row["context"]) if row["context"] else {},
            options=json.loads(row["options"]) if row["options"] else [],
            urgency=row["urgency"],
            status=row["status"],
            response=row["response"],
            created_at=row["created_at"],
            resolved_at=row["resolved_at"],
            expires_at=row["expires_at"],
        )
