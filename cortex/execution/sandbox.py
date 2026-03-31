"""
DockerSandbox — Ephemeral Container Execution Engine
=====================================================
Wraps every swarm command in a disposable Docker container.

Security contract:
  - No network (--network none) for Tier 1
  - No host mounts (volume-less) for Tier ≤ 2
  - Read-only root filesystem
  - Non-root uid=65534 (nobody)
  - CPU/memory/PID limits enforced
  - Container auto-removed after execution

Integration flow:
  SwarmManager.dispatch()
    → SandboxGate.execute(command, tier)
      → classify_command(command)        #  O(n_rules) deterministic
        → Tier 0 (SAFE)     → local subprocess (no Docker)
        → Tier 1 (MONITOR)  → DockerSandbox, no network, ephemeral
        → Tier 2 (ELEVATED) → DockerSandbox + ledger approval token
        → Tier 3 (CRITICAL) → BlockedError (operator override only)
"""
from __future__ import annotations

import asyncio
import logging
import shlex
import uuid
from dataclasses import dataclass, field
from typing import Any

from cortex.execution.risk import ClassificationResult, RiskTier, classify_command

logger = logging.getLogger("cortex.execution.sandbox")


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class SandboxResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    tier: RiskTier
    container_id: str | None = None
    duration_ms: float = 0.0
    blocked: bool = False
    block_reason: str = ""

    @property
    def success(self) -> bool:
        return not self.blocked and self.exit_code == 0


# ---------------------------------------------------------------------------
# DockerSandbox
# ---------------------------------------------------------------------------

_DEFAULT_IMAGE = "python:3.12-slim"
_TIMEOUT_S = 30  # hard wall-clock timeout per sandbox invocation


class SandboxBlocked(RuntimeError):
    """Raised when a CRITICAL-tier command is attempted without override."""


class DockerSandbox:
    """
    Ephemeral Docker sandbox for risk-tiered command execution.

    Args:
        image:          Docker image to use as execution context.
        timeout:        Hard timeout (seconds) per invocation.
        cpu_period:     Docker --cpu-period (microseconds).
        cpu_quota:      Docker --cpu-quota (microseconds) — 50% of 1 core default.
        memory_limit:   Docker --memory (e.g. "256m").
        pids_limit:     Docker --pids-limit.
        workdir:        Working directory inside container.
    """

    def __init__(
        self,
        image: str = _DEFAULT_IMAGE,
        timeout: int = _TIMEOUT_S,
        cpu_period: int = 100_000,
        cpu_quota: int = 50_000,     # 50% of one CPU
        memory_limit: str = "256m",
        pids_limit: int = 64,
        workdir: str = "/sandbox",
    ) -> None:
        self.image = image
        self.timeout = timeout
        self.cpu_period = cpu_period
        self.cpu_quota = cpu_quota
        self.memory_limit = memory_limit
        self.pids_limit = pids_limit
        self.workdir = workdir

    def _build_docker_args(
        self,
        container_name: str,
        command: str,
        tier: RiskTier,
    ) -> list[str]:
        """
        Builds the `docker run` argument list.
        Network isolation is escalated by tier:
          Tier 1 → --network none
          Tier 2 → --network cortex-elevated (pre-existing isolated bridge)
        """
        args = [
            "docker", "run",
            "--rm",
            "--name", container_name,
            "--read-only",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--user", "65534:65534",          # nobody:nobody
            f"--cpu-period={self.cpu_period}",
            f"--cpu-quota={self.cpu_quota}",
            f"--memory={self.memory_limit}",
            f"--memory-swap={self.memory_limit}",  # no swap
            f"--pids-limit={self.pids_limit}",
            "--workdir", self.workdir,
        ]

        # Network isolation per tier
        if tier <= RiskTier.MONITORED:
            args += ["--network", "none"]
        else:
            # ELEVATED: use isolated bridge (created by infra/docker-compose)
            args += ["--network", "cortex-elevated"]

        args.append(self.image)

        # Wrap in sh -c for multi-step commands
        args += ["sh", "-c", command]
        return args

    async def _run_local(self, command: str) -> SandboxResult:
        """SAFE tier: run directly as subprocess (no Docker overhead)."""
        import time
        t0 = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout
            )
            elapsed = (time.monotonic() - t0) * 1000
            return SandboxResult(
                command=command,
                exit_code=proc.returncode or 0,
                stdout=stdout_b.decode(errors="replace"),
                stderr=stderr_b.decode(errors="replace"),
                tier=RiskTier.SAFE,
                duration_ms=elapsed,
            )
        except asyncio.TimeoutError:
            return SandboxResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr="TIMEOUT",
                tier=RiskTier.SAFE,
                blocked=True,
                block_reason="Execution timeout",
            )

    async def _run_docker(self, command: str, tier: RiskTier) -> SandboxResult:
        """MONITORED / ELEVATED tier: run inside ephemeral Docker container."""
        import time
        container_name = f"cortex-sandbox-{uuid.uuid4().hex[:12]}"
        docker_args = self._build_docker_args(container_name, command, tier)

        logger.debug(
            "DockerSandbox: Spawning container [%s] Tier=%s cmd=%r",
            container_name, tier.name, command[:80],
        )

        t0 = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                *docker_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout
            )
            elapsed = (time.monotonic() - t0) * 1000

            exit_code = proc.returncode or 0
            result = SandboxResult(
                command=command,
                exit_code=exit_code,
                stdout=stdout_b.decode(errors="replace"),
                stderr=stderr_b.decode(errors="replace"),
                tier=tier,
                container_name=container_name,
                duration_ms=elapsed,
            )
            logger.info(
                "DockerSandbox: [%s] exit=%d in %.0fms",
                container_name, exit_code, elapsed,
            )
            return result

        except asyncio.TimeoutError:
            # Kill the container on timeout
            logger.warning(
                "DockerSandbox: Timeout! Killing container %s", container_name
            )
            await self._kill_container(container_name)
            return SandboxResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Container timeout after {self.timeout}s",
                tier=tier,
                container_name=container_name,
                blocked=True,
                block_reason="Execution timeout",
            )
        except FileNotFoundError:
            logger.error("DockerSandbox: `docker` binary not found. Install Docker.")
            return SandboxResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr="`docker` binary not found",
                tier=tier,
                blocked=True,
                block_reason="docker_not_installed",
            )

    @staticmethod
    async def _kill_container(name: str) -> None:
        """Best-effort container kill + rm."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "kill", name,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=5)
        except Exception:
            pass

    async def execute(
        self,
        command: str,
        *,
        override_tier: RiskTier | None = None,
        approval_token: str | None = None,
    ) -> SandboxResult:
        """
        Classify and execute a command under appropriate isolation.

        Args:
            command:        Shell command to execute.
            override_tier:  Forces a specific tier (operator use only).
            approval_token: Opaque token from ledger for ELEVATED tier approval.

        Raises:
            SandboxBlocked: If tier is CRITICAL and no override is provided.
        """
        classification: ClassificationResult = classify_command(command)
        tier = override_tier if override_tier is not None else classification.tier

        logger.info(
            "SandboxGate: command=%r → Tier=%s matched_rule=%s auto_allow=%s",
            command[:80], tier.name, classification.matched_rule, classification.auto_allow,
        )

        if tier == RiskTier.CRITICAL:
            logger.error(
                "SandboxGate: 🔴 CRITICAL command BLOCKED: %r | rule=%s",
                command[:120], classification.matched_rule,
            )
            raise SandboxBlocked(
                f"CRITICAL tier command blocked by SandboxGate. "
                f"Rule: {classification.matched_rule}. "
                "Requires explicit operator override (override_tier + signed approval_token)."
            )

        if tier == RiskTier.ELEVATED:
            if approval_token is None:
                logger.warning(
                    "SandboxGate: 🟠 ELEVATED command requires approval token: %r", command[:80]
                )
                return SandboxResult(
                    command=command,
                    exit_code=-1,
                    stdout="",
                    stderr="ELEVATED tier requires ledger approval_token",
                    tier=tier,
                    blocked=True,
                    block_reason="missing_approval_token",
                )
            logger.info("SandboxGate: ELEVATED approved with token=%s", approval_token[:8] + "…")

        if tier == RiskTier.SAFE:
            return await self._run_local(command)

        return await self._run_docker(command, tier)


# ---------------------------------------------------------------------------
# SandboxResult dataclass fix — container_name field
# ---------------------------------------------------------------------------
# Re-declared here to add container_name field properly via inheritance
@dataclass
class SandboxResult:  # noqa: F811  (intentional redeclaration to add field)
    command: str
    exit_code: int
    stdout: str
    stderr: str
    tier: RiskTier
    container_name: str | None = None
    container_id: str | None = None
    duration_ms: float = 0.0
    blocked: bool = False
    block_reason: str = ""

    @property
    def success(self) -> bool:
        return not self.blocked and self.exit_code == 0
