from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from .jit_bridge import JITBridgeCompiler
from .morph_registry import MorphRegistry
from .telemetry import AgentTelemetryEmitter
from .verifier import IntegrationVerifier


async def _noop_publish(event: dict):
    out = Path("output")
    out.mkdir(exist_ok=True)
    p = out / "telemetry_event.json"
    p.write_text(json.dumps(event, indent=2, sort_keys=True), encoding="utf-8")


async def cmd_emit(args):
    emitter = AgentTelemetryEmitter(
        agent_id=args.agent_id,
        modules_dir=Path(args.modules_dir),
        schema_paths=[Path(p) for p in args.schema_paths],
        capability_manifest=json.loads(Path(args.capabilities).read_text()),
        publish=_noop_publish,
        interval_s=args.interval,
    )
    await emitter.emit_once()


async def cmd_snapshot(args):
    registry = MorphRegistry()
    agents_md = Path(args.agents_md).read_text(encoding="utf-8")
    contracts = json.loads(Path(args.contracts).read_text(encoding="utf-8"))
    snapshot = registry.record_snapshot(agents_md, contracts)
    out = Path("output")
    out.mkdir(exist_ok=True)
    (out / "morph_snapshot.json").write_text(
        json.dumps(snapshot.__dict__, indent=2, sort_keys=True), encoding="utf-8"
    )


async def cmd_bridge(args):
    compiler = JITBridgeCompiler(output_dir=Path("output/bridges"))
    expected = json.loads(Path(args.expected).read_text())
    actual = json.loads(Path(args.actual).read_text())
    artifact = compiler.compile_bridge(args.agent_id, expected, actual)
    Path("output").mkdir(exist_ok=True)
    Path("output/bridge_artifact.json").write_text(
        json.dumps(artifact.__dict__, indent=2, sort_keys=True),
        encoding="utf-8",
    )


async def cmd_verify(args):
    verifier = IntegrationVerifier()
    bundle = verifier.verify_telemetry_bundle(Path(args.bundle))
    print(json.dumps(bundle, indent=2, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("emit")
    p.add_argument("--agent-id", required=True)
    p.add_argument("--modules-dir", required=True)
    p.add_argument("--schema-paths", nargs="+", default=[])
    p.add_argument("--capabilities", required=True)
    p.add_argument("--interval", type=float, default=5.0)

    p = sub.add_parser("snapshot")
    p.add_argument("--agents-md", required=True)
    p.add_argument("--contracts", required=True)

    p = sub.add_parser("bridge")
    p.add_argument("--agent-id", required=True)
    p.add_argument("--expected", required=True)
    p.add_argument("--actual", required=True)

    p = sub.add_parser("verify")
    p.add_argument("--bundle", required=True)

    args = parser.parse_args()

    if args.cmd == "emit":
        asyncio.run(cmd_emit(args))
    elif args.cmd == "snapshot":
        asyncio.run(cmd_snapshot(args))
    elif args.cmd == "bridge":
        asyncio.run(cmd_bridge(args))
    elif args.cmd == "verify":
        asyncio.run(cmd_verify(args))


if __name__ == "__main__":
    main()
