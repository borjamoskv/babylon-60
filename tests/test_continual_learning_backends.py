"""Tests for continual-learning execution backends."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from cortex.extensions.continual_learning import (
    MicroUpdatePlan,
    MixedBatch,
    MLXLoRABackend,
    SubprocessScoreProvider,
    build_backend_from_env,
)
from cortex.extensions.continual_learning.models import ExperienceRecord


def _example(
    *, metadata: dict[str, object] | None = None, feedback: str | None = None
) -> ExperienceRecord:
    """Create a small supervised experience for backend tests."""
    return ExperienceRecord(
        id="exp-1",
        tenant_id="tenant-a",
        user_id="user-1",
        ts=1.0,
        domain="support",
        intent="answer",
        text="Reset my password",
        confidence=0.9,
        priority=0.9,
        feedback=feedback,
        embedding=(1.0, 2.0),
        semantic_hash="hash-1",
        ttl_deadline=10.0,
        trace_id="trace-1",
        metadata=metadata or {},
    )


def test_mlx_lora_backend_dry_run_writes_dataset_and_returns_scores(tmp_path: Path) -> None:
    plan = MicroUpdatePlan(
        tenant_id="tenant-a",
        domain="support",
        adapter_id="lora:test",
        learning_rate=5e-5,
        risk_score=0.2,
        batch=MixedBatch(new_examples=(_example(feedback="Use the reset flow"),)),
    )
    backend = MLXLoRABackend(
        work_dir=tmp_path,
        base_model="mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
        dry_run=True,
        score_provider=lambda current_plan, artifact_path: (
            {"support": 0.8},
            {"support": 0.84},
        ),
    )

    result = backend.execute(plan)

    dataset_path = Path(result.metadata["dataset_path"])
    assert result.backend_name == "mlx_lora"
    assert result.artifact_path
    assert dataset_path.exists()
    lines = dataset_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["messages"][0]["content"] == "Reset my password"
    assert payload["messages"][1]["content"] == "Use the reset flow"


def test_mlx_lora_backend_requires_supervised_target(tmp_path: Path) -> None:
    plan = MicroUpdatePlan(
        tenant_id="tenant-a",
        domain="support",
        adapter_id="lora:test",
        learning_rate=5e-5,
        risk_score=0.2,
        batch=MixedBatch(new_examples=(_example(),)),
    )
    backend = MLXLoRABackend(
        work_dir=tmp_path,
        base_model="mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
        dry_run=True,
        score_provider=lambda current_plan, artifact_path: (
            {"support": 0.8},
            {"support": 0.84},
        ),
    )

    with pytest.raises(ValueError, match="requires supervised targets"):
        backend.execute(plan)


def test_subprocess_score_provider_reads_json_contract(tmp_path: Path) -> None:
    score_script = tmp_path / "score.py"
    score_script.write_text(
        "\n".join(
            [
                "import json",
                "import sys",
                "payload = json.load(sys.stdin)",
                "assert payload['plan']['domain'] == 'support'",
                "print(json.dumps({'before_scores': {'support': 0.8}, 'after_scores': {'support': 0.84}}))",
            ]
        ),
        encoding="utf-8",
    )
    provider = SubprocessScoreProvider(
        command=[sys.executable, str(score_script)],
        timeout_s=10,
        cwd=tmp_path,
    )
    plan = MicroUpdatePlan(
        tenant_id="tenant-a",
        domain="support",
        adapter_id="lora:test",
        learning_rate=5e-5,
        risk_score=0.2,
        batch=MixedBatch(new_examples=(_example(feedback="Use the reset flow"),)),
    )

    before_scores, after_scores = provider(plan, str(tmp_path / "adapter"))

    assert before_scores == {"support": 0.8}
    assert after_scores == {"support": 0.84}


def test_build_backend_from_env_requires_score_command(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="SCORE_COMMAND"):
        build_backend_from_env(
            env={
                "CORTEX_CONTINUAL_LEARNING_BACKEND": "mlx",
                "CORTEX_CONTINUAL_LEARNING_BASE_MODEL": "mlx-community/test-model",
            },
            cortex_dir=tmp_path,
        )


def test_build_backend_from_env_builds_mlx_backend(tmp_path: Path) -> None:
    backend = build_backend_from_env(
        env={
            "CORTEX_CONTINUAL_LEARNING_BACKEND": "mlx",
            "CORTEX_CONTINUAL_LEARNING_BASE_MODEL": "mlx-community/test-model",
            "CORTEX_CONTINUAL_LEARNING_SCORE_COMMAND": f"{sys.executable} -c \"print('ok')\"",
            "CORTEX_CONTINUAL_LEARNING_WORK_DIR": str(tmp_path / "runs"),
            "CORTEX_CONTINUAL_LEARNING_DRY_RUN": "1",
        },
        cortex_dir=tmp_path,
    )

    assert isinstance(backend, MLXLoRABackend)
