import pytest
import asyncio
from pathlib import Path
from cortex.integration.telemetry import AgentTelemetryEmitter, compute_agent_fingerprint

@pytest.mark.asyncio
async def test_telemetry_emits_valid_event(tmp_path):
    emitted = []
    async def mock_publish(event_dict):
        emitted.append(event_dict)
    
    emitter = AgentTelemetryEmitter(
        agent_id="cortex-001",
        modules_dir=tmp_path,
        schema_paths=[],
        capability_manifest={"schema_version": "1.0", "routes": {}},
        publish=mock_publish,
        interval_s=0.1
    )
    
    event = await emitter.emit_once()
    assert event.agent_id == "cortex-001"
    assert len(emitted) == 1
    assert emitted[0]["agent_id"] == "cortex-001"

def test_fingerprint_determinism(tmp_path):
    fp1 = compute_agent_fingerprint("agent-1", tmp_path, [], {"caps": "test"})
    fp2 = compute_agent_fingerprint("agent-1", tmp_path, [], {"caps": "test"})
    assert fp1 == fp2
