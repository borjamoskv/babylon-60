"""Sovereign App Forge contracts for ephemeral collaborative UIs.

This module rewrites the @Q-style iframe pattern into CORTEX-native primitives:
tenant-scoped state, explicit agent context, and local vector streaming.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

from cortex.engine.models import Fact
from cortex.extensions.interfaces.engine import EngineProtocol
from cortex.guards.taint import TaintEngine

APP_FORGE_FACT_TYPE = "app:state"
APP_FORGE_RUNTIME = "sovereign-app-forge"
APP_FORGE_SOURCE = "app:forge"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _require_non_blank(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} cannot be blank")
    return normalized


def _fact_meta(raw: Fact | dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw, Fact):
        return raw.meta
    meta = raw.get("meta")
    if isinstance(meta, dict):
        return meta
    metadata = raw.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _fact_content(raw: Fact | dict[str, Any]) -> str:
    if isinstance(raw, Fact):
        return raw.content
    content = raw.get("content")
    return content if isinstance(content, str) else ""


@dataclass(frozen=True)
class AppForgeInvocation:
    """Invocation envelope for an ephemeral sovereign app."""

    intent: str
    tenant_id: str = "default"
    project_id: str = "app-forge"
    app_id: str = "ephemeral-app"
    agent_id: str = "app-forge"
    session_id: str = "runtime:app-forge"

    def __post_init__(self) -> None:
        if len(self.intent.strip()) < 8:
            raise ValueError("intent must be at least 8 characters long")
        for field_name in ("tenant_id", "project_id", "app_id", "agent_id", "session_id"):
            _require_non_blank(getattr(self, field_name), field_name)


@dataclass(frozen=True)
class AppForgeRuntimeManifest:
    """Execution contract for the local iframe-style sandbox."""

    runtime_name: str = "Azkartu Sandbox"
    render_target: str = "isolated-iframe"
    bundler: str = "esbuild-wasm"
    transport: str = "postMessage"
    state_backplane: str = "VSA-SDM"
    network_policy: str = "local-only"
    inference_policy: str = "generateVectorStream -> local model bridge"
    collaboration_scope: str = "tenant-scoped shared state"

    def to_prompt_block(self) -> str:
        return (
            "Runtime Contract:\n"
            f"- runtime: {self.runtime_name}\n"
            f"- render target: {self.render_target}\n"
            f"- bundler: {self.bundler}\n"
            f"- host bridge: {self.transport}\n"
            f"- state backplane: {self.state_backplane}\n"
            f"- network policy: {self.network_policy}\n"
            f"- inference policy: {self.inference_policy}\n"
            f"- collaboration scope: {self.collaboration_scope}"
        )


@dataclass(frozen=True)
class SovereignPrimitive:
    """LLM-facing primitive exposed by the App Forge host."""

    name: str
    summary: str
    ts_signature: str
    example: str

    def to_typescript_block(self) -> str:
        return (
            "/**\n"
            f" * {self.summary}\n"
            " * Example:\n"
            " * ```ts\n"
            f" * {self.example}\n"
            " * ```\n"
            " */\n"
            f"{self.ts_signature}\n"
        )


@dataclass(frozen=True)
class SovereignStateEnvelope:
    """Versioned tenant-scoped state snapshot for a generated app."""

    tenant_id: str
    project_id: str
    app_id: str
    state_key: str
    state_scope: str
    version: int
    value: Any
    content: str
    state_hash: str
    taint: str
    created_at: str
    agent_id: str
    session_id: str

    @classmethod
    def forge(
        cls,
        *,
        tenant_id: str,
        project_id: str,
        app_id: str,
        state_key: str,
        value: Any,
        agent_id: str,
        session_id: str,
        version: int = 1,
        state_scope: str = "shared",
        created_at: str | None = None,
    ) -> SovereignStateEnvelope:
        created = created_at or _utc_now_iso()
        payload = {
            "app_id": _require_non_blank(app_id, "app_id"),
            "created_at": created,
            "scope": _require_non_blank(state_scope, "state_scope"),
            "state_hash": TaintEngine.hash_content(_canonical_json(value)),
            "state_key": _require_non_blank(state_key, "state_key"),
            "value": value,
            "version": version,
        }
        content = _canonical_json(payload)
        taint = TaintEngine.generate_taint(
            _require_non_blank(agent_id, "agent_id"),
            _require_non_blank(session_id, "session_id"),
            content,
        )
        return cls(
            tenant_id=_require_non_blank(tenant_id, "tenant_id"),
            project_id=_require_non_blank(project_id, "project_id"),
            app_id=payload["app_id"],
            state_key=payload["state_key"],
            state_scope=payload["scope"],
            version=version,
            value=value,
            content=content,
            state_hash=payload["state_hash"],
            taint=taint,
            created_at=created,
            agent_id=agent_id,
            session_id=session_id,
        )

    @classmethod
    def from_fact(cls, raw: Fact | dict[str, Any]) -> SovereignStateEnvelope:
        meta = _fact_meta(raw)
        body = json.loads(_fact_content(raw))
        if not isinstance(body, dict):
            raise ValueError("app state content must be a JSON object")

        taint = meta.get("taint")
        if not isinstance(taint, str) or not taint.strip():
            raise ValueError("app state fact is missing CORTEX-TAINT")

        tenant_id = raw.tenant_id if isinstance(raw, Fact) else raw.get("tenant_id", "default")
        project_id = raw.project if isinstance(raw, Fact) else raw.get("project", "app-forge")
        version = body.get("version", meta.get("state_version", 1))
        if not isinstance(version, int) or version < 1:
            raise ValueError("state version must be a positive integer")

        return cls(
            tenant_id=_require_non_blank(str(tenant_id), "tenant_id"),
            project_id=_require_non_blank(str(project_id), "project_id"),
            app_id=_require_non_blank(str(body["app_id"]), "app_id"),
            state_key=_require_non_blank(str(body["state_key"]), "state_key"),
            state_scope=_require_non_blank(str(body.get("scope", "shared")), "state_scope"),
            version=version,
            value=body.get("value"),
            content=_fact_content(raw),
            state_hash=_require_non_blank(str(body["state_hash"]), "state_hash"),
            taint=taint,
            created_at=_require_non_blank(str(body["created_at"]), "created_at"),
            agent_id=_require_non_blank(str(meta.get("agent_id", APP_FORGE_RUNTIME)), "agent_id"),
            session_id=_require_non_blank(
                str(meta.get("session_id", "runtime:app-forge")), "session_id"
            ),
        )

    def verify(self) -> bool:
        expected_state_hash = TaintEngine.hash_content(_canonical_json(self.value))
        return expected_state_hash == self.state_hash and TaintEngine.verify_taint(
            self.content, self.taint
        )

    def to_fact_meta(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "app_id": self.app_id,
            "app_runtime": APP_FORGE_RUNTIME,
            "session_id": self.session_id,
            "state_hash": self.state_hash,
            "state_key": self.state_key,
            "state_scope": self.state_scope,
            "state_version": self.version,
            "taint": self.taint,
        }


@runtime_checkable
class SovereignStateStore(Protocol):
    """Persistence contract for generated app state."""

    async def write(self, envelope: SovereignStateEnvelope) -> Any: ...

    async def read(
        self,
        *,
        tenant_id: str,
        project_id: str,
        app_id: str,
        state_key: str,
    ) -> SovereignStateEnvelope | None: ...


class InMemorySovereignStateStore:
    """Test/dry-run store for App Forge state envelopes."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str, str, str], SovereignStateEnvelope] = {}

    async def write(self, envelope: SovereignStateEnvelope) -> SovereignStateEnvelope:
        self._records[self._key(envelope)] = envelope
        return envelope

    async def read(
        self,
        *,
        tenant_id: str,
        project_id: str,
        app_id: str,
        state_key: str,
    ) -> SovereignStateEnvelope | None:
        return self._records.get((tenant_id, project_id, app_id, state_key))

    @staticmethod
    def _key(envelope: SovereignStateEnvelope) -> tuple[str, str, str, str]:
        return (envelope.tenant_id, envelope.project_id, envelope.app_id, envelope.state_key)


class EngineSovereignStateStore:
    """Engine-backed persistence using the existing fact write path."""

    def __init__(self, engine: EngineProtocol) -> None:
        self._engine = engine

    async def write(self, envelope: SovereignStateEnvelope) -> int:
        return await self._engine.store(
            project=envelope.project_id,
            content=envelope.content,
            tenant_id=envelope.tenant_id,
            fact_type=APP_FORGE_FACT_TYPE,
            tags=["app-forge", envelope.state_scope],
            confidence="C4",
            source=APP_FORGE_SOURCE,
            meta=envelope.to_fact_meta(),
        )

    async def read(
        self,
        *,
        tenant_id: str,
        project_id: str,
        app_id: str,
        state_key: str,
    ) -> SovereignStateEnvelope | None:
        facts = await self._engine.get_all_active_facts(
            tenant_id=tenant_id,
            project=project_id,
            fact_types=[APP_FORGE_FACT_TYPE],
        )
        candidates: list[SovereignStateEnvelope] = []
        for raw in facts:
            try:
                envelope = SovereignStateEnvelope.from_fact(raw)
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue
            if envelope.app_id == app_id and envelope.state_key == state_key and envelope.verify():
                candidates.append(envelope)

        if not candidates:
            return None

        candidates.sort(key=lambda item: (item.version, item.created_at))
        return candidates[-1]


class SovereignAppForge:
    """Builds the LLM-facing contract for local collaborative app generation."""

    def __init__(
        self,
        *,
        runtime_manifest: AppForgeRuntimeManifest | None = None,
        primitives: tuple[SovereignPrimitive, ...] | None = None,
    ) -> None:
        self.runtime_manifest = runtime_manifest or AppForgeRuntimeManifest()
        self.primitives = primitives or self.default_primitives()

    @staticmethod
    def default_primitives() -> tuple[SovereignPrimitive, ...]:
        return (
            SovereignPrimitive(
                name="useSovereignState",
                summary=(
                    "Tenant-scoped shared state persisted through the host into the "
                    "CORTEX VSA-SDM backplane. Every write is versioned and tainted."
                ),
                ts_signature=(
                    "export type useSovereignState = <T>(\n"
                    "  stateKey: string,\n"
                    "  defaultValue: T,\n"
                    "  options?: { scope?: 'shared' | 'local'; persist?: boolean },\n"
                    ") => [T, (newValue: T) => Promise<void>, "
                    "{ version: number; stateHash: string; taint: string; hydrated: boolean }];"
                ),
                example=(
                    "import { useSovereignState } from '$';\n"
                    "const [filters, setFilters, meta] = useSovereignState('filters', "
                    "{ quote: 'USD' });"
                ),
            ),
            SovereignPrimitive(
                name="useAgentContext",
                summary=(
                    "Read-only identity and workspace context injected by the host. "
                    "Use this instead of external auth SDKs."
                ),
                ts_signature=(
                    "export type useAgentContext = () => {\n"
                    "  agentId: string;\n"
                    "  tenantId: string;\n"
                    "  projectId: string;\n"
                    "  profile: string;\n"
                    "  appId: string;\n"
                    "  sessionId: string;\n"
                    "};"
                ),
                example=(
                    "import { useAgentContext } from '$';\n"
                    "const { tenantId, agentId, sessionId } = useAgentContext();"
                ),
            ),
            SovereignPrimitive(
                name="generateVectorStream",
                summary=(
                    "Streams local-model inference through the host bridge. "
                    "No external API keys and no SaaS transport inside the iframe."
                ),
                ts_signature=(
                    "export type generateVectorStream = (input: {\n"
                    "  prompt: string;\n"
                    "  system?: string;\n"
                    "  model?: string;\n"
                    "}) => AsyncIterable<{ delta: string; done?: boolean }>; "
                ),
                example=(
                    "import { generateVectorStream } from '$';\n"
                    "for await (const chunk of generateVectorStream({ prompt: 'Summarize volatility' })) {\n"
                    "  console.log(chunk.delta);\n"
                    "}"
                ),
            ),
        )

    def runtime_contract_source(self) -> str:
        blocks = [
            "export type JsonPrimitive = string | number | boolean | null;",
            "export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };",
            "export interface SovereignHostBridge {",
            "  transport: 'postMessage';",
            "  runtime: 'isolated-iframe';",
            "  stateBackplane: 'VSA-SDM';",
            "  networkPolicy: 'local-only';",
            "}",
            "",
        ]
        blocks.extend(primitive.to_typescript_block() for primitive in self.primitives)
        return "\n".join(blocks).strip()

    def system_prompt(self, invocation: AppForgeInvocation) -> str:
        return (
            "You are CORTEX App Forge operating inside a local sovereign runtime.\n"
            f"{self.runtime_manifest.to_prompt_block()}\n\n"
            "Generation Rules:\n"
            "- Build a single-purpose collaborative UI for the provided intent.\n"
            "- Treat useSovereignState as the default for shared state and use React local state "
            "only for ephemeral view state.\n"
            "- Never import Firebase, Supabase, external auth SDKs, or network clients.\n"
            "- Assume the host injects the custom APIs through the '$' module inside an iframe.\n"
            "- Any state mutation must be serializable, versionable, and safe to persist in "
            "tenant-scoped CORTEX memory.\n"
            "- Prefer plain React, no external dependencies, and local inference via "
            "generateVectorStream.\n\n"
            f"Tenant: {invocation.tenant_id}\n"
            f"Project: {invocation.project_id}\n"
            f"App ID: {invocation.app_id}\n"
            f"Intent: {invocation.intent}\n\n"
            "Available Host APIs:\n"
            f"{self.runtime_contract_source()}"
        )
