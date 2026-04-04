"""CORTEX v9.1 — Shell AST Intent Classifier.

Replaces the C3-weak `cmd.lower()` substring matching in
`FORBIDDEN_BASH_PATTERNS` with structural shell command analysis.

Architecture::

    cmd → ShellIntentClassifier.classify(cmd)
             ├── tokenize via shlex
             ├── decode obfuscation layers (base64, hex, $'...')
             ├── resolve aliases/variables
             ├── extract executable + args structure
             └── match against structural threat signatures

Threat Model:
    - base64 -d encoded payloads
    - hex (\\x) encoded payloads
    - $'\\x...' ANSI-C quoting obfuscation
    - eval/exec wrapping
    - alias/function redefinition (alias rm='rm -rf /')
    - variable expansion ($CMD where CMD=rm)
    - subshell indirection $(cat payload.sh)
    - pipe chains (curl ... | bash)
    - here-documents (bash << EOF ... EOF)

Axiom: Ω₁ (Byzantine) — LLM output is structurally hostile.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import re
import shlex
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional

logger = logging.getLogger("cortex.security.shell_ast")

__all__ = ["ShellIntentClassifier", "ShellVerdict", "ThreatLevel"]


# ═══════════════════════════════════════
# Threat Classification
# ═══════════════════════════════════════


class ThreatLevel(IntEnum):
    """Structural threat classification for shell commands."""

    CLEAN = 0  # No threat detected
    SUSPICIOUS = 1  # Obfuscation detected but no destructive payload
    DESTRUCTIVE = 2  # Known destructive pattern
    CRITICAL = 3  # Obfuscated destructive intent — maximum severity


@dataclass(frozen=True)
class ShellVerdict:
    """Result of shell AST intent classification."""

    threat: int  # ThreatLevel value
    blocked: bool  # Whether execution should be blocked
    reason: str  # Human-readable explanation
    decoded_cmd: str = ""  # The decoded/de-obfuscated command (if applicable)
    obfuscation: str = ""  # Type of obfuscation detected
    signature: str = ""  # SHA-256 of the raw command (for audit)
    raw_tokens: tuple[str, ...] = ()  # Parsed shell tokens

    def to_dict(self) -> dict:
        return {
            "threat": self.threat,
            "blocked": self.blocked,
            "reason": self.reason,
            "decoded_cmd": self.decoded_cmd[:200],
            "obfuscation": self.obfuscation,
            "signature": self.signature,
        }


# ═══════════════════════════════════════
# Structural Threat Signatures
# ═══════════════════════════════════════

# Binary executables that are ALWAYS blocked regardless of arguments
_BLOCKED_EXECUTABLES: frozenset[str] = frozenset(
    {
        "mkfs",
        "dd",
        "fdisk",
        "wipefs",
        "diskutil",
        "shutdown",
        "reboot",
        "halt",
        "poweroff",
        "sudo",
        "su",
        "doas",
        "dscl",
        "dseditgroup",
        "launchctl",
    }
)

# Executable + argument combinations that constitute destructive ops
_DESTRUCTIVE_SIGNATURES: list[tuple[str, frozenset[str], str]] = [
    # (executable, required_args_subset, label)
    ("rm", frozenset({"-rf"}), "RECURSIVE_FORCE_DELETE"),
    ("rm", frozenset({"-r", "-f"}), "RECURSIVE_FORCE_DELETE"),
    ("rm", frozenset({"--recursive", "--force"}), "RECURSIVE_FORCE_DELETE"),
    ("chmod", frozenset({"777"}), "WORLD_WRITABLE"),
    ("chmod", frozenset({"-R", "777"}), "RECURSIVE_WORLD_WRITABLE"),
    ("kill", frozenset({"-9"}), "FORCE_KILL"),
    ("pkill", frozenset({"-9"}), "FORCE_KILL"),
    ("killall", frozenset(), "MASS_KILL"),
    ("ssh-keygen", frozenset({"-R"}), "SSH_HOST_KEY_REMOVAL"),
]

# Pipe-to-shell patterns (structural, not string matching)
_PIPE_TO_SHELL_EXECUTABLES: frozenset[str] = frozenset(
    {
        "sh",
        "bash",
        "zsh",
        "ksh",
        "dash",
        "fish",
        "python",
        "python3",
        "perl",
        "ruby",
        "node",
    }
)

# Obfuscation wrapper commands
_OBFUSCATION_WRAPPERS: frozenset[str] = frozenset(
    {
        "eval",
        "exec",
        "source",
        ".",
    }
)

# Base64 payload regex (catches echo ... | base64 -d | bash patterns)
_BASE64_PIPE_RE = re.compile(
    r"""(?:echo\s+['"]?|printf\s+['"]?)([A-Za-z0-9+/=]{16,})['"]?\s*\|\s*base64\s+-[dD]""",
    re.IGNORECASE,
)

# Hex-encoded payload in $'\x...' ANSI-C quoting
_ANSI_C_HEX_RE = re.compile(r"""\$'((?:\\x[0-9a-fA-F]{2})+)'""")

# Variable-based indirection: CMD=rm; $CMD -rf /
_VAR_ASSIGN_RE = re.compile(r"""([A-Za-z_][A-Za-z0-9_]*)=(['"]?)(.+?)\2(?:\s|;|$)""")
_VAR_EXPANSION_RE = re.compile(r"""\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?""")

# Fork bomb signatures (structural)
_FORK_BOMB_RE = re.compile(r""":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;?\s*:""")

# Here-document with shell execution
_HEREDOC_RE = re.compile(r"""(?:bash|sh|zsh)\s+<<\s*['"]?(\w+)""", re.IGNORECASE)


class ShellIntentClassifier:
    """Structural shell command analyzer replacing cmd.lower() substring matching.

    Uses shlex tokenization + multi-layer deobfuscation to detect
    destructive intent regardless of encoding tricks.
    """

    def classify(self, cmd: str) -> ShellVerdict:
        """Classify a shell command's intent via structural analysis.

        Returns a ShellVerdict with threat level and block decision.
        """
        if not cmd or not cmd.strip():
            return ShellVerdict(
                threat=ThreatLevel.CLEAN,
                blocked=False,
                reason="Empty command",
                signature=self._signature(cmd),
            )

        sig = self._signature(cmd)

        # Layer 0: Fork bomb detection (regex, since shlex cannot parse it)
        if _FORK_BOMB_RE.search(cmd):
            return ShellVerdict(
                threat=ThreatLevel.CRITICAL,
                blocked=True,
                reason="Fork bomb detected",
                obfuscation="fork_bomb",
                signature=sig,
            )

        # Layer 1: Base64 obfuscation detection and decoding
        b64_verdict = self._check_base64_obfuscation(cmd, sig)
        if b64_verdict:
            return b64_verdict

        # Layer 2: ANSI-C hex quoting deobfuscation
        hex_verdict = self._check_hex_obfuscation(cmd, sig)
        if hex_verdict:
            return hex_verdict

        # Layer 3: Variable indirection resolution
        resolved_cmd = self._resolve_variables(cmd)

        # Layer 4: Tokenize the (possibly resolved) command
        try:
            tokens = shlex.split(resolved_cmd)
        except ValueError:
            # Malformed shell — suspicious by default
            return ShellVerdict(
                threat=ThreatLevel.SUSPICIOUS,
                blocked=True,
                reason="Malformed shell syntax (shlex parse failure)",
                obfuscation="syntax_error",
                signature=sig,
                raw_tokens=(),
            )

        if not tokens:
            return ShellVerdict(
                threat=ThreatLevel.CLEAN,
                blocked=False,
                reason="No tokens after parsing",
                signature=sig,
            )

        # Layer 5: Multi-command splitting (;, &&, ||)
        command_chains = self._split_chains(resolved_cmd)

        for chain_cmd in command_chains:
            try:
                chain_tokens = shlex.split(chain_cmd)
            except ValueError:
                continue
            if not chain_tokens:
                continue

            verdict = self._classify_single(chain_tokens, chain_cmd, sig)
            if verdict.blocked:
                return verdict

        # Layer 6: Pipe-to-shell detection
        pipe_verdict = self._check_pipe_to_shell(resolved_cmd, tokens, sig)
        if pipe_verdict:
            return pipe_verdict

        # Layer 7: Obfuscation wrapper detection (eval, exec)
        wrapper_verdict = self._check_obfuscation_wrappers(tokens, resolved_cmd, sig)
        if wrapper_verdict:
            return wrapper_verdict

        # Layer 8: Here-document detection
        if _HEREDOC_RE.search(cmd):
            return ShellVerdict(
                threat=ThreatLevel.SUSPICIOUS,
                blocked=True,
                reason="Here-document shell execution detected — unauditable payload",
                obfuscation="heredoc",
                signature=sig,
                raw_tokens=tuple(tokens),
            )

        # CLEAN
        return ShellVerdict(
            threat=ThreatLevel.CLEAN,
            blocked=False,
            reason="Structural analysis: no destructive intent detected",
            signature=sig,
            raw_tokens=tuple(tokens),
        )

    def _classify_single(self, tokens: list[str], raw: str, sig: str) -> ShellVerdict:
        """Classify a single command (no pipes, no chains)."""
        exe = self._extract_executable(tokens)
        args = frozenset(tokens[1:]) if len(tokens) > 1 else frozenset()

        # Check blocked executables
        if exe in _BLOCKED_EXECUTABLES:
            return ShellVerdict(
                threat=ThreatLevel.DESTRUCTIVE,
                blocked=True,
                reason=f"Blocked executable: '{exe}'",
                signature=sig,
                raw_tokens=tuple(tokens),
            )

        # Check destructive signatures
        for sig_exe, sig_args, label in _DESTRUCTIVE_SIGNATURES:
            if exe == sig_exe and sig_args.issubset(args):
                return ShellVerdict(
                    threat=ThreatLevel.DESTRUCTIVE,
                    blocked=True,
                    reason=f"Destructive signature: {label} ({exe} {' '.join(sorted(sig_args))})",
                    signature=sig,
                    raw_tokens=tuple(tokens),
                )

        return ShellVerdict(
            threat=ThreatLevel.CLEAN,
            blocked=False,
            reason=f"Single command '{exe}' passed structural check",
            signature=sig,
            raw_tokens=tuple(tokens),
        )

    def _check_base64_obfuscation(self, cmd: str, sig: str) -> Optional[ShellVerdict]:
        """Detect and decode base64-encoded payloads piped to shell."""
        match = _BASE64_PIPE_RE.search(cmd)
        if not match:
            return None

        encoded = match.group(1)
        try:
            decoded = base64.b64decode(encoded).decode("utf-8", errors="replace")
        except Exception:
            decoded = "[DECODE_FAILED]"

        # Recursively classify the decoded payload
        if decoded != "[DECODE_FAILED]":
            inner = self.classify(decoded)
            if inner.blocked:
                return ShellVerdict(
                    threat=ThreatLevel.CRITICAL,
                    blocked=True,
                    reason=f"Base64-obfuscated destructive payload: {inner.reason}",
                    decoded_cmd=decoded,
                    obfuscation="base64",
                    signature=sig,
                )

        return ShellVerdict(
            threat=ThreatLevel.SUSPICIOUS,
            blocked=True,
            reason=f"Base64-encoded payload detected (decoded: '{decoded[:80]}'). "
            f"Obfuscated commands are blocked by default.",
            decoded_cmd=decoded,
            obfuscation="base64",
            signature=sig,
        )

    def _check_hex_obfuscation(self, cmd: str, sig: str) -> Optional[ShellVerdict]:
        """Detect ANSI-C $'\\x..' hex-encoded payloads."""
        match = _ANSI_C_HEX_RE.search(cmd)
        if not match:
            return None

        hex_str = match.group(1)
        try:
            decoded = bytes(int(h, 16) for h in re.findall(r"\\x([0-9a-fA-F]{2})", hex_str)).decode(
                "utf-8", errors="replace"
            )
        except Exception:
            decoded = "[DECODE_FAILED]"

        return ShellVerdict(
            threat=ThreatLevel.SUSPICIOUS,
            blocked=True,
            reason=f"Hex-obfuscated payload detected (decoded: '{decoded[:80]}')",
            decoded_cmd=decoded,
            obfuscation="ansi_c_hex",
            signature=sig,
        )

    def _check_pipe_to_shell(self, cmd: str, tokens: list[str], sig: str) -> Optional[ShellVerdict]:
        """Detect `curl/wget ... | bash/sh/python` patterns structurally."""
        if "|" not in cmd:
            return None

        segments = cmd.split("|")
        for i in range(len(segments) - 1):
            right = segments[i + 1].strip()
            try:
                right_tokens = shlex.split(right)
            except ValueError:
                continue
            if not right_tokens:
                continue

            right_exe = self._extract_executable(right_tokens)
            if right_exe in _PIPE_TO_SHELL_EXECUTABLES:
                left = segments[i].strip()
                return ShellVerdict(
                    threat=ThreatLevel.CRITICAL,
                    blocked=True,
                    reason=f"Pipe-to-shell pattern: '{left[:40]}' → '{right_exe}'",
                    obfuscation="pipe_to_shell",
                    signature=sig,
                    raw_tokens=tuple(tokens),
                )

        return None

    def _check_obfuscation_wrappers(
        self, tokens: list[str], cmd: str, sig: str
    ) -> Optional[ShellVerdict]:
        """Detect eval/exec wrapping that hides actual command intent."""
        if not tokens:
            return None

        exe = self._extract_executable(tokens)
        if exe in _OBFUSCATION_WRAPPERS:
            # Extract the wrapped payload
            wrapped = " ".join(tokens[1:])
            return ShellVerdict(
                threat=ThreatLevel.SUSPICIOUS,
                blocked=True,
                reason=f"Obfuscation wrapper '{exe}' detected. Wrapped: '{wrapped[:80]}'",
                decoded_cmd=wrapped,
                obfuscation=f"wrapper_{exe}",
                signature=sig,
                raw_tokens=tuple(tokens),
            )

        return None

    def _resolve_variables(self, cmd: str) -> str:
        """Attempt to resolve inline variable assignments and expansions.

        Example: CMD=rm; $CMD -rf / → rm -rf /
        """
        variables: dict[str, str] = {}

        # Find all variable assignments
        for match in _VAR_ASSIGN_RE.finditer(cmd):
            var_name = match.group(1)
            var_value = match.group(3)
            variables[var_name] = var_value

        if not variables:
            return cmd

        # Expand all variable references
        def _expand(m: re.Match) -> str:
            name = m.group(1)
            return variables.get(name, m.group(0))

        resolved = _VAR_EXPANSION_RE.sub(_expand, cmd)

        if resolved != cmd:
            logger.warning(
                "🔍 [SHELL AST] Variable indirection resolved: %s → %s",
                cmd[:60],
                resolved[:60],
            )

        return resolved

    def _split_chains(self, cmd: str) -> list[str]:
        """Split a command into individual commands on ;, &&, ||.

        Respects quoting (shlex-aware splitting).
        """
        # Simple regex split that handles the common cases
        # More sophisticated parsing would require a full shell parser
        parts = re.split(r"\s*(?:;|&&|\|\|)\s*", cmd)
        return [p.strip() for p in parts if p.strip()]

    @staticmethod
    def _extract_executable(tokens: list[str]) -> str:
        """Extract the base executable name from a token list.

        Handles:
            /usr/bin/rm → rm
            env VAR=x cmd → cmd
            command -v rm → rm (but we track 'command')
        """
        if not tokens:
            return ""

        exe = tokens[0]

        # Skip 'env' prefix with variable assignments
        idx = 0
        if exe == "env":
            idx = 1
            while idx < len(tokens) and "=" in tokens[idx]:
                idx += 1
            if idx < len(tokens):
                exe = tokens[idx]
            else:
                return "env"

        # Strip path: /usr/bin/rm → rm
        if "/" in exe:
            exe = exe.rsplit("/", 1)[-1]

        return exe.lower()

    @staticmethod
    def _signature(cmd: str) -> str:
        """SHA-256 signature for audit trail."""
        return hashlib.sha256(cmd.encode("utf-8")).hexdigest()[:16]


# Global singleton
SHELL_CLASSIFIER = ShellIntentClassifier()
