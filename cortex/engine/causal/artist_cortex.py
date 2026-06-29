from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


SCHEMA_SQL = Path(__file__).resolve().parents[2] / "db" / "schema.sql"


@dataclass(frozen=True)
class CortexThresholds:
    default_decision_threshold: float = 0.80
    distribution_floor: float = 0.25
    originality_floor: float = 0.35
    anchor_lock_days: int = 30
    colapse_interval_cycles: int = 12


class ArtistCortex:
    def __init__(self, db_path: str | os.PathLike[str]) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.conn.execute("PRAGMA journal_mode = WAL;")
        self._init_schema()

    def close(self) -> None:
        self.conn.close()

    def _init_schema(self) -> None:
        with open(SCHEMA_SQL, "r", encoding="utf-8") as f:
            self.conn.executescript(f.read())
        self.conn.commit()

    def bootstrap_project(self, name: str, core_vector: str) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO projects(name, core_optimization_vector)
            VALUES (?, ?)
            """,
            (name, core_vector),
        )
        project_id = int(cur.lastrowid)
        self.conn.execute(
            """
            INSERT OR IGNORE INTO thresholds(project_id)
            VALUES (?)
            """,
            (project_id,),
        )
        self.conn.commit()
        return project_id

    def start_session(self, project_id: int, notes: str = "") -> int:
        cur = self.conn.execute(
            """
            INSERT INTO sessions(project_id, notes)
            VALUES (?, ?)
            """,
            (project_id, notes),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def log_event(self, session_id: int, event_type: str, payload: dict[str, Any] | str) -> int:
        payload_text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
        cur = self.conn.execute(
            """
            INSERT INTO events(session_id, event_type, payload)
            VALUES (?, ?, ?)
            """,
            (session_id, event_type, payload_text),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def log_think(self, session_id: int, payload: dict[str, Any]) -> int:
        return self.log_event(session_id, "THINK", payload)

    def log_input(self, session_id: int, payload: dict[str, Any]) -> int:
        return self.log_event(session_id, "INPUT", payload)

    def log_output(
        self,
        session_id: int,
        kind: str,
        uri: str,
        content: bytes | str,
    ) -> int:
        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        else:
            content_bytes = content

        content_hash = hashlib.sha256(content_bytes).hexdigest()
        cur = self.conn.execute(
            """
            INSERT INTO artifacts(session_id, kind, uri, content_hash)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, kind, uri, content_hash),
        )
        self.conn.execute(
            """
            INSERT INTO decisions(session_id, decision_type, rationale)
            VALUES (?, 'APPROVE', ?)
            """,
            (session_id, f"artifact:{kind}:{content_hash[:12]}"),
        )
        self.log_event(session_id, "OUTPUT", {"kind": kind, "uri": uri, "hash": content_hash})
        self.conn.commit()
        return int(cur.lastrowid)

    def update_metrics(
        self,
        session_id: int,
        *,
        think_to_exec_ms: int,
        originality_ratio: float,
        recombination_ratio: float,
        default_decision_ratio: float,
        distribution_yield: float,
        aesthetic_hash: str,
        rupture_count: int,
    ) -> None:
        self.conn.execute(
            """
            UPDATE metrics
            SET think_to_exec_ms = ?,
                originality_ratio = ?,
                recombination_ratio = ?,
                default_decision_ratio = ?,
                distribution_yield = ?,
                aesthetic_hash = ?,
                rupture_count = ?,
                last_updated = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE session_id = ?
            """,
            (
                think_to_exec_ms,
                originality_ratio,
                recombination_ratio,
                default_decision_ratio,
                distribution_yield,
                aesthetic_hash,
                rupture_count,
                session_id,
            ),
        )
        self.conn.commit()

    def build_aesthetic_hash(self, values: dict[str, Any]) -> str:
        # Tres ejes estables. Cambia los nombres, no la idea.
        axes = {
            "density": values.get("density", 0),
            "contrast": values.get("contrast", 0),
            "fracture": values.get("fracture", 0),
        }
        raw = json.dumps(axes, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]

    def evaluate_session(self, session_id: int) -> dict[str, Any]:
        session = self.conn.execute(
            """
            SELECT s.id, s.status, s.started_at, s.ended_at, p.core_optimization_vector,
                   t.default_decision_threshold, t.distribution_floor, t.originality_floor
            FROM sessions s
            JOIN projects p ON p.id = s.project_id
            LEFT JOIN thresholds t ON t.project_id = p.id
            WHERE s.id = ?
            """,
            (session_id,),
        ).fetchone()

        metrics = self.conn.execute(
            "SELECT * FROM metrics WHERE session_id = ?",
            (session_id,),
        ).fetchone()

        if session is None or metrics is None:
            raise ValueError(f"session_id inválido: {session_id}")

        abort_reasons: list[str] = []

        if float(metrics["default_decision_ratio"]) > float(session["default_decision_threshold"]):
            abort_reasons.append("default_decision_ratio_over_threshold")

        if float(metrics["distribution_yield"]) < float(session["distribution_floor"]):
            abort_reasons.append("distribution_yield_under_floor")

        if float(metrics["originality_ratio"]) < float(session["originality_floor"]):
            abort_reasons.append("originality_ratio_under_floor")

        should_abort = len(abort_reasons) > 0

        return {
            "session_id": session_id,
            "core_vector": session["core_optimization_vector"],
            "status": session["status"],
            "metrics": {
                "think_to_exec_ms": metrics["think_to_exec_ms"],
                "originality_ratio": metrics["originality_ratio"],
                "recombination_ratio": metrics["recombination_ratio"],
                "default_decision_ratio": metrics["default_decision_ratio"],
                "distribution_yield": metrics["distribution_yield"],
                "aesthetic_hash": metrics["aesthetic_hash"],
                "rupture_count": metrics["rupture_count"],
            },
            "abort": should_abort,
            "abort_reasons": abort_reasons,
        }

    def enforce(self, session_id: int) -> dict[str, Any]:
        verdict = self.evaluate_session(session_id)
        if verdict["abort"]:
            self.log_event(session_id, "ABORT", {"reasons": verdict["abort_reasons"]})
            self.conn.execute(
                """
                UPDATE sessions
                SET status = 'ABORTED',
                    ended_at = COALESCE(ended_at, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
                WHERE id = ?
                """,
                (session_id,),
            )
            self.conn.commit()
        return verdict

    def lock_anchor(self, project_id: int, label: str, path: str, days: int = 30) -> int:
        locked_until = self._utc_plus_days(days)
        cur = self.conn.execute(
            """
            INSERT INTO anchors(project_id, label, path, locked_until)
            VALUES (?, ?, ?, ?)
            """,
            (project_id, label, path, locked_until),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def release_anchor(self, anchor_id: int) -> None:
        self.conn.execute(
            """
            UPDATE anchors
            SET locked_until = NULL
            WHERE id = ?
            """,
            (anchor_id,),
        )
        self.conn.commit()

    def get_session_state(self, session_id: int) -> dict[str, Any]:
        session = self.conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        metrics = self.conn.execute("SELECT * FROM metrics WHERE session_id = ?", (session_id,)).fetchone()
        events = self.conn.execute(
            "SELECT * FROM events WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
        artifacts = self.conn.execute(
            "SELECT * FROM artifacts WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()

        if session is None:
            raise ValueError(f"session_id inválido: {session_id}")

        return {
            "session": dict(session),
            "metrics": dict(metrics) if metrics else None,
            "events": [dict(row) for row in events],
            "artifacts": [dict(row) for row in artifacts],
        }

    @staticmethod
    def _utc_plus_days(days: int) -> str:
        future = int(time.time()) + (days * 86400)
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(future))


if __name__ == "__main__":
    cortex = ArtistCortex("./30_CORTEX/cortex.db")
    try:
        project_id = cortex.bootstrap_project("30_CORTEX", "ARTE_PURO")
        session_id = cortex.start_session(project_id, notes="boot")
        cortex.log_think(session_id, {"phase": "init"})
        cortex.update_metrics(
            session_id,
            think_to_exec_ms=4200,
            originality_ratio=0.72,
            recombination_ratio=0.28,
            default_decision_ratio=0.19,
            distribution_yield=0.44,
            aesthetic_hash=cortex.build_aesthetic_hash({"density": 8, "contrast": 5, "fracture": 7}),
            rupture_count=1,
        )
        verdict = cortex.enforce(session_id)
        print(json.dumps(verdict, indent=2, ensure_ascii=False))
    finally:
        cortex.close()
