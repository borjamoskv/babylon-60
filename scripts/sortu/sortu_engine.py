from __future__ import annotations

import hashlib
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Awaitable, Sequence

from sortu_ledger import SkillLedger, TransitionEvent
from sortu_models import (
    AbortReason,
    ForgeAbortError,
    ForgeInvocation,
    SkillRecord,
    SortuBiopsy,
    SortuState,
)
from sortu_overlap import OverlapDetector
from verify_sortu import VerificationError, verify_tripartite


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class SortuEngine:
    def __init__(
        self,
        db_conn: sqlite3.Connection | None = None,
        skills_dir: str | Path | None = None,
        *,
        skills_root: str | Path | None = None,
        graph_store: Any | None = None,
        overlap_threshold: float = 0.9,
    ) -> None:
        self._db_conn = db_conn or sqlite3.connect(":memory:")
        self.ledger = SkillLedger(self._db_conn)
        resolved_skills_dir = skills_dir if skills_dir is not None else skills_root
        self.skills_dir = Path(resolved_skills_dir) if resolved_skills_dir is not None else Path.cwd()
        self.graph_store = graph_store
        self.default_overlap_threshold = overlap_threshold
        self._overlap = OverlapDetector(self.skills_dir)

    @staticmethod
    def _intent_to_name(intent: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", intent.lower()).strip("-")
        return slug or "skill"

    def _abort(
        self,
        inv: ForgeInvocation,
        reason: AbortReason,
        detail: str,
        *,
        artifact_hashes: dict[str, str] | None = None,
    ) -> None:
        record = SkillRecord.new(
            skill_name=self._intent_to_name(inv.intent),
            version="1.0.0",
            artifact_hashes=artifact_hashes or {},
            causal_parent=inv.causal_parent,
            ttl_days=inv.ttl_days,
        )
        self.ledger.register(record)
        self.ledger.transition(record.skill_id, SortuState.ABORTED, abort_reason=reason)
        raise ForgeAbortError(reason, detail)

    def _verify_skill_dir(self, skill_dir: str | Path) -> dict[str, str]:
        return verify_tripartite(Path(skill_dir))["artifact_hashes"]

    @staticmethod
    def _hash_file(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _verify_pipeline_skill_dir(self, skill_dir: str | Path) -> dict[str, str]:
        root = Path(skill_dir)
        if not root.exists():
            raise VerificationError(f"{root} not found")

        skill_md = root / "SKILL.md"
        schema_json = root / "schema.json"
        verifier_files = sorted(root.glob("verify_*.py"))

        missing = [
            label
            for path, label in ((skill_md, "SKILL.md"), (schema_json, "schema.json"))
            if not path.exists()
        ]
        if missing:
            raise VerificationError(f"Missing required artifact: {missing[0]}")
        if not verifier_files:
            raise VerificationError("Missing required artifact: verify_*.py")

        return {
            "SKILL.md": self._hash_file(skill_md),
            "schema.json": self._hash_file(schema_json),
            **{path.name: self._hash_file(path) for path in verifier_files},
        }

    def _forge_sync(
        self,
        inv: ForgeInvocation,
        *,
        skill_dir: str | Path | None = None,
        artifact_hashes: dict[str, str] | None = None,
    ) -> SkillRecord:
        if inv.causal_parent and self.ledger.get(inv.causal_parent) is None:
            self._abort(inv, AbortReason.INVALID_CAUSAL_PARENT, "causal parent not found")

        overlap = self._overlap.decide(
            inv.intent,
            overlap_threshold=inv.overlap_threshold,
            causal_gap_threshold=inv.causal_gap_threshold,
        )
        if overlap.decision == "ABORT_REDUNDANT":
            self._abort(
                inv,
                AbortReason.REDUNDANT_COMPUTATION,
                f"overlap={overlap.overlap_score:.2f}",
            )

        verified_artifact_hashes = dict(artifact_hashes or {})
        if skill_dir is not None and not verified_artifact_hashes:
            try:
                verified_artifact_hashes = self._verify_skill_dir(skill_dir)
            except VerificationError as exc:
                self._abort(
                    inv,
                    AbortReason.CONTRACT_VERIFICATION_FAILED,
                    str(exc),
                )

        record = SkillRecord.new(
            skill_name=self._intent_to_name(inv.intent),
            version="1.0.0",
            artifact_hashes=verified_artifact_hashes,
            causal_parent=inv.causal_parent,
            ttl_days=inv.ttl_days,
        )
        self.ledger.register(record)
        for state in [
            SortuState.AUDITED,
            SortuState.FORGED,
            SortuState.VERIFIED,
            SortuState.LINKED,
            SortuState.LEDGERED,
            SortuState.ACTIVE,
        ]:
            self.ledger.transition(record.skill_id, state)
        return self.ledger.get(record.skill_id)  # type: ignore[return-value]

    def forge(
        self,
        invocation_or_skill: ForgeInvocation | str | Path,
        *,
        skill_dir: str | Path | None = None,
        intent: str = "",
        invocation_log: Sequence[dict[str, Any]] | None = None,
        requested_by: str = "sortu-pipeline",
    ) -> SkillRecord | Awaitable[SkillRecord]:
        if isinstance(invocation_or_skill, ForgeInvocation):
            return self._forge_sync(invocation_or_skill, skill_dir=skill_dir)
        return self._forge_pipeline(
            Path(invocation_or_skill),
            intent=intent,
            invocation_log=invocation_log,
            requested_by=requested_by,
        )

    async def _forge_pipeline(
        self,
        skill_dir: Path,
        *,
        intent: str = "",
        invocation_log: Sequence[dict[str, Any]] | None = None,
        requested_by: str = "sortu-pipeline",
    ) -> SkillRecord:
        normalized_intent = intent.strip()
        if len(normalized_intent) < 8:
            normalized_intent = (
                f"{normalized_intent} skill".strip()
                if normalized_intent
                else f"Forge skill {skill_dir.name}"
            )
        invocation = ForgeInvocation(
            intent=normalized_intent,
            causal_parent=None,
            requested_by=requested_by,
            overlap_threshold=self.default_overlap_threshold,
        )

        try:
            artifact_hashes = self._verify_pipeline_skill_dir(skill_dir)
        except VerificationError:
            return self._record_pipeline_abort(invocation, skill_dir, AbortReason.MISSING_TRIPARTITE)

        record = self._forge_sync(
            invocation,
            skill_dir=skill_dir,
            artifact_hashes=artifact_hashes,
        )
        record.biopsy = self._build_biopsy(invocation_log or ())
        record.graph_entities_created = await self._link_skill_graph(skill_dir)
        return record

    def _record_pipeline_abort(
        self,
        inv: ForgeInvocation,
        skill_dir: Path,
        reason: AbortReason,
    ) -> SkillRecord:
        record = SkillRecord.new(
            skill_name=skill_dir.name or self._intent_to_name(inv.intent),
            version="1.0.0",
            artifact_hashes={},
            causal_parent=inv.causal_parent,
            ttl_days=inv.ttl_days,
        )
        self.ledger.register(record)
        self.ledger.transition(record.skill_id, SortuState.ABORTED, abort_reason=reason)
        hydrated = self.ledger.get(record.skill_id)
        if hydrated is None:
            raise RuntimeError("aborted pipeline record was not persisted")
        return hydrated

    @staticmethod
    def _build_biopsy(invocation_log: Sequence[dict[str, Any]]) -> SortuBiopsy | None:
        if not invocation_log:
            return None

        compound_yield = 0.0
        entropy_cost = 0.0
        for event in invocation_log:
            hours_saved = max(float(event.get("hours_saved", 0.0)), 0.0)
            chain_depth = max(int(event.get("chain_depth", 1)), 1)
            latency_ms = max(float(event.get("latency_ms", 0.0)), 0.0)
            if event.get("success", True):
                compound_yield += hours_saved * (1.15 ** (chain_depth - 1))
            entropy_cost += latency_ms / 1000.0

        net_exergy = round(compound_yield - entropy_cost, 2)
        return SortuBiopsy(
            total_invocations=len(invocation_log),
            compound_yield=round(compound_yield, 2),
            entropy_cost=round(entropy_cost, 2),
            net_exergy=net_exergy,
            verdict="PASS" if net_exergy > 0 else "HOLD",
        )

    async def _link_skill_graph(self, skill_dir: Path) -> int:
        if self.graph_store is None:
            return 0
        add_node = getattr(self.graph_store, "add_node", None)
        if callable(add_node):
            await add_node(
                node_id=skill_dir.name,
                tenant_id="sortu",
                node_type="skill",
                attributes={"path": str(skill_dir)},
            )
        return 1

    def quarantine_sweep(self, *, now: datetime | None = None) -> list[TransitionEvent]:
        ref = now or _now_utc()
        events: list[TransitionEvent] = []
        for record in self.ledger.list_by_state(SortuState.ACTIVE):
            if record.ttl_expiration <= ref:
                events.append(self.ledger.transition(record.skill_id, SortuState.QUARANTINED))
        return events

    def tombstone_sweep(
        self,
        *,
        grace_days: int = 7,
        now: datetime | None = None,
    ) -> list[TransitionEvent]:
        ref = now or _now_utc()
        cutoff = ref - timedelta(days=grace_days)
        events: list[TransitionEvent] = []
        for record in self.ledger.list_by_state(SortuState.QUARANTINED):
            if record.ttl_expiration <= cutoff:
                events.append(self.ledger.transition(record.skill_id, SortuState.TOMBSTONED))
        return events

    def purge_sweep(
        self,
        *,
        purge_after_days: int = 30,
        now: datetime | None = None,
    ) -> list[TransitionEvent]:
        ref = now or _now_utc()
        cutoff = ref - timedelta(days=purge_after_days)
        events: list[TransitionEvent] = []
        for record in self.ledger.list_by_state(SortuState.TOMBSTONED):
            if record.ttl_expiration <= cutoff:
                events.append(self.ledger.transition(record.skill_id, SortuState.PURGED))
        return events
