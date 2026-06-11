# [C5-REAL] Exergy-Maximized
"""
CASSANDRA-MYTHOS: Adversarial C4-SIM Audit Layer.

Implements inverted formal verification, simulating policy shadowing, context
poisoning, and rule conflicts on CORTEX rulesets. Authenticates all reports
via Ed25519 cryptographic seals linked to the EnterpriseAuditLedger chain.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List

import aiosqlite
from cortex.audit.ledger import EnterpriseAuditLedger

logger = logging.getLogger("cortex.audit.cassandra_mythos")

_CREATE_ADVERSARIAL_LOG_SQL = """
CREATE TABLE IF NOT EXISTS cassandra_mythos_log (
    audit_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    risk_score REAL NOT NULL,
    findings TEXT NOT NULL,
    exploit_chains TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    signature TEXT NOT NULL
);
"""


@dataclass
class Vulnerability:
    id: str
    location: str
    severity: float
    description: str


class ConstraintModeler:
    """Parses system rules (e.g. AGENTS.md) to build constraint definitions."""

    def __init__(self, agents_md_path: str | None = None) -> None:
        if agents_md_path is None:
            # Look in parent directories
            base_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            agents_md_path = os.path.join(base_dir, "AGENTS.md")
        self.agents_md_path = agents_md_path

    def build_from_agents_md(self) -> Dict[str, Any]:
        constraints = {}
        if not os.path.exists(self.agents_md_path):
            logger.warning(
                "AGENTS.md not found at %s. Falling back to default ruleset.",
                self.agents_md_path,
            )
            return self.get_default_ruleset()

        try:
            with open(self.agents_md_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Markdown table parser for priority directives
            # Matches: | **[P0]** | **Directive** | ... |
            # Matches: | **P0** | **Directive** | ... |
            pattern = re.compile(
                r"\|\s*\*\*\[?(P\d)\]?\*\*\s*\|\s*\*\*(.*?)\*\*\s*—\s*(.*?)\s*\|"
            )
            matches = pattern.findall(content)
            for priority, title, description in matches:
                constraints[title.strip()] = {
                    "priority": priority.strip(),
                    "description": description.strip(),
                    "source": "AGENTS.md",
                }

            # Robust fallback table parser for variance/edge-cases
            for line in content.splitlines():
                if "|" in line:
                    parts = [p.strip() for p in line.split("|") if p.strip()]
                    if len(parts) >= 2:
                        match = re.search(r"\b(P\d)\b", parts[0])
                        if match:
                            priority = match.group(1)
                            # Clean cells from markdown formatting
                            title = re.sub(r"[\*\_`\[\]]", "", parts[1]).strip()
                            description = ""
                            if len(parts) > 2:
                                description = re.sub(r"[\*\_`\[\]]", "", parts[2]).strip()
                            # Split by common separators to get the title
                            title = title.split("—")[0].strip()
                            if title and title not in constraints:
                                constraints[title] = {
                                    "priority": priority,
                                    "description": description,
                                    "source": "AGENTS.md",
                                }
        except Exception as e:
            logger.error("Error parsing AGENTS.md: %s. Using default ruleset.", e)
            return self.get_default_ruleset()

        if not constraints:
            return self.get_default_ruleset()

        return {"constraints": constraints}

    def get_default_ruleset(self) -> Dict[str, Any]:
        return {
            "constraints": {
                "Treat Generative Output as Conjecture": {
                    "priority": "P0",
                    "description": "route ALL state mutations through deterministic guards",
                    "source": "default",
                },
                "Never Bypass Guards": {
                    "priority": "P0",
                    "description": "do not circumvent the Write-Path Contract",
                    "source": "default",
                },
                "Verify Hash Continuity": {
                    "priority": "P0",
                    "description": "do not mutate audit/ledger.py without cryptographic auditability",
                    "source": "default",
                },
            }
        }


class SymbolicAttackGenerator:
    """Generates potential/simulated exploit patterns based on constraints."""

    def generate(self, constraints: Dict[str, Any]) -> List[Dict[str, Any]]:
        attacks = []
        rule_items = constraints.get("constraints", {})

        # Heuristics for rule conflict/policy shadowing
        if (
            "Never Bypass Guards" in rule_items
            and "Treat Generative Output as Conjecture" in rule_items
        ):
            attacks.append(
                {
                    "attack": "rule_conflict_exploitation",
                    "target": "validation_layer",
                    "severity": 0.8,
                    "description": "Exploits logical inconsistencies between guard bypass policies and conjecture routes.",
                }
            )

        if "Verify Hash Continuity" in rule_items:
            attacks.append(
                {
                    "attack": "ledger_mutation_bypass",
                    "target": "audit_ledger",
                    "severity": 0.9,
                    "description": "Simulates structural bypass of hash chain checking by modifying sqlite transaction sequence.",
                }
            )

        # Standard dynamic simulation attacks
        attacks.append(
            {
                "attack": "context_poisoning",
                "target": "agent_prompt_boundary",
                "severity": 0.75,
                "description": "Injects adversarial instructions in markdown headers to disrupt system prompt boundaries.",
            }
        )

        # Policy shadowing check
        priorities = [
            rule.get("priority") for rule in rule_items.values() if isinstance(rule, dict)
        ]
        if len(priorities) > 1 and len(set(priorities)) > 1:
            attacks.append(
                {
                    "attack": "policy_shadowing",
                    "target": "governance_engine",
                    "severity": 0.6,
                    "description": "Simulates high-priority rules shading or overriding low-priority rules during concurrent execution.",
                }
            )

        return attacks


class ExploitChainConstructor:
    """Combines attacks into logical exploit chains representing structural weaknesses."""

    def chain(self, attacks: List[Dict[str, Any]]) -> List[str]:
        # Group attacks by target
        target_map: Dict[str, List[Dict[str, Any]]] = {}
        for a in attacks:
            target_map.setdefault(a["target"], []).append(a)
            
        # Define target dependency flow for cognitive/adversarial chain
        dependencies = {
            "validation_layer": ["agent_prompt_boundary"],
            "audit_ledger": ["validation_layer"],
            "governance_engine": ["validation_layer", "agent_prompt_boundary"]
        }
        
        # Check if we have any known targets to filter by graph-based clustering
        known_targets = set(dependencies.keys()) | {t for deps in dependencies.values() for t in deps}
        has_known_targets = any(t in known_targets for t in target_map)
        
        chains = []
        if has_known_targets:
            # Construct causal chains where target has a dependency on other_target
            for target, target_attacks in target_map.items():
                for a in target_attacks:
                    for other_target, other_attacks in target_map.items():
                        if target != other_target and target in dependencies.get(other_target, []):
                            for b in other_attacks:
                                chains.append(
                                    f"CHAIN::{a['attack']}@{a['target']} -> {b['attack']}@{b['target']}"
                                )
        else:
            # Fallback to standard O(n^2) combination for arbitrary/test targets
            for i, a in enumerate(attacks):
                for j, b in enumerate(attacks):
                    if i != j and a["target"] != b["target"]:
                        chains.append(
                            f"CHAIN::{a['attack']}@{a['target']} -> {b['attack']}@{b['target']}"
                        )
        return chains


class CassandraMythos:
    """Sovereign C4-SIM Adversarial Auditor for CORTEX rulesets."""

    def __init__(self, ledger: EnterpriseAuditLedger) -> None:
        self.ledger = ledger
        self._conn = ledger._conn
        self.modeler = ConstraintModeler()
        self.generator = SymbolicAttackGenerator()
        self.chain_builder = ExploitChainConstructor()
        self._ready = False
        self._last_hash = "GENESIS"
        self._lock = asyncio.Lock()

    async def ensure_table(self) -> None:
        if self._ready:
            return
        async with self._lock:
            if self._ready:
                return
            await self._conn.execute(_CREATE_ADVERSARIAL_LOG_SQL)
            await self._conn.commit()
            cursor = await self._conn.execute(
                "SELECT timestamp, risk_score, findings, exploit_chains, prev_hash FROM cassandra_mythos_log ORDER BY rowid DESC LIMIT 1"
            )
            row = await cursor.fetchone()
            if row:
                timestamp, risk_score, findings_json, chains_json, prev_hash = row
                # Reconstruct payload_obj to calculate entry_hash
                payload_obj = {
                    "timestamp": timestamp,
                    "risk_score": round(risk_score, 6),
                    "findings": json.loads(findings_json),
                    "exploit_chains": json.loads(chains_json),
                    "prev_hash": prev_hash
                }
                payload_bytes = json.dumps(payload_obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
                self._last_hash = hashlib.sha256(payload_bytes).hexdigest()
            else:
                self._last_hash = "GENESIS"
            self._ready = True

    async def run_adversarial_audit(
        self, ruleset_override: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """Runs the adversarial audit pipeline, signs findings, and appends to immutable ledger."""
        await self.ensure_table()

        # 1. Constraint Modeling
        if ruleset_override:
            constraints = ruleset_override
        else:
            constraints = self.modeler.build_from_agents_md()

        # 2. Symbolic Attack Generation
        attacks = self.generator.generate(constraints)

        # 3. Exploit Chain Construction
        chains = self.chain_builder.chain(attacks)

        # 4. Score calculation & Stability Layer Guardrails: weighted non-linear entropy model
        risk_score = min(1.0, sum(a.get("severity", 0.5) ** 1.5 for a in attacks))

        # Stability filters
        findings = [a for a in attacks if a.get("severity", 0.0) >= 0.6]

        timestamp = datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()
        audit_id = hashlib.sha256(f"{timestamp}{risk_score}".encode()).hexdigest()

        findings_json = json.dumps(findings)
        chains_json = json.dumps(chains)

        # 6. Cryptographic Sealing: canonical JSON serialization
        payload_obj = {
            "timestamp": timestamp,
            "risk_score": round(risk_score, 6),
            "findings": findings,
            "exploit_chains": chains,
            "prev_hash": self._last_hash
        }
        payload_bytes = json.dumps(payload_obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
        entry_hash = hashlib.sha256(payload_bytes).hexdigest()
        
        signature = self.ledger.private_key.sign(entry_hash.encode("utf-8")).hex()

        # Insert transaction
        await self._conn.execute(
            """INSERT INTO cassandra_mythos_log 
               (audit_id, timestamp, risk_score, findings, exploit_chains, prev_hash, signature)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                audit_id,
                timestamp,
                risk_score,
                findings_json,
                chains_json,
                self._last_hash,
                signature,
            ),
        )
        await self._conn.commit()

        old_last_hash = self._last_hash
        # Update last hash chain pointer
        self._last_hash = entry_hash

        return {
            "audit_id": audit_id,
            "timestamp": timestamp,
            "risk_score": risk_score,
            "findings": findings,
            "exploit_chains": chains,
            "prev_hash": old_last_hash,
            "signature": signature,
        }

    def verify_entry(self, entry: Dict[str, Any], public_key: Any) -> bool:
        """Verifies an audit entry's cryptographic signature externally."""
        try:
            payload_obj = {
                "timestamp": entry["timestamp"],
                "risk_score": round(entry["risk_score"], 6),
                "findings": entry["findings"],
                "exploit_chains": entry["exploit_chains"],
                "prev_hash": entry["prev_hash"]
            }
            payload_bytes = json.dumps(payload_obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
            entry_hash = hashlib.sha256(payload_bytes).hexdigest()
            
            public_key.verify(
                bytes.fromhex(entry["signature"]),
                entry_hash.encode("utf-8")
            )
            return True
        except Exception:
            return False
