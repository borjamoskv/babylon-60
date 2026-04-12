"""Pluggable execution backends for continual-learning micro-updates."""

from __future__ import annotations

import hashlib
import json
import math
import os
import shlex
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from cortex.extensions.continual_learning.models import (
    ExperienceRecord,
    MicroUpdateBackend,
    MicroUpdateBackendResult,
    MicroUpdatePlan,
)

__all__ = ["MLXLoRABackend", "SubprocessScoreProvider", "build_backend_from_env"]

ScoreProvider = Callable[[MicroUpdatePlan, str], tuple[dict[str, float], dict[str, float]]]
ExampleFormatter = Callable[[ExperienceRecord], dict[str, Any]]

_TRUTHY_ENV_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSY_ENV_VALUES = frozenset({"0", "false", "no", "off"})


def _default_example_formatter(example: ExperienceRecord) -> dict[str, Any]:
    """Convert an experience into a minimally supervised ShareGPT-like example."""
    target = example.feedback or _first_string_value(
        example.metadata,
        "target",
        "target_text",
        "assistant_response",
        "response",
        "label",
    )
    if target is None:
        raise ValueError(
            "MLXLoRABackend requires supervised targets in feedback or metadata "
            "('target', 'target_text', 'assistant_response', 'response', 'label')"
        )
    return {
        "messages": [
            {"role": "user", "content": example.text},
            {"role": "assistant", "content": target},
        ]
    }


def _first_string_value(payload: dict[str, Any], *keys: str) -> str | None:
    """Return the first non-blank string value present in ``payload``."""
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _json_default(value: Any) -> Any:
    """Serialize non-JSON primitives into deterministic string fallbacks."""
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _normalize_score_map(name: str, value: Any) -> dict[str, float]:
    """Validate a score mapping emitted by an external scorer."""
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{name} must be a non-empty mapping of domain -> float")

    normalized: dict[str, float] = {}
    for raw_key, raw_score in value.items():
        if not isinstance(raw_key, str) or not raw_key.strip():
            raise ValueError(f"{name} keys must be non-blank strings")
        try:
            score = float(raw_score)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name}[{raw_key!r}] must be numeric") from exc
        if not math.isfinite(score):
            raise ValueError(f"{name}[{raw_key!r}] must be finite")
        normalized[raw_key.strip()] = score
    return normalized


def _parse_env_bool(raw_value: str | None, *, name: str, default: bool = False) -> bool:
    """Parse a strict boolean environment variable."""
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in _TRUTHY_ENV_VALUES:
        return True
    if normalized in _FALSY_ENV_VALUES:
        return False
    raise ValueError(f"{name} must be one of {_TRUTHY_ENV_VALUES | _FALSY_ENV_VALUES}")


def _parse_env_int(
    raw_value: str | None,
    *,
    name: str,
    default: int,
    min_value: int = 1,
) -> int:
    """Parse a positive integer environment variable."""
    if raw_value is None:
        return default
    try:
        parsed = int(raw_value.strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if parsed < min_value:
        raise ValueError(f"{name} must be >= {min_value}")
    return parsed


class SubprocessScoreProvider:
    """Invoke an external scorer over JSON stdin and validate the returned scores."""

    def __init__(
        self,
        *,
        command: str | Sequence[str],
        timeout_s: int = 300,
        cwd: str | Path | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        if isinstance(command, str):
            parsed_command = tuple(shlex.split(command))
        else:
            parsed_command = tuple(str(part).strip() for part in command if str(part).strip())
        if not parsed_command:
            raise ValueError("command must be non-empty")
        if timeout_s <= 0:
            raise ValueError("timeout_s must be > 0")

        self._command = parsed_command
        self._timeout_s = timeout_s
        self._cwd = Path(cwd).expanduser() if cwd is not None else None
        self._env = dict(env) if env is not None else None

    def __call__(
        self,
        plan: MicroUpdatePlan,
        artifact_path: str,
    ) -> tuple[dict[str, float], dict[str, float]]:
        """Return before/after score mappings emitted by the configured subprocess."""
        payload = {
            "artifact_path": artifact_path,
            "plan": asdict(plan),
        }
        process = subprocess.run(
            list(self._command),
            input=json.dumps(payload, ensure_ascii=True, sort_keys=True, default=_json_default),
            capture_output=True,
            text=True,
            timeout=self._timeout_s,
            check=False,
            cwd=str(self._cwd) if self._cwd is not None else None,
            env=self._env,
        )
        if process.returncode != 0:
            raise RuntimeError(
                "score provider failed with return code "
                f"{process.returncode}: {process.stderr[-500:]}"
            )

        try:
            output = json.loads(process.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("score provider returned invalid JSON") from exc

        before_scores = _normalize_score_map("before_scores", output.get("before_scores"))
        after_scores = _normalize_score_map("after_scores", output.get("after_scores"))
        return before_scores, after_scores


class MLXLoRABackend:
    """Subprocess-backed MLX LoRA trainer for sidecar execution outside the core loop."""

    def __init__(
        self,
        *,
        work_dir: str | Path,
        score_provider: ScoreProvider,
        base_model: str,
        python_executable: str = "python",
        command_timeout_s: int = 600,
        iters: int = 100,
        batch_size: int = 2,
        lora_layers: int = 8,
        dry_run: bool = False,
        example_formatter: ExampleFormatter | None = None,
    ) -> None:
        self._work_dir = Path(work_dir).expanduser()
        self._work_dir.mkdir(parents=True, exist_ok=True)
        self._score_provider = score_provider
        self._base_model = base_model.strip()
        self._python_executable = python_executable.strip()
        self._command_timeout_s = int(command_timeout_s)
        self._iters = int(iters)
        self._batch_size = int(batch_size)
        self._lora_layers = int(lora_layers)
        self._dry_run = dry_run
        self._example_formatter = example_formatter or _default_example_formatter

        if not self._base_model:
            raise ValueError("base_model must be non-blank")
        if not self._python_executable:
            raise ValueError("python_executable must be non-blank")
        if self._command_timeout_s <= 0:
            raise ValueError("command_timeout_s must be > 0")
        if self._iters <= 0:
            raise ValueError("iters must be > 0")
        if self._batch_size <= 0:
            raise ValueError("batch_size must be > 0")
        if self._lora_layers <= 0:
            raise ValueError("lora_layers must be > 0")

    def execute(self, plan: MicroUpdatePlan) -> MicroUpdateBackendResult:
        """Materialize the rehearsal batch, optionally run MLX LoRA, and return scored outputs."""
        run_dir = self._work_dir / f"{plan.tenant_id}_{plan.domain}_{int(time.time() * 1000)}"
        run_dir.mkdir(parents=True, exist_ok=True)

        dataset_path = run_dir / "train.jsonl"
        self._write_dataset(dataset_path, plan.batch.all_examples)
        adapter_dir = run_dir / "adapter"
        adapter_dir.mkdir(parents=True, exist_ok=True)

        command = [
            self._python_executable,
            "-m",
            "mlx_lm.lora",
            "--model",
            self._base_model,
            "--data",
            str(run_dir),
            "--adapter-path",
            str(adapter_dir),
            "--iters",
            str(self._iters),
            "--batch-size",
            str(self._batch_size),
            "--lora-layers",
            str(self._lora_layers),
        ]
        command_result: dict[str, Any] = {"command": command, "dataset_path": str(dataset_path)}
        if not self._dry_run:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self._command_timeout_s,
                check=False,
            )
            command_result["returncode"] = process.returncode
            command_result["stdout_tail"] = process.stdout[-500:]
            command_result["stderr_tail"] = process.stderr[-500:]
            if process.returncode != 0:
                raise RuntimeError(
                    "MLX LoRA training failed with return code "
                    f"{process.returncode}: {process.stderr[-500:]}"
                )
        else:
            command_result["dry_run"] = True

        before_scores, after_scores = self._score_provider(plan, str(adapter_dir))
        return MicroUpdateBackendResult(
            adapter_id=plan.adapter_id,
            before_scores=before_scores,
            after_scores=after_scores,
            training_metrics={
                "learning_rate": plan.learning_rate,
                "risk_score": plan.risk_score,
                "batch_size": float(plan.batch.size),
                "new_examples": float(len(plan.batch.new_examples)),
                "anchor_examples": float(len(plan.batch.anchor_examples)),
                "prototype_examples": float(len(plan.batch.prototype_examples)),
            },
            baseline_embeddings=tuple(example.embedding for example in plan.batch.anchor_examples),
            current_embeddings=tuple(example.embedding for example in plan.batch.new_examples),
            artifact_path=str(adapter_dir),
            data_fingerprint=self._fingerprint(plan),
            backend_name="mlx_lora",
            snapshot_reason="post_mlx_micro_update",
            metadata=command_result,
        )

    def _write_dataset(self, dataset_path: Path, examples: Sequence[ExperienceRecord]) -> None:
        """Persist the rehearsal batch as JSONL for MLX-LM consumption."""
        if not examples:
            raise ValueError("cannot execute MLX LoRA backend without examples")
        with dataset_path.open("w", encoding="utf-8") as handle:
            for example in examples:
                payload = self._example_formatter(example)
                handle.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def _fingerprint(self, plan: MicroUpdatePlan) -> str:
        """Build a stable fingerprint for the exact training batch and risk settings."""
        digest = hashlib.sha3_256()
        digest.update(plan.adapter_id.encode("utf-8"))
        digest.update(str(plan.learning_rate).encode("utf-8"))
        digest.update(str(plan.risk_score).encode("utf-8"))
        for example in plan.batch.all_examples:
            digest.update(example.id.encode("utf-8"))
            digest.update(example.semantic_hash.encode("utf-8"))
        return digest.hexdigest()


def build_backend_from_env(
    *,
    env: dict[str, str] | None = None,
    cortex_dir: str | Path | None = None,
) -> MicroUpdateBackend | None:
    """Build a continual-learning execution backend from explicit environment variables."""
    env_map = dict(os.environ) if env is None else dict(env)
    backend_name = env_map.get("CORTEX_CONTINUAL_LEARNING_BACKEND", "").strip().lower()
    if not backend_name:
        return None

    if backend_name != "mlx":
        raise ValueError(f"unsupported continual-learning backend: {backend_name}")

    base_model = env_map.get("CORTEX_CONTINUAL_LEARNING_BASE_MODEL", "").strip()
    if not base_model:
        raise ValueError(
            "CORTEX_CONTINUAL_LEARNING_BASE_MODEL is required when "
            "CORTEX_CONTINUAL_LEARNING_BACKEND=mlx"
        )

    score_command = env_map.get("CORTEX_CONTINUAL_LEARNING_SCORE_COMMAND", "").strip()
    if not score_command:
        raise ValueError(
            "CORTEX_CONTINUAL_LEARNING_SCORE_COMMAND is required when "
            "CORTEX_CONTINUAL_LEARNING_BACKEND=mlx"
        )

    base_dir = Path(cortex_dir).expanduser() if cortex_dir is not None else Path.cwd()
    work_dir = Path(
        env_map.get(
            "CORTEX_CONTINUAL_LEARNING_WORK_DIR",
            str(base_dir / "continual_learning_runs"),
        )
    ).expanduser()

    scorer = SubprocessScoreProvider(
        command=score_command,
        timeout_s=_parse_env_int(
            env_map.get("CORTEX_CONTINUAL_LEARNING_SCORE_TIMEOUT_S"),
            name="CORTEX_CONTINUAL_LEARNING_SCORE_TIMEOUT_S",
            default=300,
        ),
        cwd=work_dir,
    )

    return MLXLoRABackend(
        work_dir=work_dir,
        score_provider=scorer,
        base_model=base_model,
        python_executable=env_map.get("CORTEX_CONTINUAL_LEARNING_PYTHON", "python"),
        command_timeout_s=_parse_env_int(
            env_map.get("CORTEX_CONTINUAL_LEARNING_TRAIN_TIMEOUT_S"),
            name="CORTEX_CONTINUAL_LEARNING_TRAIN_TIMEOUT_S",
            default=600,
        ),
        iters=_parse_env_int(
            env_map.get("CORTEX_CONTINUAL_LEARNING_ITERS"),
            name="CORTEX_CONTINUAL_LEARNING_ITERS",
            default=100,
        ),
        batch_size=_parse_env_int(
            env_map.get("CORTEX_CONTINUAL_LEARNING_BATCH_SIZE"),
            name="CORTEX_CONTINUAL_LEARNING_BATCH_SIZE",
            default=2,
        ),
        lora_layers=_parse_env_int(
            env_map.get("CORTEX_CONTINUAL_LEARNING_LORA_LAYERS"),
            name="CORTEX_CONTINUAL_LEARNING_LORA_LAYERS",
            default=8,
        ),
        dry_run=_parse_env_bool(
            env_map.get("CORTEX_CONTINUAL_LEARNING_DRY_RUN"),
            name="CORTEX_CONTINUAL_LEARNING_DRY_RUN",
            default=False,
        ),
    )
