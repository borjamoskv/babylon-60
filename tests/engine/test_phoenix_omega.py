from __future__ import annotations

from pathlib import Path

import pytest

from cortex.engine.phoenix_omega import (
    AnalysisEngine,
    AtomicPhase,
    BPOExtractionEngine,
    PhaseStatus,
    PhoenixOrchestrator,
    PhoenixState,
)
from cortex.extensions.evolution.phoenix_omega import (
    PhoenixOrchestrator as ExtensionPhoenixOrchestrator,
)


def _initial_state() -> PhoenixState:
    """Build a clean Phoenix state for unit tests."""

    return PhoenixState(
        phase=AtomicPhase.ANALYSIS,
        status=PhaseStatus.PENDING,
        atoms={},
        artifacts={},
        metrics={},
    )


def _write_sample_module(root: Path) -> Path:
    """Create a Python module with enough structure to exercise the pipeline."""

    sample = root / "sample.py"
    sample.write_text(
        "import requests\n"
        "\n"
        "def helper(balance: int) -> int:\n"
        "    return balance + 1\n"
        "\n"
        "async def worker(price: int) -> int:\n"
        "    requests.get('https://example.invalid')\n"
        "    total = 0\n"
        "    for bid in [price]:\n"
        "        total += helper(bid)\n"
        "    return total\n"
        "\n"
        "class Processor:\n"
        "    def __init__(self, balance: int) -> None:\n"
        "        self.balance = balance\n",
        encoding="utf-8",
    )
    return sample


@pytest.mark.asyncio
async def test_analysis_engine_collects_atoms_and_bpo_patterns(tmp_path: Path) -> None:
    sample = _write_sample_module(tmp_path)

    state = await AnalysisEngine().execute(_initial_state(), [sample])

    assert state.status == PhaseStatus.COMPLETED
    assert state.phase == AtomicPhase.ANALYSIS
    assert set(state.atoms) >= {
        "sample::helper",
        "sample::worker",
        "sample::Processor",
        "sample::__init__",
    }
    assert state.metrics["total_atoms"] >= 4.0
    assert "sample::worker" in state.artifacts["bpo_metadata"]
    assert "NETWORK_IO" in state.artifacts["bpo_metadata"]["sample::worker"]
    assert "TRANSACTIONAL_LOOP" in state.artifacts["bpo_metadata"]["sample::worker"]
    assert "sample::worker" in state.artifacts["coupling_graph"]["sample::helper"]["in"]


@pytest.mark.asyncio
async def test_bpo_extraction_engine_adds_priority_interface(tmp_path: Path) -> None:
    sample = _write_sample_module(tmp_path)
    analyzed_state = await AnalysisEngine().execute(_initial_state(), [sample])

    extracted_state = await BPOExtractionEngine().execute(analyzed_state)

    plan_by_id = {entry["atom_id"]: entry for entry in extracted_state.artifacts["extraction_plan"]}
    worker_plan = plan_by_id["sample::worker"]

    assert extracted_state.phase == AtomicPhase.EXTRACTION
    assert extracted_state.status == PhaseStatus.COMPLETED
    assert worker_plan["priority"] == "HIGH"
    assert worker_plan["interface"]["name"] == "Iworker"
    assert worker_plan["interface"]["args"] == ["price"]
    assert worker_plan["interface"]["is_async"] is True


@pytest.mark.asyncio
async def test_orchestrator_ignite_runs_full_cycle_for_directory(tmp_path: Path) -> None:
    _write_sample_module(tmp_path)

    final_state = await PhoenixOrchestrator().ignite([tmp_path])

    assert final_state.phase == AtomicPhase.VERIFICATION
    assert final_state.status == PhaseStatus.COMPLETED
    assert "verification_report" in final_state.artifacts
    assert "extraction_plan" in final_state.artifacts
    assert "scaling_plan" in final_state.artifacts
    assert final_state.metrics["verification_score"] == 100.0


def test_extension_wrapper_reexports_core_orchestrator() -> None:
    assert ExtensionPhoenixOrchestrator is PhoenixOrchestrator
