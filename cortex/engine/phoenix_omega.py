"""PHOENIX-OMEGA structural analysis and transformation pipeline."""

from __future__ import annotations

import ast
import asyncio
import hashlib
import logging
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.engine.phoenix_omega")

DEFAULT_COMPLEXITY_THRESHOLD = 10.0
DEFAULT_DEPENDENT_THRESHOLD = 5


class PhaseStatus(Enum):
    """Lifecycle status for each Phoenix phase."""

    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    ROLLED_BACK = auto()


class AtomicPhase(Enum):
    """Sequential phases in the Phoenix pipeline."""

    ANALYSIS = "analysis"
    EXTRACTION = "extraction"
    RECONSTRUCTION = "reconstruction"
    SCALING = "scaling"
    VERIFICATION = "verification"


@dataclass
class StructuralAtom:
    """Atomic unit of code discovered during structural analysis."""

    id: str
    source_path: Path
    ast_node: ast.AST
    complexity_score: float
    dependencies: set[str]
    dependents: set[str]
    semantic_signature: str
    transformation_history: list[dict[str, Any]] = field(default_factory=list)

    def compute_signature(self) -> str:
        """Return a short deterministic signature for the current AST node."""

        source = _safe_unparse(self.ast_node)
        return hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]


@dataclass
class PhoenixState:
    """State snapshot produced by each stage of the Phoenix pipeline."""

    phase: AtomicPhase
    status: PhaseStatus
    atoms: dict[str, StructuralAtom]
    artifacts: dict[str, Any]
    metrics: dict[str, float]
    rollback_snapshot: dict[str, Any] | None = None

    def transition_to(self, new_phase: AtomicPhase) -> PhoenixState:
        """Create the next state while preserving a rollback snapshot by deep-cloning mutable parts."""

        return PhoenixState(
            phase=new_phase,
            status=PhaseStatus.PENDING,
            atoms={aid: _clone_atom(atom) for aid, atom in self.atoms.items()},
            artifacts=self.artifacts.copy(),
            metrics=self.metrics.copy(),
            rollback_snapshot=self.to_snapshot(),
        )

    def to_snapshot(self) -> dict[str, Any]:
        """Serialize the visible state needed for rollback diagnostics."""

        return {
            "phase": self.phase.value,
            "status": self.status.name,
            "atoms_count": len(self.atoms),
            "artifacts_keys": sorted(self.artifacts.keys()),
            "metrics": self.metrics.copy(),
        }


def _safe_unparse(node: ast.AST) -> str:
    """Render an AST node as source, falling back to a stable AST dump."""

    try:
        return ast.unparse(node)
    except (AttributeError, ValueError):
        return ast.dump(node, annotate_fields=True, include_attributes=False)


def _clone_atom(atom: StructuralAtom) -> StructuralAtom:
    """Clone an atom to avoid mutating prior state snapshots in-place."""

    return StructuralAtom(
        id=atom.id,
        source_path=atom.source_path,
        ast_node=atom.ast_node,
        complexity_score=atom.complexity_score,
        dependencies=set(atom.dependencies),
        dependents=set(atom.dependents),
        semantic_signature=atom.semantic_signature,
        transformation_history=[entry.copy() for entry in atom.transformation_history],
    )


def _calculate_complexity(node: ast.AST) -> float:
    """Compute an approximate cyclomatic complexity score."""

    return 1.0 + sum(
        len(child.values) - 1.0 if isinstance(child, ast.BoolOp) else 1.0
        for child in ast.walk(node)
        if isinstance(
            child,
            ast.If
            | ast.While
            | ast.For
            | ast.ExceptHandler
            | ast.With
            | ast.Assert
            | ast.comprehension
            | ast.BoolOp,
        )
    )


def _extract_dependencies(node: ast.AST) -> set[str]:
    """Extract loaded names and attributes used by an AST node."""

    return {
        child.id if isinstance(child, ast.Name) else child.attr
        for child in ast.walk(node)
        if (isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load))
        or (isinstance(child, ast.Attribute) and isinstance(child.ctx, ast.Load))
    }


def _detect_clusters(graph: dict[str, dict[str, set[str]]]) -> list[set[str]]:
    """Detect dense clusters in a coupling graph using breadth-first search."""

    clusters: list[set[str]] = []
    visited: set[str] = set()
    for node in graph:
        if node in visited:
            continue

        cluster = {node}
        queue: deque[str] = deque([node])
        visited.add(node)

        while queue:
            current = queue.popleft()
            neighbors = (
                graph.get(current, {}).get("in", set()) | graph.get(current, {}).get("out", set())
            ) - visited
            visited.update(neighbors)
            queue.extend(sorted(neighbors))
            cluster.update(neighbors)

        if len(cluster) > 2:
            clusters.append(cluster)

    return clusters


class BaseEngine(ABC):
    """Abstract contract for every Phoenix phase engine."""

    @abstractmethod
    async def execute(self, state: PhoenixState, *args: Any, **kwargs: Any) -> PhoenixState:
        """Execute a phase and return the next state."""


class AnalysisEngine(BaseEngine):
    """Parse Python files into structural atoms and coupling metadata."""

    def __init__(self, complexity_threshold: float = DEFAULT_COMPLEXITY_THRESHOLD) -> None:
        """Initialize the analysis engine with its complexity threshold."""

        self.complexity_threshold = complexity_threshold

    async def execute(self, state: PhoenixState, target_paths: list[Path]) -> PhoenixState:
        """Analyze Python targets and produce atoms, graphs, and BPO metadata."""

        logger.info("Phoenix analysis scanning %s targets", len(target_paths))
        python_files = await asyncio.to_thread(self._collect_python_files, target_paths)

        atoms: dict[str, StructuralAtom] = state.atoms.copy()
        for path in python_files:
            try:
                atoms.update(await self._parse_file(path))
            except SyntaxError as error:
                logger.error("Phoenix analysis skipped invalid Python file %s: %s", path, error)
            except (OSError, UnicodeDecodeError, ValueError) as error:
                logger.error("Phoenix analysis failed to read %s: %s", path, error)

        self._link_dependencies(atoms)
        bpo_hits = self._detect_bpo_patterns(atoms)
        coupling_graph = self._build_coupling_graph(atoms)
        clusters = _detect_clusters(coupling_graph)

        complexities = [atom.complexity_score for atom in atoms.values()]
        avg_complexity = sum(complexities) / len(complexities) if complexities else 0.0

        new_state = state.transition_to(AtomicPhase.ANALYSIS)
        new_state.status = PhaseStatus.COMPLETED
        new_state.atoms = atoms
        new_state.metrics.update(
            {
                "total_atoms": float(len(atoms)),
                "python_files_scanned": float(len(python_files)),
                "high_complexity_count": float(
                    sum(score > self.complexity_threshold for score in complexities)
                ),
                "avg_complexity": avg_complexity,
                "bpo_patterns_detected": float(len(bpo_hits)),
                "dense_clusters": float(len(clusters)),
            }
        )
        new_state.artifacts["coupling_graph"] = coupling_graph
        new_state.artifacts["bpo_metadata"] = bpo_hits
        new_state.artifacts["dense_clusters"] = [sorted(cluster) for cluster in clusters]
        return new_state

    def _collect_python_files(self, target_paths: list[Path]) -> list[Path]:
        """Expand files and directories into a deterministic list of Python files."""

        python_files: list[Path] = []
        seen: set[Path] = set()
        for raw_path in target_paths:
            path = Path(raw_path)
            if not path.exists():
                logger.warning("Phoenix analysis ignored missing target %s", path)
                continue

            if path.is_file():
                if path.suffix == ".py":
                    resolved = path.resolve()
                    if resolved not in seen:
                        seen.add(resolved)
                        python_files.append(resolved)
                continue

            for file_path in sorted(path.rglob("*.py")):
                resolved = file_path.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    python_files.append(resolved)

        return python_files

    async def _parse_file(self, path: Path) -> dict[str, StructuralAtom]:
        """Parse a Python file into structural atoms."""

        source = await asyncio.to_thread(path.read_text, encoding="utf-8")
        tree = ast.parse(source, filename=str(path))

        file_atoms: dict[str, StructuralAtom] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                atom_id = f"{path.stem}::{node.name}"
                atom = StructuralAtom(
                    id=atom_id,
                    source_path=path,
                    ast_node=node,
                    complexity_score=float(_calculate_complexity(node)),
                    dependencies=_extract_dependencies(node),
                    dependents=set(),
                    semantic_signature="",
                )
                atom.semantic_signature = atom.compute_signature()
                file_atoms[atom_id] = atom

        return file_atoms

    def _detect_bpo_patterns(self, atoms: dict[str, StructuralAtom]) -> dict[str, list[str]]:
        """Detect coarse BPO-oriented structural patterns from source heuristics."""

        bpo_meta: dict[str, list[str]] = {}
        for atom_id, atom in atoms.items():
            source = _safe_unparse(atom.ast_node)
            patterns: list[str] = []

            if any(
                keyword in source for keyword in ("requests.", "httpx.", "aiohttp.", "api_call")
            ):
                patterns.append("NETWORK_IO")
            if any(
                keyword in source for keyword in ("read_csv", "json.load", "open(", "parse_doc")
            ):
                patterns.append("DATA_INGEST")
            if "for" in source and any(
                keyword in source for keyword in ("bid", "price", "quote", "balance")
            ):
                patterns.append("TRANSACTIONAL_LOOP")

            if patterns:
                bpo_meta[atom_id] = patterns

        return bpo_meta

    def _link_dependencies(self, atoms: dict[str, StructuralAtom]) -> None:
        """Connect atoms by matching dependency names to discovered atom names."""

        atom_names = {atom_id.split("::")[-1]: atom_id for atom_id in atoms}
        for atom_id, atom in atoms.items():
            for dependency in atom.dependencies:
                target_atom_id = atom_names.get(dependency)
                if target_atom_id and target_atom_id != atom_id:
                    atoms[target_atom_id].dependents.add(atom_id)

    def _build_coupling_graph(
        self, atoms: dict[str, StructuralAtom]
    ) -> dict[str, dict[str, set[str]]]:
        """Build a directional dependency graph between atoms."""

        return {
            atom_id: {"in": set(atom.dependents), "out": set(atom.dependencies)}
            for atom_id, atom in atoms.items()
        }


class ExtractionEngine(BaseEngine):
    """Produce extraction plans for complex or highly coupled atoms."""

    def __init__(
        self,
        complexity_threshold: float = DEFAULT_COMPLEXITY_THRESHOLD,
        dependent_threshold: int = DEFAULT_DEPENDENT_THRESHOLD,
    ) -> None:
        """Initialize extraction thresholds for complexity and fan-out."""

        self.complexity_threshold = complexity_threshold
        self.dependent_threshold = dependent_threshold

    async def execute(self, state: PhoenixState) -> PhoenixState:
        """Generate an extraction plan from the analyzed atoms."""

        logger.info("Phoenix extraction isolating dense atomic zones")
        extraction_plan: list[dict[str, Any]] = []
        for atom_id, atom in state.atoms.items():
            if atom.complexity_score > self.complexity_threshold or len(atom.dependents) > (
                self.dependent_threshold
            ):
                extraction_plan.append(
                    {
                        "atom_id": atom_id,
                        "interface": self._design_interface(atom),
                        "strategy": "DECOUPLE_PROTOCOL"
                        if len(atom.dependents) > self.dependent_threshold
                        else "EXTRACT_MIXIN",
                    }
                )

        new_state = state.transition_to(AtomicPhase.EXTRACTION)
        new_state.status = PhaseStatus.COMPLETED
        new_state.artifacts["extraction_plan"] = extraction_plan
        new_state.metrics["planned_extractions"] = float(len(extraction_plan))
        return new_state

    def _design_interface(self, atom: StructuralAtom) -> dict[str, Any]:
        """Derive a lightweight callable interface for an atom."""

        node = atom.ast_node
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            args = self._extract_callable_args(node)
            is_async = isinstance(node, ast.AsyncFunctionDef)
        elif isinstance(node, ast.ClassDef):
            init_method = self._find_init_method(node)
            args = self._extract_callable_args(init_method) if init_method else []
            is_async = False
        else:
            args = []
            is_async = False

        return {"name": f"I{atom.id.split('::')[-1]}", "args": args, "is_async": is_async}

    def _extract_callable_args(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef | None
    ) -> list[str]:
        """Extract a human-readable argument list from a callable AST node."""

        if node is None:
            return []

        args = [arg.arg for arg in node.args.posonlyargs + node.args.args]
        if args and args[0] in {"self", "cls"}:
            args = args[1:]
        args.extend(arg.arg for arg in node.args.kwonlyargs)
        if node.args.vararg is not None:
            args.append(f"*{node.args.vararg.arg}")
        if node.args.kwarg is not None:
            args.append(f"**{node.args.kwarg.arg}")
        return args

    def _find_init_method(self, node: ast.ClassDef) -> ast.FunctionDef | None:
        """Locate the constructor method for a class atom."""

        for child in node.body:
            if isinstance(child, ast.FunctionDef) and child.name == "__init__":
                return child
        return None


class BPOExtractionEngine(ExtractionEngine):
    """Augment extraction plans with BPO-specific heuristics."""

    async def execute(self, state: PhoenixState) -> PhoenixState:
        """Add BPO-prioritized extractions to the base extraction plan."""

        logger.info("Phoenix BPO extraction isolating business DNA")
        extracted_state = await super().execute(state)
        bpo_meta: dict[str, list[str]] = extracted_state.artifacts.get("bpo_metadata", {})
        extraction_plan: list[dict[str, Any]] = extracted_state.artifacts["extraction_plan"]

        existing_ids = {plan["atom_id"] for plan in extraction_plan}
        for plan in extraction_plan:
            patterns = bpo_meta.get(plan["atom_id"])
            if patterns:
                plan["patterns"] = patterns
                plan.setdefault("priority", "HIGH")

        for atom_id, patterns in bpo_meta.items():
            if atom_id in existing_ids:
                continue

            extraction_plan.append(
                {
                    "atom_id": atom_id,
                    "interface": self._design_interface(extracted_state.atoms[atom_id]),
                    "strategy": f"BPO_SPECIALIST_{'_'.join(patterns)}",
                    "patterns": patterns,
                    "priority": "HIGH",
                }
            )

        extracted_state.metrics["bpo_specific_extractions"] = float(len(bpo_meta))
        return extracted_state


class ReconstructionEngine(BaseEngine):
    """Apply non-destructive transformation metadata to every atom."""

    async def execute(self, state: PhoenixState) -> PhoenixState:
        """Record reconstruction metadata without mutating source files."""

        logger.info("Phoenix reconstruction recording transformation history")
        transformed_atoms: dict[str, StructuralAtom] = {}
        for atom_id, atom in state.atoms.items():
            cloned_atom = _clone_atom(atom)
            cloned_atom.transformation_history.append(
                {
                    "action": "pattern_injection",
                    "phase": AtomicPhase.RECONSTRUCTION.value,
                }
            )
            cloned_atom.semantic_signature = cloned_atom.compute_signature()
            transformed_atoms[atom_id] = cloned_atom

        new_state = state.transition_to(AtomicPhase.RECONSTRUCTION)
        new_state.status = PhaseStatus.COMPLETED
        new_state.atoms = transformed_atoms
        new_state.metrics["transformations_applied"] = float(len(transformed_atoms))
        new_state.artifacts["transformation_summary"] = {
            "transformed_atoms": sorted(transformed_atoms),
        }
        return new_state


class ScalingEngine(BaseEngine):
    """Generate scaling recommendations from coupling and fan-out data."""

    def __init__(self, dependent_threshold: int = DEFAULT_DEPENDENT_THRESHOLD) -> None:
        """Initialize scaling thresholds."""

        self.dependent_threshold = dependent_threshold

    async def execute(self, state: PhoenixState) -> PhoenixState:
        """Build a scaling plan from coupling clusters and high fan-out atoms."""

        logger.info("Phoenix scaling generating module fragmentation plan")
        graph: dict[str, dict[str, set[str]]] = state.artifacts.get("coupling_graph", {})
        scaling_plan: list[dict[str, Any]] = []

        for cluster in _detect_clusters(graph):
            scaling_plan.append({"target": sorted(cluster), "action": "EXTRACT_CLUSTER"})

        for atom_id, atom in state.atoms.items():
            if len(atom.dependents) > self.dependent_threshold:
                scaling_plan.append({"target": atom_id, "action": "PROMOTE_TO_SERVICE"})

        new_state = state.transition_to(AtomicPhase.SCALING)
        new_state.status = PhaseStatus.COMPLETED
        new_state.artifacts["scaling_plan"] = scaling_plan
        new_state.metrics["services_promoted"] = float(
            sum(plan["action"] == "PROMOTE_TO_SERVICE" for plan in scaling_plan)
        )
        return new_state


class VerificationEngine(BaseEngine):
    """Run deterministic checks over the pipeline output."""

    async def execute(self, state: PhoenixState) -> PhoenixState:
        """Verify artifact completeness and signature presence."""

        logger.info("Phoenix verification validating pipeline integrity")
        required_artifacts = ("coupling_graph", "extraction_plan", "scaling_plan")
        missing_artifacts = [
            artifact_name
            for artifact_name in required_artifacts
            if artifact_name not in state.artifacts
        ]
        signatures = [atom.semantic_signature for atom in state.atoms.values()]
        empty_signatures = sum(not signature for signature in signatures)
        unique_signatures = len(set(signatures))
        verification_report = {
            "atoms_verified": len(signatures),
            "unique_signatures": unique_signatures,
            "signature_collisions": max(len(signatures) - unique_signatures, 0),
            "missing_artifacts": missing_artifacts,
            "empty_signatures": empty_signatures,
        }

        is_safe = not missing_artifacts and empty_signatures == 0
        new_state = state.transition_to(AtomicPhase.VERIFICATION)
        new_state.status = PhaseStatus.COMPLETED if is_safe else PhaseStatus.FAILED
        new_state.artifacts["verification_report"] = verification_report
        new_state.metrics["verification_score"] = 100.0 if is_safe else 0.0
        return new_state


class PhoenixOrchestrator:
    """Sequential orchestrator for the Phoenix pipeline."""

    def __init__(
        self,
        analyzer: AnalysisEngine | None = None,
        extractor: BaseEngine | None = None,
        reconstructor: BaseEngine | None = None,
        scaler: BaseEngine | None = None,
        verifier: BaseEngine | None = None,
    ) -> None:
        """Build an orchestrator with overridable phase engines."""

        self.analyzer = analyzer or AnalysisEngine()
        self.extractor = extractor or BPOExtractionEngine()
        self.reconstructor = reconstructor or ReconstructionEngine()
        self.scaler = scaler or ScalingEngine()
        self.verifier = verifier or VerificationEngine()

    async def ignite(self, target_paths: list[Path]) -> PhoenixState:
        """Execute every phase in order and return the final state."""

        logger.info("Phoenix ignition starting structural metamorphosis")
        state = PhoenixState(
            phase=AtomicPhase.ANALYSIS,
            status=PhaseStatus.PENDING,
            atoms={},
            artifacts={},
            metrics={},
        )

        stages: list[tuple[BaseEngine, tuple[Any, ...]]] = [
            (self.analyzer, (target_paths,)),
            (self.extractor, ()),
            (self.reconstructor, ()),
            (self.scaler, ()),
            (self.verifier, ()),
        ]

        for engine, args in stages:
            state = await engine.execute(state, *args)
            if state.status != PhaseStatus.COMPLETED:
                logger.error("Phoenix halted at %s", engine.__class__.__name__)
                break

        return state


__all__ = [
    "AtomicPhase",
    "BaseEngine",
    "BPOExtractionEngine",
    "ExtractionEngine",
    "PhaseStatus",
    "PhoenixOrchestrator",
    "PhoenixState",
    "ReconstructionEngine",
    "ScalingEngine",
    "StructuralAtom",
    "VerificationEngine",
]


if __name__ == "__main__":
    final_state = asyncio.run(PhoenixOrchestrator().ignite([Path(__file__)]))
    logger.info(
        "Phoenix boot sequence completed with status=%s metrics=%s",
        final_state.status.name,
        final_state.metrics,
    )
