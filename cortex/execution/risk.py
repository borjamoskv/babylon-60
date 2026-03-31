"""
Risk-Tiered Auto-Allow Engine — Ω₁ Byzantine Deterministic Gate
================================================================
Classifies shell commands into 4 risk tiers.

Tier 0 — SAFE       → auto-allow, no sandbox required
Tier 1 — MONITORED  → auto-allow inside Docker sandbox, full stdout capture
Tier 2 — ELEVATED   → sandboxed + ledger approval required before execution
Tier 3 — CRITICAL   → blocked by default; requires explicit operator override

Exergy invariant (Ω₂): classification is O(1) regex-based, deterministic,
no LLM inference. Guard closes before execution.

Approval tokens: HMAC-SHA256 signed, 300s TTL, tied to (command, tier).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import time
from dataclasses import dataclass, field
from enum import IntEnum


class RiskTier(IntEnum):
    SAFE = 0        # read-only, no side-effects
    MONITORED = 1   # writes to /tmp or ephemeral paths, sandboxed
    ELEVATED = 2    # writes to persistent paths, network ops, installs
    CRITICAL = 3    # rm -rf, DROP TABLE, credential ops, kernel calls


# ---------------------------------------------------------------------------
# Pattern table — ordered from most to least specific.
# Each entry: (compiled_pattern, RiskTier, rationale)
# ---------------------------------------------------------------------------
@dataclass
class _Rule:
    pattern: re.Pattern[str]
    tier: RiskTier
    rationale: str


def _rule(pattern: str, tier: RiskTier, rationale: str) -> _Rule:
    return _Rule(re.compile(pattern, re.IGNORECASE | re.DOTALL), tier, rationale)


_RULES: list[_Rule] = [
    # ── CRITICAL (3) ── highest specificity first
    _rule(r"\brm\s+-rf?\b", RiskTier.CRITICAL, "recursive deletion"),
    _rule(r"\bdd\b.*\bof=", RiskTier.CRITICAL, "raw disk write"),
    _rule(r"\bmkfs\b", RiskTier.CRITICAL, "filesystem format"),
    _rule(r"\b(DROP|TRUNCATE)\s+TABLE\b", RiskTier.CRITICAL, "DDL destruction"),
    _rule(r"\b(shutdown|reboot|halt|poweroff)\b", RiskTier.CRITICAL, "host lifecycle"),
    _rule(r"\bkill\s+-9\b", RiskTier.CRITICAL, "SIGKILL"),
    _rule(r"(chmod|chown)\s+(777|a\+x)\b", RiskTier.CRITICAL, "world-writable perms"),
    _rule(r"\bsudo\b", RiskTier.CRITICAL, "privilege escalation"),
    _rule(r"\bsu\s+-", RiskTier.CRITICAL, "root switch"),
    _rule(r"(export|set)\s+.*?(KEY|TOKEN|SECRET|PASSWORD)", RiskTier.CRITICAL, "credential leak"),
    _rule(r"\bcurl\b.*\|\s*(sh|bash|zsh)", RiskTier.CRITICAL, "remote code execution"),
    _rule(r"\bwget\b.*\|\s*(sh|bash|zsh)", RiskTier.CRITICAL, "remote code execution"),
    _rule(r"eval\s*\(", RiskTier.CRITICAL, "dynamic eval"),
    _rule(r"\binsmod\b|\bmodprobe\b", RiskTier.CRITICAL, "kernel module"),

    # ── ELEVATED (2) ──
    _rule(r"\b(pip|pip3|uv|npm|yarn|cargo|brew)\s+install\b", RiskTier.ELEVATED, "package install"),
    _rule(r"\b(apt|apt-get|yum|dnf|apk)\s+(install|remove|purge)\b", RiskTier.ELEVATED, "sys-package"),
    _rule(r"\bgit\s+(push|force|reset --hard|clean -f)\b", RiskTier.ELEVATED, "git mutation"),
    _rule(r"\bdocker\s+(run|rm|rmi|exec)\b", RiskTier.ELEVATED, "container ops"),
    _rule(r"\bssh\b", RiskTier.ELEVATED, "remote shell"),
    _rule(r"\bscp\b|\brsync\b", RiskTier.ELEVATED, "remote file transfer"),
    _rule(r"\bcurl\b|\bwget\b", RiskTier.ELEVATED, "network fetch"),
    _rule(r"\bopen\s+https?://", RiskTier.ELEVATED, "browser launch"),
    _rule(r">(>?)\s*/(?!(tmp|var/tmp))", RiskTier.ELEVATED, "write to persistent path"),
    _rule(r"\b(mv|cp)\b.*\s/(?!(tmp))", RiskTier.ELEVATED, "file mutation"),
    _rule(r"\balembic\b", RiskTier.ELEVATED, "DB migration"),
    _rule(r"\b(psql|sqlite3|mysql)\b.*(-c|<)", RiskTier.ELEVATED, "DB execution"),

    # ── MONITORED (1) ──
    _rule(r"\bpython\b|\bpython3\b", RiskTier.MONITORED, "python execution"),
    _rule(r"\bnode\b|\bnpx\b|\bnpm\s+run\b", RiskTier.MONITORED, "node execution"),
    _rule(r"\bbash\b|\bzsh\b|\bsh\b", RiskTier.MONITORED, "shell spawn"),
    _rule(r"\bmake\b", RiskTier.MONITORED, "build execution"),
    _rule(r"\bpytest\b|\bunittest\b", RiskTier.MONITORED, "test runner"),
    _rule(r">/tmp/", RiskTier.MONITORED, "write to /tmp"),

    # ── SAFE (0) — default read-only ops ──
    _rule(r"^(ls|cat|echo|pwd|which|type|env|printenv|date|uname)\b", RiskTier.SAFE, "read-only shell"),
    _rule(r"^(git\s+(log|diff|status|show|branch|remote -v))", RiskTier.SAFE, "git read"),
    _rule(r"\bgrep\b|\bfind\b|\bawk\b|\bsed\b.*\|", RiskTier.SAFE, "stream processing"),
    _rule(r"\bhead\b|\btail\b|\bwc\b|\bsort\b|\buniq\b", RiskTier.SAFE, "text tools"),
]


@dataclass
class ClassificationResult:
    command: str
    tier: RiskTier
    matched_rule: str
    auto_allow: bool = field(init=False)

    def __post_init__(self) -> None:
        # Tiers 0 and 1 are auto-allowed. 2+ require approval or operator override.
        self.auto_allow = self.tier <= RiskTier.MONITORED


def classify_command(command: str) -> ClassificationResult:
    """
    Deterministic O(1*n_rules) risk classification.
    Returns the highest tier triggered by any matching rule.
    Default: MONITORED if no rule matches (fail-safe).
    """
    max_tier = RiskTier.SAFE
    matched = "default:safe"

    for rule in _RULES:
        if rule.pattern.search(command):
            if rule.tier > max_tier:
                max_tier = rule.tier
                matched = f"{rule.rationale} [{rule.pattern.pattern[:40]}]"
            if max_tier == RiskTier.CRITICAL:
                break  # Short-circuit at worst case

    # Unknown commands that match nothing default to MONITORED (not SAFE)
    if max_tier == RiskTier.SAFE:
        for safe_rule in _RULES:
            if safe_rule.tier == RiskTier.SAFE and safe_rule.pattern.search(command):
                break
        else:
            max_tier = RiskTier.MONITORED
            matched = "default:unknown_command_monitored"

    return ClassificationResult(command=command, tier=max_tier, matched_rule=matched)


# ---------------------------------------------------------------------------
# HMAC-SHA256 Approval Tokens
# ---------------------------------------------------------------------------

_TOKEN_VERSION = 1
_TOKEN_TTL_S = 300  # 5 minutes


def _get_signing_key() -> bytes:
    """
    Retrieve the HMAC signing key.
    Priority: CORTEX_SANDBOX_SECRET env var → auto-generated ephemeral key.
    """
    secret = os.environ.get("CORTEX_SANDBOX_SECRET")
    if secret:
        return secret.encode("utf-8")
    # Auto-generate deterministic key from machine identity (fallback)
    import uuid
    machine_seed = str(uuid.getnode())  # MAC address as int → str
    return hashlib.sha256(f"cortex-sandbox-{machine_seed}".encode()).digest()


@dataclass(frozen=True)
class ApprovalToken:
    """Signed token authorizing execution of a specific command at a specific tier."""
    command_hash: str  # SHA-256 of the command string
    tier: int
    operator_id: str
    issued_at: float  # time.time() epoch
    version: int
    signature: str

    def serialize(self) -> str:
        """Encode to transport-safe JSON string."""
        return json.dumps({
            "ch": self.command_hash,
            "t": self.tier,
            "op": self.operator_id,
            "ts": self.issued_at,
            "v": self.version,
            "sig": self.signature,
        }, separators=(",", ":"))

    @classmethod
    def deserialize(cls, raw: str) -> ApprovalToken:
        """Decode from JSON string."""
        d = json.loads(raw)
        return cls(
            command_hash=d["ch"],
            tier=d["t"],
            operator_id=d["op"],
            issued_at=d["ts"],
            version=d["v"],
            signature=d["sig"],
        )


def _compute_command_hash(command: str) -> str:
    return hashlib.sha256(command.encode("utf-8")).hexdigest()


def _sign_payload(payload: bytes, key: bytes) -> str:
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def _build_signing_payload(command_hash: str, tier: int, operator_id: str, issued_at: float) -> bytes:
    return f"v{_TOKEN_VERSION}|{command_hash}|{tier}|{operator_id}|{issued_at}".encode("utf-8")


def issue_approval_token(
    command: str,
    tier: RiskTier,
    operator_id: str = "system",
) -> ApprovalToken:
    """
    Issue a signed approval token for a specific command + tier combination.
    Token is valid for _TOKEN_TTL_S seconds.
    """
    key = _get_signing_key()
    command_hash = _compute_command_hash(command)
    issued_at = time.time()
    payload = _build_signing_payload(command_hash, int(tier), operator_id, issued_at)
    signature = _sign_payload(payload, key)

    return ApprovalToken(
        command_hash=command_hash,
        tier=int(tier),
        operator_id=operator_id,
        issued_at=issued_at,
        version=_TOKEN_VERSION,
        signature=signature,
    )


def verify_approval_token(
    token: ApprovalToken | str,
    command: str,
    *,
    max_age: float = _TOKEN_TTL_S,
) -> tuple[bool, str]:
    """
    Verify an approval token against a command.

    Returns:
        (valid: bool, reason: str)
    """
    if isinstance(token, str):
        try:
            token = ApprovalToken.deserialize(token)
        except (json.JSONDecodeError, KeyError) as e:
            return False, f"token_parse_error: {e}"

    # 1. Version check
    if token.version != _TOKEN_VERSION:
        return False, f"version_mismatch: expected={_TOKEN_VERSION} got={token.version}"

    # 2. Command binding
    expected_hash = _compute_command_hash(command)
    if not hmac.compare_digest(token.command_hash, expected_hash):
        return False, "command_mismatch: token is bound to a different command"

    # 3. TTL check
    age = time.time() - token.issued_at
    if age > max_age:
        return False, f"token_expired: age={age:.1f}s max={max_age}s"
    if age < -30:
        return False, f"token_from_future: age={age:.1f}s"

    # 4. HMAC verification
    key = _get_signing_key()
    payload = _build_signing_payload(
        token.command_hash, token.tier, token.operator_id, token.issued_at,
    )
    expected_sig = _sign_payload(payload, key)
    if not hmac.compare_digest(token.signature, expected_sig):
        return False, "signature_invalid: HMAC verification failed"

    return True, "valid"
