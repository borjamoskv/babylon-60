"""MOSKV-Aether — Agent Tool Layer.

Thin, sandboxed wrappers the Executor agent dispatches.
All file/shell operations are confined to task.repo_path.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import subprocess
from collections.abc import Callable
from pathlib import Path

import httpx

from cortex.guards.capabilities import RiskTier
from cortex.guards.capability_guard import CapabilityGuard

__all__ = ["AgentToolkit"]

logger = logging.getLogger("cortex.extensions.aether.tools")

_MAX_OUTPUT = 8000  # chars truncated to avoid flooding context
_BASH_TIMEOUT = 60  # seconds

# ── Sovereign Command Guard (Ω₃: Byzantine Default) ──────────────────────
# Destructive patterns that autonomous agents must NEVER execute.
# Checked via substring match on the normalized command string.
FORBIDDEN_BASH_PATTERNS: frozenset[str] = frozenset(
    {
        "rm -rf /",
        "rm -rf ~",
        "rm -rf .",
        "mkfs",
        "dd if=",
        "> /dev/",
        "chmod 777",
        "chmod -R 777",
        "curl | sh",
        "curl | bash",
        "wget | sh",
        "wget | bash",
        "shutdown",
        "reboot",
        "kill -9",
        "killall",
        "pkill -9",
        "launchctl unload",
        "systemctl stop",
        "sudo rm",
        "sudo dd",
        ":(){ :|:& };:",  # fork bomb
        "mv / ",
        "format c:",
        "> /etc/",
        "ssh-keygen -R",
    }
)


class AgentToolkit:
    """Sandboxed tool set for the Aether Executor agent.

    All paths are relative to ``repo_path``.
    ``bash()`` is capped at ``_BASH_TIMEOUT`` seconds.

    Security layers:
        1. Path confinement via ``_safe_path()`` for file operations.
        2. Sovereign Command Guard via ``_sovereign_bash_guard()`` for shell ops.
        3. Timeout ceiling at ``_BASH_TIMEOUT`` seconds.
    """

    def __init__(
        self,
        repo_path: str | Path,
        allowed_tools: list[str] | None = None,
        capability_guard: CapabilityGuard | None = None,
    ) -> None:
        self.repo_path = Path(repo_path).resolve()
        if not self.repo_path.exists():
            raise FileNotFoundError(f"Repo path does not exist: {self.repo_path}")

        self.capability_guard = capability_guard

        # Capability expansion (Standardizing high-level tokens to low-level methods)
        if allowed_tools is not None:
            expanded = set()
            mappings = {
                "filesystem": {"read_file", "write_file", "list_dir"},
                "bash": {"bash"},
                "git": {
                    "git_diff",
                    "git_status",
                    "git_log",
                    "git_commit",
                    "git_create_branch",
                    "git_push",
                },
                "web": {"web_search", "autodidact_ingest"},
                "mcp": {"toolbox_membrane"},
                "ledger": {"ledger_query_fact", "ledger_search"},
            }
            for tool in allowed_tools:
                if tool in mappings:
                    expanded.update(mappings[tool])
                else:
                    expanded.add(tool)
            self.allowed_tools = list(expanded)
        else:
            self.allowed_tools = None

    # ── Path helpers ──────────────────────────────────────────────────

    def _safe_path(self, relative: str) -> Path:
        """Resolve a relative path, ensuring it stays inside repo_path."""
        p = (self.repo_path / relative).resolve()
        if not str(p).startswith(str(self.repo_path)):
            raise PermissionError(f"Path escape attempt blocked: {relative}")
        return p

    @staticmethod
    def _sovereign_bash_guard(cmd: str) -> str | None:
        """Validate a shell command against the Sovereign Command Guard.

        Returns None if the command is safe, or an error string if blocked.
        Axiom Ω₃: I verify, then trust. Never reversed.
        """
        normalized = cmd.lower().strip()
        for pattern in FORBIDDEN_BASH_PATTERNS:
            if pattern in normalized:
                logger.warning(
                    "🛡️ SOVEREIGN GUARD BLOCKED: '%s' matched forbidden pattern '%s'",
                    cmd[:80],
                    pattern,
                )
                return (
                    f"[BLOCKED] Sovereign Command Guard rejected command. "
                    f"Matched forbidden pattern: '{pattern}'. "
                    f"This action requires human authorization."
                )
        return None

    # ── File tools ────────────────────────────────────────────────────

    def read_file(self, path: str) -> str:
        """Read a file relative to repo root. Returns its text content."""
        p = self._safe_path(path)
        if not p.exists():
            return f"[ERROR] File not found: {path}"
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            if len(content) > _MAX_OUTPUT:
                content = content[:_MAX_OUTPUT] + f"\n... [truncated at {_MAX_OUTPUT} chars]"
            return content
        except OSError as e:
            return f"[ERROR] Cannot read {path}: {e}"

    def write_file(self, path: str, content: str) -> str:
        """Write (overwrite) a file relative to repo root."""
        p = self._safe_path(path)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            logger.info("✏️  write_file: %s (%d bytes)", path, len(content))
            return f"OK — wrote {len(content)} bytes to {path}"
        except OSError as e:
            return f"[ERROR] Cannot write {path}: {e}"

    def list_dir(self, path: str = ".") -> str:
        """List directory contents relative to repo root."""
        p = self._safe_path(path)
        if not p.is_dir():
            return f"[ERROR] Not a directory: {path}"
        try:
            entries = sorted(p.iterdir())
            lines = []
            for e in entries[:200]:
                rel = e.relative_to(self.repo_path)
                tag = "/" if e.is_dir() else ""
                lines.append(f"  {rel}{tag}")
            if len(entries) > 200:
                lines.append(f"  ... ({len(entries) - 200} more)")
            return "\n".join(lines) or "(empty)"
        except OSError as e:
            return f"[ERROR] {e}"

    # ── Shell tools ───────────────────────────────────────────────────

    def bash(self, cmd: str, timeout: int = _BASH_TIMEOUT) -> str:
        """Run a shell command in the repo dir. Returns stdout+stderr."""
        # ── Sovereign Command Guard (Ω₃) ──
        blocked = type(self)._sovereign_bash_guard(cmd)
        if blocked:
            return blocked

        logger.info("🔧 bash: %s", cmd[:120])
        try:
            result = subprocess.run(
                cmd,
                shell=True,  # noqa: S602 # nosec B602: Guarded by _sovereign_bash_guard
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
            )
            output = (result.stdout + result.stderr).strip()
            if result.returncode != 0:
                output = f"[FAIL] (exit code: {result.returncode})\n{output}"

            if len(output) > _MAX_OUTPUT:
                output = output[:_MAX_OUTPUT] + "\n... [truncated]"
            return output or "(no output)"
        except subprocess.TimeoutExpired:
            return f"[ERROR] Command timed out after {timeout}s"
        except Exception as e:  # noqa: BLE001
            return f"[ERROR] bash failed: {e}"

    # ── Git tools ─────────────────────────────────────────────────────

    def git_diff(self) -> str:
        """Return current working tree diff."""
        return self.bash("git diff --stat HEAD && git diff HEAD")

    def git_status(self) -> str:
        """Return git status."""
        return self.bash("git status --short")

    def git_log(self, n: int = 5) -> str:
        """Return recent git log."""
        return self.bash(f"git log --oneline -{n}")

    def git_commit(self, message: str) -> str:
        """Stage all changes and commit."""
        safe_msg = message.replace('"', "'")
        return self.bash(f'git add -A && git commit -m "{safe_msg}"')

    def git_create_branch(self, branch_name: str) -> str:
        """Create and checkout a new branch."""
        safe = branch_name.replace(" ", "-").replace("/", "-")[:60]
        return self.bash(f"git checkout -b {safe}")

    def git_push(self, branch: str) -> str:
        """Push branch to origin."""
        return self.bash(f"git push -u origin {branch}")

    # ── Web tool ──────────────────────────────────────────────────────

    def web_search(self, query: str) -> str:
        """Minimal DuckDuckGo instant answer lookup for the agent."""
        try:
            resp = httpx.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": "1"},
                timeout=10.0,
                headers={"User-Agent": "MOSKV-Aether/1.0"},
            )
            data = resp.json()
            abstract = data.get("AbstractText", "")
            related = [r.get("Text", "") for r in data.get("RelatedTopics", [])[:3]]
            result = abstract or " | ".join(related) or "(no result)"
            return result[:2000]
        except Exception as e:  # noqa: BLE001
            return f"[ERROR] web_search failed: {e}"

    def autodidact_ingest(self, target_url: str, intent: str = "Aprender") -> str:
        """Semantic scalpel: ingest documentation using AUTODIDACT-Ω with a specific intent."""
        logger.info("🧠 autodidact_ingest: %s (Intent: %s)", target_url, intent)
        # Inline import to avoid circular dependencies and unnecessary overhead
        try:
            import asyncio

            from cortex.extensions.skills.autodidact.actuator import autodidact_pipeline

            # Helper to run async in sync context
            def _run_async():
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                if loop.is_running():
                    import nest_asyncio  # pyright: ignore[reportMissingImports]

                    nest_asyncio.apply(loop)
                return asyncio.run(autodidact_pipeline(target_url, intent, force=False))

            result = _run_async()
            return f"AUTODIDACT-Ω Result: {result}"
        except Exception as e:  # noqa: BLE001
            return f"[ERROR] Autodidact failed: {e}"

    # ── Ledger tools ──────────────────────────────────────────────────

    @staticmethod
    def _ledger_db_path() -> str:
        """Resolve the active CORTEX ledger database path.

        Precedence: CORTEX_DB_PATH env var → default ~/.cortex/cortex.db.
        """
        return os.environ.get(
            "CORTEX_DB_PATH",
            str(Path.home() / ".cortex" / "cortex.db"),
        )

    def ledger_query_fact(self, fact_id: str) -> str:
        """Query the Sovereign Ledger for a specific event by ID and verify its hash.

        Opens a read-only connection to the ledger DB, fetches the event, recomputes
        its SHA-256 over the stored payload_json and prev_hash, then compares to the
        stored hash.  Returns a compact, LLM-friendly verification report.

        Args:
            fact_id: The ``event_id`` UUID of the ledger event to verify.

        Returns:
            A single-string verification report suitable for an LLM context window.
        """
        db_path = self._ledger_db_path()
        if not Path(db_path).exists():
            return f"[LEDGER] DB not found at {db_path}. Run `cortex init` first."

        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            try:
                row = conn.execute(
                    "SELECT event_id, ts, tool, actor, action, payload_json, "
                    "prev_hash, hash, semantic_status, created_at "
                    "FROM ledger_events WHERE event_id = ?",
                    (fact_id,),
                ).fetchone()
            finally:
                conn.close()
        except sqlite3.OperationalError as e:
            return f"[LEDGER] DB read error: {e}"

        if row is None:
            return f"[LEDGER] Event '{fact_id}' not found."

        stored_hash: str = row["hash"] or ""
        prev_hash: str = row["prev_hash"] or "GENESIS"
        payload_json: str = row["payload_json"] or ""

        # Re-derive hash using the same canonical scheme as LedgerVerifier: reconstruct
        # the LedgerEvent from its stored payload and call compute_hash(prev_hash).
        hash_ok: bool | None = None  # None = unverifiable (parse error)
        try:
            payload = json.loads(payload_json)
            from cortex.ledger.models import (  # local import: avoid top-level cycle
                ActionResult,
                ActionTarget,
                IntentPayload,
                LedgerEvent,
            )

            target = ActionTarget(**payload["target"])
            result = ActionResult(**payload["result"])
            intent = IntentPayload(**payload["intent"]) if payload.get("intent") else None
            event = LedgerEvent(
                event_id=payload["event_id"],
                ts=payload["timestamp"],
                tool=payload["tool"],
                actor=payload["actor"],
                action=payload["action"],
                target=target,
                result=result,
                intent=intent,
                correlation_id=payload.get("correlation_id"),
                trace_id=payload.get("trace_id"),
                prev_hash=payload.get("prev_hash"),
                hash=payload.get("hash"),
                semantic_status=payload.get("semantic_status", "pending"),
                metadata=payload.get("metadata", {}),
            )
            recomputed = event.compute_hash(prev_hash)
            hash_ok = recomputed == stored_hash
        except (ImportError, KeyError, TypeError, ValueError) as e:
            logger.debug("Hash recomputation unavailable for event %s: %s", fact_id, e)
            # payload structure is not a full LedgerEvent (e.g. legacy record) — cannot verify

        if hash_ok is None:
            status_icon = "⚠️ UNVERIFIABLE"
        elif hash_ok:
            status_icon = "✅ VERIFIED"
        else:
            status_icon = "⚠️ COMPROMISED"

        lines = [
            f"[LEDGER] {status_icon} — event_id: {row['event_id']}",
            f"  actor      : {row['actor']}",
            f"  tool       : {row['tool']}",
            f"  action     : {row['action']}",
            f"  ts         : {row['ts']}",
            f"  status     : {row['semantic_status']}",
            f"  stored_hash: {stored_hash[:16]}…",
            f"  hash_match : {hash_ok}",
        ]
        if hash_ok is False:
            lines.append(
                "  ⛔ WARNING: Stored hash does not match recomputed hash. "
                "Ledger integrity may be compromised."
            )
        if hash_ok is None:
            lines.append(
                "  ℹ️  Hash recomputation unavailable — payload may be a legacy record."
            )
        return "\n".join(lines)

    def ledger_search(self, query: str, limit: int = 5) -> str:
        """Search the Sovereign Ledger for events matching a text query.

        Performs a case-insensitive substring search against ``actor``, ``tool``,
        ``action``, and ``payload_json`` columns of the ``ledger_events`` table,
        returning the most recent matching events ordered by timestamp descending.

        Only events with semantic_status in ``('indexed', 'pending')`` are included
        so the agent sees facts that are either fully enriched or awaiting enrichment,
        filtering out transient ``processing`` and ``failed`` entries.

        Args:
            query: Free-text search string.
            limit: Maximum number of results to return (default 5, capped at 20).

        Returns:
            A formatted multi-line string suitable for an LLM context window.
        """
        db_path = self._ledger_db_path()
        if not Path(db_path).exists():
            return f"[LEDGER] DB not found at {db_path}. Run `cortex init` first."

        safe_limit = max(1, min(int(limit), 20))
        pattern = f"%{query}%"

        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    """
                    SELECT event_id, ts, tool, actor, action, hash, semantic_status
                    FROM ledger_events
                    WHERE semantic_status IN ('indexed', 'pending')
                      AND (
                            actor       LIKE ? COLLATE NOCASE
                         OR tool        LIKE ? COLLATE NOCASE
                         OR action      LIKE ? COLLATE NOCASE
                         OR payload_json LIKE ? COLLATE NOCASE
                          )
                    ORDER BY ts DESC
                    LIMIT ?
                    """,
                    (pattern, pattern, pattern, pattern, safe_limit),
                ).fetchall()
            finally:
                conn.close()
        except sqlite3.OperationalError as e:
            return f"[LEDGER] DB read error: {e}"

        if not rows:
            return f"[LEDGER] No events matching '{query}'."

        lines = [f"[LEDGER] {len(rows)} result(s) for '{query}':"]
        for i, row in enumerate(rows, 1):
            h = (row["hash"] or "")[:12]
            lines.append(
                f"  {i}. [{row['ts'][:19]}] {row['actor']} · {row['action']}"
                f"  (tool={row['tool']}, status={row['semantic_status']}, hash={h}…)"
                f"  id={row['event_id']}"
            )
        return "\n".join(lines)

    # ── Dispatch ──────────────────────────────────────────────────────

    def dispatch(self, tool_name: str, args: dict[str, str]) -> str:
        """Dispatch a tool call by name. Returns string result."""

        # 0. Capability Guard Verification (Axiom Ω₄)
        if self.capability_guard:
            # Map tools to their operative RiskTier
            if tool_name in {"read_file", "list_dir", "git_status", "git_log", "git_diff"}:
                tier = RiskTier.TIER_1_LOCAL_SAFE
            elif tool_name in {"web_search", "autodidact_ingest"}:
                tier = RiskTier.TIER_2_REMOTE_READ
            elif tool_name in {"write_file", "git_commit", "git_create_branch"}:
                tier = RiskTier.TIER_3_LOCAL_MUTATION
            elif tool_name in {"bash", "git_push"}:
                tier = RiskTier.TIER_4_REMOTE_MUTATION
            elif tool_name in {"ledger_query_fact", "ledger_search"}:
                tier = RiskTier.TIER_1_LOCAL_SAFE
            else:
                tier = RiskTier.TIER_3_LOCAL_MUTATION

            try:
                # We enforce that the required capability maps exactly to the tool name.
                self.capability_guard.validate_action(tool_name, tier)
            except ValueError as e:
                logger.warning("CapabilityGuard rejected '%s': %s", tool_name, e)
                return f"[ERROR] CapabilityViolationError: {e}"

        # Legacy fallback if no guard provided
        if self.allowed_tools is not None and tool_name not in self.allowed_tools:
            logger.warning("Tool %s intercepted: not in allowed_tools list.", tool_name)
            return (
                f"[ERROR] ToolNotAllowedError: You do not have permission to execute '{tool_name}'."
            )
        handlers: dict[str, Callable[[dict[str, str]], str]] = {
            "read_file": lambda a: self.read_file(a.get("path", "")),
            "write_file": lambda a: self.write_file(a.get("path", ""), a.get("content", "")),
            "list_dir": lambda a: self.list_dir(a.get("path", ".")),
            "bash": lambda a: self.bash(a.get("cmd", ""), int(a.get("timeout", _BASH_TIMEOUT))),
            "git_diff": lambda _: self.git_diff(),
            "git_status": lambda _: self.git_status(),
            "git_log": lambda a: self.git_log(int(a.get("n", 5))),
            "git_commit": lambda a: self.git_commit(a.get("message", "aether: autonomous commit")),
            "git_create_branch": lambda a: self.git_create_branch(a.get("branch", "")),
            "git_push": lambda a: self.git_push(a.get("branch", "")),
            "web_search": lambda a: self.web_search(a.get("query", "")),
            "autodidact_ingest": lambda a: self.autodidact_ingest(
                a.get("target_url", ""), a.get("intent", "Aprender")
            ),
            "ledger_query_fact": lambda a: self.ledger_query_fact(a.get("fact_id", "")),
            "ledger_search": lambda a: self.ledger_search(
                a.get("query", ""),
                int(a["limit"]) if a.get("limit", "").lstrip("-").isdigit() else 5,
            ),
        }
        fn = handlers.get(tool_name)
        if fn is None:
            return f"[ERROR] Unknown tool: {tool_name}"
        try:
            return fn(args)
        except Exception as e:  # noqa: BLE001
            logger.exception("Tool dispatch error [%s]", tool_name)
            return f"[ERROR] {tool_name} raised: {e}"
