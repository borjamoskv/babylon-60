"""MOSKVBot execution runtime."""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

from cortex.extensions.moskvbot.git import GitClient, git_worktree
from cortex.extensions.moskvbot.models import (
    CloudExecutionUnavailable,
    CommandResult,
    CommandSpec,
    ExecutionBackend,
    MissionPlan,
    MissionResult,
    MissionStatus,
)


class LocalCommandRunner:
    """Runs commands without a shell inside an isolated workspace."""

    async def run(self, command: CommandSpec, workspace: Path) -> CommandResult:
        """Execute one command and capture bounded output."""
        cwd = self._resolve_cwd(workspace, command.cwd)
        start = time.monotonic()
        env = os.environ.copy()
        env.setdefault("CORTEX_SOURCE", "agent:moskvbot")
        env.setdefault("CORTEX_TENANT_ID", "local-tenant")

        try:
            process = await asyncio.create_subprocess_exec(
                *command.argv,
                cwd=str(cwd),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            duration_s = time.monotonic() - start
            return CommandResult(
                command=command,
                cwd=cwd,
                return_code=-1,
                stdout="",
                stderr=self._clean_output(str(exc), command),
                duration_s=duration_s,
            )
        timed_out = False
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=command.timeout_s,
            )
        except asyncio.TimeoutError:
            timed_out = True
            process.kill()
            stdout_bytes, stderr_bytes = await process.communicate()

        duration_s = time.monotonic() - start
        return CommandResult(
            command=command,
            cwd=cwd,
            return_code=process.returncode if process.returncode is not None else -1,
            stdout=self._clean_output(stdout_bytes.decode(errors="replace"), command),
            stderr=self._clean_output(stderr_bytes.decode(errors="replace"), command),
            duration_s=duration_s,
            timed_out=timed_out,
        )

    def _resolve_cwd(self, workspace: Path, relative_cwd: str | None) -> Path:
        root = workspace.resolve()
        cwd = root if relative_cwd is None else (root / relative_cwd).resolve()
        if not cwd.is_relative_to(root):
            raise ValueError(f"Command cwd escapes workspace: {relative_cwd}")
        return cwd

    def _clean_output(self, text: str, command: CommandSpec) -> str:
        cleaned = text[-8000:]
        for secret in command.redact:
            if secret:
                cleaned = cleaned.replace(secret, "[REDACTED]")
        return cleaned


class MOSKVBot:
    """Executes MOSKVBot plans in isolated worktrees."""

    def __init__(self, repo_path: str | Path = ".") -> None:
        self.repo_path = Path(repo_path).expanduser().resolve()
        self.command_runner = LocalCommandRunner()

    async def run(
        self,
        plan: MissionPlan,
        *,
        parallelism: int = 2,
        keep_worktree: bool = True,
        commit: bool = False,
        commit_message: str | None = None,
        worktree_base_path: str | Path | None = None,
    ) -> MissionResult:
        """Run worker commands, validation commands, and optional Git commit."""
        if plan.backend == ExecutionBackend.CLOUD_ISOLATED:
            raise CloudExecutionUnavailable(
                "cloud-isolated backend requires a configured MOSKVBot cloud adapter"
            )
        if parallelism < 1:
            raise ValueError("parallelism must be at least 1")

        command_results: list[CommandResult] = []
        validation_results: list[CommandResult] = []
        errors: list[str] = []
        commit_sha: str | None = None
        changed_files: tuple[str, ...] = ()
        git = GitClient(plan.repo_path)

        with git_worktree(
            plan.repo_path,
            branch_name=plan.branch_name,
            base_path=worktree_base_path,
            keep=keep_worktree,
            delete_branch_on_cleanup=not commit,
        ) as worktree_path:
            semaphore = asyncio.Semaphore(parallelism)

            async def run_worker_commands(worker_index: int) -> list[CommandResult]:
                worker = plan.workers[worker_index]
                worker_results: list[CommandResult] = []
                async with semaphore:
                    for command in worker.commands:
                        result = await self.command_runner.run(command, worktree_path)
                        worker_results.append(result)
                        if not result.ok:
                            break
                return worker_results

            worker_batches = await asyncio.gather(
                *(run_worker_commands(index) for index in range(len(plan.workers)))
            )
            for batch in worker_batches:
                command_results.extend(batch)
            errors.extend(self._errors_from_results(command_results, "worker"))

            if not errors:
                for command in plan.validation_commands:
                    result = await self.command_runner.run(command, worktree_path)
                    validation_results.append(result)
                    if not result.ok:
                        break
                errors.extend(self._errors_from_results(validation_results, "validation"))

            changed_files = git.dirty_files(cwd=worktree_path)
            if commit and not errors:
                message = commit_message or f"MOSKVBot mission: {plan.goal}"
                commit_sha = git.commit_all(worktree_path, message)

            status = MissionStatus.COMPLETED if not errors else MissionStatus.FAILED
            return MissionResult(
                mission_id=plan.mission_id,
                status=status,
                worktree_path=worktree_path if keep_worktree else None,
                branch_name=plan.branch_name,
                command_results=tuple(command_results),
                validation_results=tuple(validation_results),
                changed_files=changed_files,
                commit_sha=commit_sha,
                errors=tuple(errors),
            )

    def _errors_from_results(self, results: list[CommandResult], phase: str) -> list[str]:
        errors: list[str] = []
        for result in results:
            if result.ok:
                continue
            if result.timed_out:
                errors.append(f"{phase} command timed out: {result.command.display}")
            else:
                errors.append(
                    f"{phase} command failed ({result.return_code}): {result.command.display}"
                )
        return errors
