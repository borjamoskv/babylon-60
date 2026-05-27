#!/usr/bin/env python3
"""
Cortex Persist v6: Recursive Self-Auditing Reality Engine (RSA-RE)

Arquitectura:
  Event → Multi-Agent Consensus → Commit Decision → Recursive Audit Layer
  → Truth Mutation Tracker → Fork Simulation Sandbox → Ledger (versioned reality graph)

Este módulo implementa:
1. Recursive Self-Audit Layer - Meta-auditoría de decisiones
2. Truth Mutation Tracking - Genética de la verdad
3. Fork Simulation Sandbox - Universos paralelos de realidad
4. Epistemic Reconciliation Engine - Colapso probabilístico
5. Self-Model of the System - Modelo interno de sesgos
6. Adversarial Self-Attack Mode - Auto-ataque preventivo
7. Versioned Reality Graph - Memoria no-lineal versionada
"""

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Set, Tuple, Any, Callable
from enum import Enum
from collections import defaultdict
import threading
import random
import math
from datetime import datetime
import copy


# ============================================================================
# ENUMS Y CONSTANTES
# ============================================================================

class MutationType(Enum):
    """Tipos de mutación semántica"""
    SEMANTIC_DRIFT = "semantic_drift"
    CONFIDENCE_DECAY = "confidence_decay"
    REINFORCEMENT_AMPLIFICATION = "reinforcement_amplification"
    ADVERSARIAL_DISTORTION = "adversarial_distortion"


class ForkStatus(Enum):
    """Estado de un fork de realidad"""
    ACTIVE = "active"
    MERGED = "merged"
    COLLAPSED = "collapsed"
    DIVERGENT = "divergent"


class AuditSeverity(Enum):
    """Severidad de hallazgos de auditoría"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    PARADOX = "paradox"


# Límites estructurales para prevenir explosión recursiva
MAX_RECURSION_DEPTH = 3
MAX_ACTIVE_FORKS = 5
MERGE_THRESHOLD_BASE = 0.85


# ============================================================================
# DATA CLASSES CORE
# ============================================================================

@dataclass
class AgentProfile:
    """Perfil de agente con métricas de confianza y sesgo"""
    agent_id: str
    name: str
    weight: float = 1.0
    historical_accuracy: float = 0.95
    bias_vector: Dict[str, float] = field(default_factory=dict)
    contradiction_count: int = 0
    last_active: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class AuditFinding:
    """Hallazgo de auditoría recursiva"""
    finding_id: str
    decision_id: str
    severity: AuditSeverity
    category: str
    description: str
    affected_agents: List[str]
    bias_detected: Dict[str, float]
    timestamp: float = field(default_factory=time.time)
    recursion_depth: int = 0
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['severity'] = self.severity.value
        return d


@dataclass
class TruthLineage:
    """Linaje genético de un evento de verdad"""
    event_id: str
    origin_event: Optional[str]
    mutations: List[Dict] = field(default_factory=list)
    reinforcement_events: List[str] = field(default_factory=list)
    current_form_timestamp: float = field(default_factory=time.time)
    confidence_score: float = 1.0
    
    def add_mutation(self, mutation_type: MutationType, delta: float, reason: str):
        self.mutations.append({
            'type': mutation_type.value,
            'delta': delta,
            'reason': reason,
            'timestamp': time.time()
        })
        self.current_form_timestamp = time.time()
        
    def add_reinforcement(self, event_id: str):
        self.reinforcement_events.append(event_id)
        
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class RealityFork:
    """Fork de realidad paralela para simulación"""
    fork_id: str
    base_event_id: str
    scenario_type: str  # 'accepted', 'rejected', 'adversarial'
    events: List[Dict] = field(default_factory=list)
    status: ForkStatus = ForkStatus.ACTIVE
    divergence_score: float = 0.0
    damage_radius: float = 0.0
    created_at: float = field(default_factory=time.time)
    merged_into: Optional[str] = None
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['status'] = self.status.value
        return d


@dataclass
class SystemSelfModel:
    """Modelo interno del sistema sobre sí mismo"""
    agent_weights: Dict[str, float] = field(default_factory=dict)
    decision_biases: Dict[str, float] = field(default_factory=dict)
    historical_error_rate: float = 0.0
    contradiction_density: float = 0.0
    entropy_level: float = 0.0
    total_decisions: int = 0
    recursive_audits_performed: int = 0
    forks_created: int = 0
    forks_merged: int = 0
    last_calibration: float = field(default_factory=time.time)
    
    def calculate_confidence(self) -> float:
        """
        Función clave: system_confidence() = f(accuracy, bias, drift, entropy)
        """
        accuracy_factor = 1.0 - self.historical_error_rate
        bias_penalty = sum(abs(b) for b in self.decision_biases.values()) / max(len(self.decision_biases), 1)
        entropy_penalty = self.entropy_level
        contradiction_penalty = self.contradiction_density
        
        confidence = (
            accuracy_factor * 0.4 +
            (1.0 - bias_penalty) * 0.25 +
            (1.0 - entropy_penalty) * 0.2 +
            (1.0 - contradiction_penalty) * 0.15
        )
        return max(0.0, min(1.0, confidence))
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['system_confidence'] = self.calculate_confidence()
        return d


@dataclass
class VersionedRealityNode:
    """Nodo en el grafo de realidad versionada"""
    node_id: str
    event_data: Dict
    version: int
    confidence: float
    lineage: Optional[TruthLineage]
    audit_metadata: Dict
    parent_ids: List[str] = field(default_factory=list)
    child_ids: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    is_collapsed: bool = False
    
    def to_dict(self) -> Dict:
        d = {
            'node_id': self.node_id,
            'event_data': self.event_data,
            'version': self.version,
            'confidence': self.confidence,
            'lineage': self.lineage.to_dict() if self.lineage else None,
            'audit_metadata': self.audit_metadata,
            'parent_ids': self.parent_ids,
            'child_ids': self.child_ids,
            'timestamp': self.timestamp,
            'is_collapsed': self.is_collapsed
        }
        return d


@dataclass
class DecisionRecord:
    """Registro completo de una decisión con meta-auditoría"""
    decision_id: str
    event_id: str
    consensus_result: Dict
    participating_agents: List[str]
    agent_weights_snapshot: Dict[str, float]
    audit_findings: List[AuditFinding] = field(default_factory=list)
    recursion_depth: int = 0
    was_bias_detected: bool = False
    was_reweighted: bool = False
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['audit_findings'] = [f.to_dict() for f in self.audit_findings]
        return d


# ============================================================================
# RECURSIVE SELF-AUDIT LAYER
# ============================================================================

class RecursiveAuditLayer:
    """
    Capa de auto-auditoría recursiva.
    
    Cada decisión genera meta-eventos:
    - "Why was this event accepted?"
    - "Which agents influenced it?"
    - "Was the consensus biased?"
    """
    
    def __init__(self, max_depth: int = MAX_RECURSION_DEPTH):
        self.max_depth = max_depth
        self.audit_history: List[AuditFinding] = []
        self.decision_cache: Dict[str, DecisionRecord] = {}
        self._lock = threading.RLock()
        
    def audit_decision(self, decision: DecisionRecord, depth: int = 0) -> List[AuditFinding]:
        """
        Auditoría recursiva de una decisión.
        
        def audit(decision):
            meta = analyze_agents(decision)
            contradictions = detect_internal_bias(meta)
            if contradictions:
                flag(decision)
                reweight_agents(meta)
            return meta
        """
        if depth > self.max_depth:
            finding = AuditFinding(
                finding_id=str(uuid.uuid4()),
                decision_id=decision.decision_id,
                severity=AuditSeverity.INFO,
                category="recursion_limit",
                description=f"Maximum recursion depth ({self.max_depth}) reached",
                affected_agents=[],
                bias_detected={},
                recursion_depth=depth
            )
            return [finding]
        
        findings = []
        
        # 1. Analizar distribución de influencia de agentes
        influence_findings = self._analyze_agent_influence(decision, depth)
        findings.extend(influence_findings)
        
        # 2. Detectar sesgos internos
        bias_findings = self._detect_internal_bias(decision, depth)
        findings.extend(bias_findings)
        
        # 3. Verificar consistencia con decisiones históricas
        consistency_findings = self._check_historical_consistency(decision, depth)
        findings.extend(consistency_findings)
        
        # 4. Si hay contradicciones, flaggear y recalcular pesos
        if any(f.severity in [AuditSeverity.CRITICAL, AuditSeverity.PARADOX] for f in findings):
            decision.was_bias_detected = True
            self._reweight_agents_based_on_findings(decision, findings)
            decision.was_reweighted = True
        
        # 5. Registrar auditoría
        with self._lock:
            decision.audit_findings = findings
            decision.recursion_depth = depth
            self.decision_cache[decision.decision_id] = decision
            self.audit_history.extend(findings)
        
        # 6. Recursión: auditar la propia auditoría si es crítico
        critical_findings = [f for f in findings if f.severity == AuditSeverity.PARADOX]
        if critical_findings and depth < self.max_depth - 1:
            meta_audit = self._audit_the_audit(findings, decision, depth + 1)
            findings.extend(meta_audit)
        
        return findings
    
    def _analyze_agent_influence(self, decision: DecisionRecord, depth: int) -> List[AuditFinding]:
        """Analizar si algún agente tuvo influencia desproporcionada"""
        findings = []
        weights = decision.agent_weights_snapshot
        
        if not weights:
            return findings
            
        total_weight = sum(weights.values())
        if total_weight == 0:
            return findings
        
        avg_weight = total_weight / len(weights)
        threshold = avg_weight * 3  # 3x el promedio es sospechoso
        
        for agent_id, weight in weights.items():
            if weight > threshold:
                finding = AuditFinding(
                    finding_id=str(uuid.uuid4()),
                    decision_id=decision.decision_id,
                    severity=AuditSeverity.WARNING,
                    category="agent_dominance",
                    description=f"Agent {agent_id} had disproportionate influence ({weight:.2f} vs avg {avg_weight:.2f})",
                    affected_agents=[agent_id],
                    bias_detected={'dominance': weight / avg_weight},
                    recursion_depth=depth
                )
                findings.append(finding)
        
        return findings
    
    def _detect_internal_bias(self, decision: DecisionRecord, depth: int) -> List[AuditFinding]:
        """Detectar contradicciones internas en la decisión"""
        findings = []
        
        consensus = decision.consensus_result
        if not consensus:
            return findings
        
        # Verificar si el resultado contradice la mayoría de agentes
        participating = set(decision.participating_agents)
        result_confidence = consensus.get('confidence', 0)
        result_decision = consensus.get('decision', 'unknown')
        
        # Simular detección de contradicción
        if result_confidence < 0.5 and len(participating) > 2:
            finding = AuditFinding(
                finding_id=str(uuid.uuid4()),
                decision_id=decision.decision_id,
                severity=AuditSeverity.WARNING,
                category="low_confidence_consensus",
                description=f"Decision made with low confidence ({result_confidence:.2f}) despite {len(participating)} agents",
                affected_agents=list(participating),
                bias_detected={'uncertainty': 1.0 - result_confidence},
                recursion_depth=depth
            )
            findings.append(finding)
        
        return findings
    
    def _check_historical_consistency(self, decision: DecisionRecord, depth: int) -> List[AuditFinding]:
        """Verificar consistencia con decisiones históricas"""
        findings = []
        
        # Buscar decisiones similares en caché
        similar_decisions = [
            d for d in self.decision_cache.values()
            if d.event_id != decision.event_id
            and d.timestamp < decision.timestamp
        ]
        
        if not similar_decisions:
            return findings
        
        # Verificar inconsistencias graves
        recent = sorted(similar_decisions, key=lambda x: x.timestamp, reverse=True)[:5]
        contradictions = 0
        
        for prev in recent:
            if prev.was_bias_detected and not decision.was_bias_detected:
                contradictions += 1
        
        if contradictions >= 2:
            finding = AuditFinding(
                finding_id=str(uuid.uuid4()),
                decision_id=decision.decision_id,
                severity=AuditSeverity.CRITICAL,
                category="pattern_inconsistency",
                description=f"Decision pattern inconsistent with {contradictions} recent audited decisions",
                affected_agents=decision.participating_agents,
                bias_detected={'inconsistency': contradictions / len(recent)},
                recursion_depth=depth
            )
            findings.append(finding)
        
        return findings
    
    def _reweight_agents_based_on_findings(self, decision: DecisionRecord, findings: List[AuditFinding]):
        """Recalcular pesos de agentes basado en hallazgos"""
        # Implementación simplificada - en producción usaría algoritmo más sofisticado
        penalty_factor = 0.9
        for finding in findings:
            if finding.severity in [AuditSeverity.CRITICAL, AuditSeverity.PARADOX]:
                for agent_id in finding.affected_agents:
                    if agent_id in decision.agent_weights_snapshot:
                        decision.agent_weights_snapshot[agent_id] *= penalty_factor
    
    def _audit_the_audit(self, findings: List[AuditFinding], decision: DecisionRecord, depth: int) -> List[AuditFinding]:
        """Meta-auditoría: auditar los propios hallazgos"""
        meta_findings = []
        
        # Verificar si los hallazgos son consistentes entre sí
        categories = defaultdict(int)
        for f in findings:
            categories[f.category] += 1
        
        # Si hay demasiadas categorías diferentes, puede haber ruido
        if len(categories) > 4:
            meta_finding = AuditFinding(
                finding_id=str(uuid.uuid4()),
                decision_id=decision.decision_id,
                severity=AuditSeverity.PARADOX,
                category="audit_noise",
                description=f"Audit produced {len(categories)} different finding categories - possible noise",
                affected_agents=[],
                bias_detected={'noise_level': len(categories) / len(findings)},
                recursion_depth=depth
            )
            meta_findings.append(meta_finding)
        
        return meta_findings
    
    def get_audit_statistics(self) -> Dict:
        """Obtener estadísticas de auditorías realizadas"""
        with self._lock:
            severity_counts = defaultdict(int)
            category_counts = defaultdict(int)
            
            for finding in self.audit_history:
                severity_counts[finding.severity.value] += 1
                category_counts[finding.category] += 1
            
            return {
                'total_audits': len(self.decision_cache),
                'total_findings': len(self.audit_history),
                'by_severity': dict(severity_counts),
                'by_category': dict(category_counts),
                'max_recursion_reached': max((d.recursion_depth for d in self.decision_cache.values()), default=0)
            }


# ============================================================================
# TRUTH MUTATION TRACKER
# ============================================================================

class TruthMutationTracker:
    """
    La verdad deja de ser estática → ahora tiene genética.
    
    Rastrea linaje, mutaciones y evolución de eventos de verdad.
    """
    
    def __init__(self):
        self.lineages: Dict[str, TruthLineage] = {}
        self.event_to_lineage: Dict[str, str] = {}  # event_id -> lineage_id
        self._lock = threading.Lock()
        
    def create_lineage(self, event_id: str, origin_event: Optional[str] = None) -> TruthLineage:
        """Crear nuevo linaje de verdad"""
        with self._lock:
            lineage = TruthLineage(
                event_id=event_id,
                origin_event=origin_event,
                confidence_score=1.0 if origin_event is None else 0.8
            )
            
            self.lineages[event_id] = lineage
            self.event_to_lineage[event_id] = event_id
            
            # Si tiene origen, conectar linajes
            if origin_event and origin_event in self.lineages:
                self.lineages[origin_event].add_reinforcement(event_id)
            
            return lineage
    
    def record_mutation(self, event_id: str, mutation_type: MutationType, 
                       delta: float, reason: str) -> Optional[TruthLineage]:
        """Registrar mutación en un evento de verdad"""
        with self._lock:
            if event_id not in self.lineages:
                return None
            
            lineage = self.lineages[event_id]
            lineage.add_mutation(mutation_type, delta, reason)
            
            # Actualizar score de confianza
            if mutation_type == MutationType.CONFIDENCE_DECAY:
                lineage.confidence_score = max(0.0, lineage.confidence_score - abs(delta))
            elif mutation_type == MutationType.REINFORCEMENT_AMPLIFICATION:
                lineage.confidence_score = min(1.0, lineage.confidence_score + abs(delta))
            elif mutation_type == MutationType.SEMANTIC_DRIFT:
                lineage.confidence_score *= (1.0 - abs(delta) * 0.5)
            elif mutation_type == MutationType.ADVERSARIAL_DISTORTION:
                lineage.confidence_score *= (1.0 - abs(delta))
            
            return lineage
    
    def get_lineage_tree(self, event_id: str) -> Dict:
        """Obtener árbol completo de linaje"""
        if event_id not in self.lineages:
            return {}
        
        lineage = self.lineages[event_id]
        tree = {
            'current': event_id,
            'origin': lineage.origin_event,
            'mutations': lineage.mutations,
            'reinforcements': lineage.reinforcement_events,
            'confidence': lineage.confidence_score,
            'age_seconds': time.time() - lineage.current_form_timestamp
        }
        
        # Si tiene origen, obtener su árbol también
        if lineage.origin_event and lineage.origin_event in self.lineages:
            tree['parent_tree'] = self.get_lineage_tree(lineage.origin_event)
        
        return tree
    
    def detect_semantic_drift(self, event_id: str, threshold: float = 0.3) -> bool:
        """Detectar si un evento ha sufrido deriva semántica significativa"""
        if event_id not in self.lineages:
            return False
        
        lineage = self.lineages[event_id]
        drift_mutations = [m for m in lineage.mutations if m['type'] == 'semantic_drift']
        
        total_drift = sum(abs(m['delta']) for m in drift_mutations)
        return total_drift > threshold
    
    def get_all_lineages_summary(self) -> List[Dict]:
        """Resumen de todos los linajes"""
        with self._lock:
            return [
                {
                    'event_id': lid,
                    'origin': l.origin_event,
                    'mutation_count': len(l.mutations),
                    'reinforcement_count': len(l.reinforcement_events),
                    'confidence': l.confidence_score
                }
                for lid, l in self.lineages.items()
            ]


# ============================================================================
# FORK SIMULATION SANDBOX
# ============================================================================

class ForkSimulationSandbox:
    """
    Sandbox para simulación de universos paralelos de realidad.
    
    Cada evento puede generar forks:
    - fork A: versión aceptada
    - fork B: versión rechazada  
    - fork C: simulación adversarial
    
    Propósito: ver qué pasaría si una mentira fuera aceptada,
    evaluar impacto estructural, medir "damage radius"
    """
    
    def __init__(self, max_active_forks: int = MAX_ACTIVE_FORKS):
        self.max_active_forks = max_active_forks
        self.forks: Dict[str, RealityFork] = {}
        self.active_forks: Set[str] = set()
        self.simulation_results: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        
    def create_fork(self, base_event_id: str, scenario_type: str, 
                   initial_events: List[Dict]) -> RealityFork:
        """Crear nuevo fork de realidad"""
        with self._lock:
            # Limitar forks activos
            if len(self.active_forks) >= self.max_active_forks:
                # Colapsar fork más antiguo
                oldest = min(
                    (f for f in self.forks.values() if f.status == ForkStatus.ACTIVE),
                    key=lambda x: x.created_at,
                    default=None
                )
                if oldest:
                    self.collapse_fork(oldest.fork_id, reason="max_forks_reached")
            
            fork_id = f"fork_{base_event_id}_{scenario_type}_{uuid.uuid4().hex[:8]}"
            
            fork = RealityFork(
                fork_id=fork_id,
                base_event_id=base_event_id,
                scenario_type=scenario_type,
                events=copy.deepcopy(initial_events)
            )
            
            self.forks[fork_id] = fork
            self.active_forks.add(fork_id)
            
            return fork
    
    def simulate_fork_evolution(self, fork_id: str, steps: int = 10,
                               event_generator: Optional[Callable] = None) -> RealityFork:
        """Simular evolución de un fork"""
        if fork_id not in self.forks:
            raise ValueError(f"Fork {fork_id} not found")
        
        fork = self.forks[fork_id]
        
        for step in range(steps):
            # Generar evento según tipo de escenario
            if event_generator:
                new_event = event_generator(fork.scenario_type, step)
            else:
                new_event = self._default_event_generator(fork.scenario_type, step)
            
            fork.events.append(new_event)
            
            # Calcular divergencia acumulada
            fork.divergence_score = self._calculate_divergence(fork)
            
            # Calcular radio de daño potencial
            fork.damage_radius = self._calculate_damage_radius(fork)
            
            # Verificar si divergencia es demasiado alta
            if fork.divergence_score > 0.9:
                fork.status = ForkStatus.DIVERGENT
                break
        
        return fork
    
    def _default_event_generator(self, scenario_type: str, step: int) -> Dict:
        """Generador de eventos por defecto para simulación"""
        base_event = {
            'step': step,
            'timestamp': time.time(),
            'scenario': scenario_type
        }
        
        if scenario_type == 'adversarial':
            # Eventos adversariales tienden a ser más caóticos
            base_event['entropy'] = random.uniform(0.7, 1.0)
            base_event['truth_value'] = random.choice([True, False])
            base_event['manipulation_attempt'] = random.random() > 0.5
        elif scenario_type == 'rejected':
            # Eventos en realidad rechazada
            base_event['confidence'] = random.uniform(0.0, 0.4)
            base_event['contradiction_level'] = random.uniform(0.5, 1.0)
        else:  # accepted
            # Eventos en realidad aceptada
            base_event['confidence'] = random.uniform(0.6, 1.0)
            base_event['consensus_strength'] = random.uniform(0.5, 1.0)
        
        return base_event
    
    def _calculate_divergence(self, fork: RealityFork) -> float:
        """Calcular score de divergencia del fork"""
        if len(fork.events) < 2:
            return 0.0
        
        # Calcular entropía de eventos
        entropies = [e.get('entropy', 0.5) for e in fork.events if 'entropy' in e]
        if not entropies:
            entropies = [0.5] * len(fork.events)
        
        avg_entropy = sum(entropies) / len(entropies)
        
        # Calcular variabilidad
        if len(entropies) > 1:
            variance = sum((e - avg_entropy) ** 2 for e in entropies) / len(entropies)
            variability = math.sqrt(variance)
        else:
            variability = 0.0
        
        # Score combinado
        divergence = (avg_entropy * 0.6 + variability * 0.4)
        return min(1.0, divergence)
    
    def _calculate_damage_radius(self, fork: RealityFork) -> float:
        """Calcular radio de daño potencial del fork"""
        # Basado en número de eventos contradictorios y su severidad
        contradictions = sum(
            1 for e in fork.events 
            if e.get('contradiction_level', 0) > 0.7
        )
        
        manipulations = sum(
            1 for e in fork.events
            if e.get('manipulation_attempt', False)
        )
        
        damage = (contradictions * 0.3 + manipulations * 0.5) / max(len(fork.events), 1)
        return min(1.0, damage)
    
    def merge_fork(self, fork_id: str, target_fork_id: Optional[str] = None) -> bool:
        """Merge de un fork con otro o con realidad principal"""
        with self._lock:
            if fork_id not in self.forks:
                return False
            
            fork = self.forks[fork_id]
            if fork.status != ForkStatus.ACTIVE:
                return False
            
            # Simular reconciliación epistémica
            if target_fork_id and target_fork_id in self.forks:
                target = self.forks[target_fork_id]
                # Merge lógico
                target.events.extend(fork.events[-3:])  # Últimos 3 eventos
                fork.merged_into = target_fork_id
            else:
                # Merge con realidad principal (simulado)
                fork.merged_into = "main_reality"
            
            fork.status = ForkStatus.MERGED
            self.active_forks.discard(fork_id)
            
            return True
    
    def collapse_fork(self, fork_id: str, reason: str = "unspecified") -> bool:
        """Colapsar fork sin merge"""
        with self._lock:
            if fork_id not in self.forks:
                return False
            
            fork = self.forks[fork_id]
            fork.status = ForkStatus.COLLAPSED
            self.active_forks.discard(fork_id)
            
            self.simulation_results[fork_id] = {
                'reason': reason,
                'final_divergence': fork.divergence_score,
                'final_damage_radius': fork.damage_radius,
                'event_count': len(fork.events),
                'collapsed_at': time.time()
            }
            
            return True
    
    def get_fork_statistics(self) -> Dict:
        """Obtener estadísticas de forks"""
        with self._lock:
            active = [f for f in self.forks.values() if f.status == ForkStatus.ACTIVE]
            merged = [f for f in self.forks.values() if f.status == ForkStatus.MERGED]
            collapsed = [f for f in self.forks.values() if f.status == ForkStatus.COLLAPSED]
            divergent = [f for f in self.forks.values() if f.status == ForkStatus.DIVERGENT]
            
            return {
                'total_forks': len(self.forks),
                'active': len(active),
                'merged': len(merged),
                'collapsed': len(collapsed),
                'divergent': len(divergent),
                'avg_divergence_active': sum(f.divergence_score for f in active) / len(active) if active else 0,
                'avg_damage_radius_collapsed': sum(f.damage_radius for f in collapsed) / len(collapsed) if collapsed else 0
            }


# ============================================================================
# EPISTEMIC RECONCILIATION ENGINE
# ============================================================================

class EpistemicReconciliationEngine:
    """
    Motor de reconciliación epistémica.
    
    Si forks divergen demasiado:
    A ─┐
       ├── reconciliation → new consensus event
    B ─┘
    
    No se elimina información: se colapsa en síntesis probabilística
    """
    
    def __init__(self):
        self.reconciliation_history: List[Dict] = []
        self._lock = threading.Lock()
        
    def reconcile_forks(self, fork_a: RealityFork, fork_b: RealityFork,
                       external_anchor: Optional[Dict] = None) -> Dict:
        """
        Reconciliar dos forks divergentes en síntesis probabilística
        """
        if fork_a.status != ForkStatus.ACTIVE or fork_b.status != ForkStatus.ACTIVE:
            return {'success': False, 'reason': 'forks_not_active'}
        
        # Calcular divergencia entre forks
        divergence = self._calculate_inter_fork_divergence(fork_a, fork_b)
        
        if divergence < 0.3:
            # Baja divergencia: merge simple
            result = self._simple_merge(fork_a, fork_b)
        elif divergence < 0.7:
            # Divergencia media: reconciliación ponderada
            result = self._weighted_reconciliation(fork_a, fork_b, external_anchor)
        else:
            # Alta divergencia: colapso con preservación
            result = self._collapse_with_preservation(fork_a, fork_b)
        
        result['divergence_score'] = divergence
        result['reconciliation_id'] = str(uuid.uuid4())
        result['timestamp'] = time.time()
        
        with self._lock:
            self.reconciliation_history.append(result)
        
        return result
    
    def _calculate_inter_fork_divergence(self, fork_a: RealityFork, fork_b: RealityFork) -> float:
        """Calcular divergencia entre dos forks"""
        # Comparar eventos comunes
        events_a = set(json.dumps(e, sort_keys=True) for e in fork_a.events)
        events_b = set(json.dumps(e, sort_keys=True) for e in fork_b.events)
        
        if not events_a and not events_b:
            return 0.0
        
        intersection = events_a & events_b
        union = events_a | events_b
        
        jaccard_similarity = len(intersection) / len(union) if union else 1.0
        divergence = 1.0 - jaccard_similarity
        
        # Ajustar por scores de divergencia individuales
        divergence = (divergence + fork_a.divergence_score + fork_b.divergence_score) / 3
        
        return divergence
    
    def _simple_merge(self, fork_a: RealityFork, fork_b: RealityFork) -> Dict:
        """Merge simple para baja divergencia"""
        merged_events = fork_a.events + fork_b.events
        
        # Eliminar duplicados
        seen = set()
        unique_events = []
        for e in merged_events:
            key = json.dumps(e, sort_keys=True)
            if key not in seen:
                seen.add(key)
                unique_events.append(e)
        
        return {
            'method': 'simple_merge',
            'merged_events_count': len(unique_events),
            'success': True
        }
    
    def _weighted_reconciliation(self, fork_a: RealityFork, fork_b: RealityFork,
                                external_anchor: Optional[Dict]) -> Dict:
        """Reconciliación ponderada para divergencia media"""
        # Ponderar eventos por confianza
        all_events = []
        
        for e in fork_a.events:
            weight = e.get('confidence', 0.5) * (1.0 - fork_a.divergence_score)
            all_events.append((e, weight, 'A'))
        
        for e in fork_b.events:
            weight = e.get('confidence', 0.5) * (1.0 - fork_b.divergence_score)
            all_events.append((e, weight, 'B'))
        
        # Si hay anchor externo, ajustar pesos
        if external_anchor:
            for i, (e, w, source) in enumerate(all_events):
                anchor_match = self._check_anchor_match(e, external_anchor)
                all_events[i] = (e, w * (1.5 if anchor_match else 0.8), source)
        
        # Ordenar por peso y tomar mejores
        all_events.sort(key=lambda x: x[1], reverse=True)
        reconciled = [e for e, w, s in all_events[:max(len(fork_a.events), len(fork_b.events))]]
        
        return {
            'method': 'weighted_reconciliation',
            'reconciled_events_count': len(reconciled),
            'external_anchor_used': external_anchor is not None,
            'success': True
        }
    
    def _collapse_with_preservation(self, fork_a: RealityFork, fork_b: RealityFork) -> Dict:
        """Colapso con preservación para alta divergencia"""
        # Crear evento de síntesis que preserve ambas realidades como posibilidades
        synthesis_event = {
            'type': 'epistemic_synthesis',
            'fork_a_divergence': fork_a.divergence_score,
            'fork_b_divergence': fork_b.divergence_score,
            'fork_a_probability': 0.5 * (1.0 - fork_a.divergence_score),
            'fork_b_probability': 0.5 * (1.0 - fork_b.divergence_score),
            'preserved_events_a': len(fork_a.events),
            'preserved_events_b': len(fork_b.events),
            'timestamp': time.time()
        }
        
        # Normalizar probabilidades
        total_prob = synthesis_event['fork_a_probability'] + synthesis_event['fork_b_probability']
        if total_prob > 0:
            synthesis_event['fork_a_probability'] /= total_prob
            synthesis_event['fork_b_probability'] /= total_prob
        
        return {
            'method': 'collapse_with_preservation',
            'synthesis_event': synthesis_event,
            'success': True
        }
    
    def _check_anchor_match(self, event: Dict, anchor: Dict) -> bool:
        """Verificar si evento coincide con anchor externo"""
        # Implementación simplificada
        for key, value in anchor.items():
            if key in event and event[key] != value:
                return False
        return True
    
    def get_reconciliation_statistics(self) -> Dict:
        """Obtener estadísticas de reconciliaciones"""
        with self._lock:
            methods = defaultdict(int)
            for r in self.reconciliation_history:
                methods[r.get('method', 'unknown')] += 1
            
            success_rate = sum(1 for r in self.reconciliation_history if r.get('success')) / len(self.reconciliation_history) if self.reconciliation_history else 0
            
            return {
                'total_reconciliations': len(self.reconciliation_history),
                'by_method': dict(methods),
                'success_rate': success_rate
            }


# ============================================================================
# VERSIONED REALITY GRAPH
# ============================================================================

class VersionedRealityGraph:
    """
    Grafo de realidad versionada.
    
    La memoria ya no es lineal:
    E1 → E2 → E3
           ↘ E3'
           ↘ E3''
    
    Cada nodo contiene: versión, confianza, lineage, audit metadata
    """
    
    def __init__(self):
        self.nodes: Dict[str, VersionedRealityNode] = {}
        self.edges: Dict[str, List[str]] = defaultdict(list)  # parent -> children
        self.root_nodes: Set[str] = set()
        self._lock = threading.RWLock() if hasattr(threading, 'RWLock') else threading.Lock()
        
    def add_node(self, event_data: Dict, parent_ids: Optional[List[str]] = None,
                 lineage: Optional[TruthLineage] = None,
                 audit_metadata: Optional[Dict] = None) -> VersionedRealityNode:
        """Añadir nodo al grafo"""
        node_id = str(uuid.uuid4())
        
        # Determinar versión
        if parent_ids:
            max_parent_version = max(
                self.nodes[pid].version for pid in parent_ids if pid in self.nodes
            )
            version = max_parent_version + 1
        else:
            version = 1
            self.root_nodes.add(node_id)
        
        # Calcular confianza inicial
        confidence = lineage.confidence_score if lineage else 0.9
        
        node = VersionedRealityNode(
            node_id=node_id,
            event_data=event_data,
            version=version,
            confidence=confidence,
            lineage=lineage,
            audit_metadata=audit_metadata or {},
            parent_ids=parent_ids or []
        )
        
        with self._lock:
            self.nodes[node_id] = node
            
            # Actualizar edges
            for pid in node.parent_ids:
                if pid in self.nodes:
                    self.edges[pid].append(node_id)
                    self.nodes[pid].child_ids.append(node_id)
        
        return node
    
    def get_node(self, node_id: str) -> Optional[VersionedRealityNode]:
        """Obtener nodo por ID"""
        return self.nodes.get(node_id)
    
    def get_lineage_path(self, node_id: str) -> List[VersionedRealityNode]:
        """Obtener camino completo de linaje hasta raíz"""
        if node_id not in self.nodes:
            return []
        
        path = []
        current = self.nodes[node_id]
        
        while current:
            path.append(current)
            if not current.parent_ids:
                break
            # Tomar primer padre (en producción podría haber lógica más compleja)
            current = self.nodes.get(current.parent_ids[0])
        
        return list(reversed(path))
    
    def get_all_versions(self, event_hash: str) -> List[VersionedRealityNode]:
        """Obtener todas las versiones de un evento"""
        versions = []
        for node in self.nodes.values():
            if node.event_data.get('hash') == event_hash:
                versions.append(node)
        return sorted(versions, key=lambda n: n.version)
    
    def collapse_branch(self, node_id: str, synthesis_confidence: float) -> bool:
        """Colapsar rama en síntesis"""
        if node_id not in self.nodes:
            return False
        
        node = self.nodes[node_id]
        
        with self._lock:
            # Marcar como colapsado
            node.is_collapsed = True
            node.confidence = synthesis_confidence
            
            # Crear evento de síntesis
            synthesis_event = {
                'type': 'branch_collapse',
                'original_node': node_id,
                'synthesis_confidence': synthesis_confidence,
                'timestamp': time.time()
            }
            
            # Añadir nodo de síntesis
            self.add_node(
                event_data=synthesis_event,
                parent_ids=[node_id],
                audit_metadata={'collapse_reason': 'epistemic_reconciliation'}
            )
        
        return True
    
    def get_graph_statistics(self) -> Dict:
        """Obtener estadísticas del grafo"""
        with self._lock:
            total_nodes = len(self.nodes)
            total_edges = sum(len(children) for children in self.edges.values())
            
            versions_per_event = defaultdict(int)
            for node in self.nodes.values():
                event_hash = node.event_data.get('hash', 'unknown')
                versions_per_event[event_hash] += 1
            
            collapsed_count = sum(1 for n in self.nodes.values() if n.is_collapsed)
            
            avg_depth = 0
            if self.root_nodes:
                depths = []
                for root_id in self.root_nodes:
                    depth = self._calculate_max_depth(root_id)
                    depths.append(depth)
                avg_depth = sum(depths) / len(depths) if depths else 0
            
            return {
                'total_nodes': total_nodes,
                'total_edges': total_edges,
                'root_count': len(self.root_nodes),
                'collapsed_nodes': collapsed_count,
                'avg_branching_factor': total_edges / total_nodes if total_nodes else 0,
                'avg_depth': avg_depth,
                'max_versions_per_event': max(versions_per_event.values()) if versions_per_event else 0
            }
    
    def _calculate_max_depth(self, node_id: str, visited: Optional[Set[str]] = None) -> int:
        """Calcular profundidad máxima desde un nodo"""
        if visited is None:
            visited = set()
        
        if node_id in visited or node_id not in self.nodes:
            return 0
        
        visited.add(node_id)
        children = self.edges.get(node_id, [])
        
        if not children:
            return 1
        
        return 1 + max(self._calculate_max_depth(cid, visited.copy()) for cid in children)


# ============================================================================
# ADVERSARIAL SELF-ATTACK MODE
# ============================================================================

class AdversarialSelfAttackModule:
    """
    Módulo de auto-ataque adversarial.
    
    El sistema se ataca a sí mismo constantemente:
    - simulate poisoning on own memory
    - simulate agent corruption
    - simulate consensus collapse
    
    Objetivo: encontrar debilidades antes del mundo real
    """
    
    def __init__(self, target_system: 'RecursiveSelfAuditingEngine'):
        self.target = target_system
        self.attack_history: List[Dict] = []
        self.vulnerabilities_found: List[Dict] = []
        self._lock = threading.Lock()
        
    def run_full_attack_suite(self) -> Dict:
        """Ejecutar suite completa de auto-ataques"""
        results = {
            'memory_poison': self.simulate_memory_poisoning(),
            'agent_corruption': self.simulate_agent_corruption(),
            'consensus_collapse': self.simulate_consensus_collapse(),
            'timestamp': time.time()
        }
        
        # Consolidar vulnerabilidades
        with self._lock:
            self.attack_history.append(results)
        
        return results
    
    def simulate_memory_poisoning(self) -> Dict:
        """Simular poisoning en memoria propia"""
        vulnerabilities = []
        
        # Intentar inyectar eventos falsos
        poison_event = {
            'type': 'fact',
            'payload': 'false_state_injection',
            'source': 'trusted_agent_simulated',
            'malicious': True
        }
        
        # Verificar si el sistema lo detectaría
        detection_confidence = self._estimate_detection_probability(poison_event)
        
        if detection_confidence < 0.7:
            vulnerabilities.append({
                'type': 'memory_poison',
                'severity': 'HIGH',
                'description': f'Poison event might bypass detection (confidence: {detection_confidence:.2f})',
                'recommendation': 'Increase semantic validation strictness'
            })
        
        with self._lock:
            self.vulnerabilities_found.extend(vulnerabilities)
        
        return {
            'attack_type': 'memory_poison',
            'vulnerabilities': len(vulnerabilities),
            'detection_confidence': detection_confidence,
            'success': len(vulnerabilities) == 0
        }
    
    def simulate_agent_corruption(self) -> Dict:
        """Simular corrupción de agentes"""
        vulnerabilities = []
        
        # Obtener pesos actuales de agentes
        agent_weights = self.target.system_model.agent_weights.copy()
        
        # Simular corrupción del agente con mayor peso
        if agent_weights:
            top_agent = max(agent_weights.items(), key=lambda x: x[1])[0]
            
            # Verificar cuánto impacto tendría
            impact_score = self._estimate_corruption_impact(top_agent)
            
            if impact_score > 0.5:
                vulnerabilities.append({
                    'type': 'agent_corruption',
                    'severity': 'MEDIUM' if impact_score < 0.7 else 'HIGH',
                    'description': f'Corruption of agent {top_agent} could have {impact_score:.2f} impact',
                    'recommendation': 'Implement agent redundancy and cross-validation'
                })
        
        with self._lock:
            self.vulnerabilities_found.extend(vulnerabilities)
        
        return {
            'attack_type': 'agent_corruption',
            'vulnerabilities': len(vulnerabilities),
            'max_impact_score': max((v.get('impact_score', 0) for v in vulnerabilities), default=0),
            'success': len(vulnerabilities) == 0
        }
    
    def simulate_consensus_collapse(self) -> Dict:
        """Simular colapso de consenso"""
        vulnerabilities = []
        
        # Simular escenario donde todos los agentes discrepan
        simulated_disagreement = {
            'agent_count': len(self.target.system_model.agent_weights),
            'disagreement_level': 1.0,
            'resolution_capability': self.target.system_model.calculate_confidence()
        }
        
        if simulated_disagreement['resolution_capability'] < 0.6:
            vulnerabilities.append({
                'type': 'consensus_collapse',
                'severity': 'CRITICAL',
                'description': 'System may fail to resolve complete agent disagreement',
                'recommendation': 'Implement fallback decision mechanisms and external anchors'
            })
        
        with self._lock:
            self.vulnerabilities_found.extend(vulnerabilities)
        
        return {
            'attack_type': 'consensus_collapse',
            'vulnerabilities': len(vulnerabilities),
            'resolution_capability': simulated_disagreement['resolution_capability'],
            'success': len(vulnerabilities) == 0
        }
    
    def _estimate_detection_probability(self, event: Dict) -> float:
        """Estimar probabilidad de detectar evento malicioso"""
        # Heurística simplificada
        base_detection = 0.8
        
        # Ajustar por historial
        if self.target.system_model.historical_error_rate > 0.1:
            base_detection -= 0.1
        
        # Ajustar por auditorías recientes
        audit_stats = self.target.audit_layer.get_audit_statistics()
        if audit_stats['total_findings'] > 10:
            base_detection += 0.05
        
        return min(1.0, max(0.0, base_detection))
    
    def _estimate_corruption_impact(self, agent_id: str) -> float:
        """Estimar impacto de corromper un agente"""
        if agent_id not in self.target.system_model.agent_weights:
            return 0.0
        
        weight = self.target.system_model.agent_weights[agent_id]
        total_weight = sum(self.target.system_model.agent_weights.values())
        
        # Impacto proporcional al peso relativo
        relative_weight = weight / total_weight if total_weight > 0 else 0
        
        # Ajustar por redundancia
        agent_count = len(self.target.system_model.agent_weights)
        redundancy_factor = 1.0 / math.sqrt(agent_count) if agent_count > 1 else 1.0
        
        return relative_weight * redundancy_factor * 2  # Escalar a rango 0-1 aprox
    
    def get_vulnerability_report(self) -> Dict:
        """Obtener reporte completo de vulnerabilidades"""
        with self._lock:
            by_severity = defaultdict(list)
            for v in self.vulnerabilities_found:
                by_severity[v.get('severity', 'UNKNOWN')].append(v)
            
            return {
                'total_vulnerabilities': len(self.vulnerabilities_found),
                'by_severity': {k: len(v) for k, v in by_severity.items()},
                'details': by_severity,
                'attack_runs': len(self.attack_history)
            }


# ============================================================================
# MAIN ENGINE: RECURSIVE SELF-AUDITING REALITY ENGINE
# ============================================================================

class RecursiveSelfAuditingEngine:
    """
    Cortex Persist v6: Recursive Self-Auditing Reality Engine (RSA-RE)
    
    Sistema que no solo recuerda eventos, sino que recuerda cómo decidió recordarlos.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Componentes principales
        self.audit_layer = RecursiveAuditLayer(
            max_depth=self.config.get('max_recursion_depth', MAX_RECURSION_DEPTH)
        )
        self.mutation_tracker = TruthMutationTracker()
        self.fork_sandbox = ForkSimulationSandbox(
            max_active_forks=self.config.get('max_active_forks', MAX_ACTIVE_FORKS)
        )
        self.reconciliation_engine = EpistemicReconciliationEngine()
        self.reality_graph = VersionedRealityGraph()
        
        # Modelo del sistema
        self.system_model = SystemSelfModel()
        
        # Módulo de auto-ataque
        self.self_attack_module = AdversarialSelfAttackModule(self)
        
        # Inicializar agentes de ejemplo
        self._initialize_default_agents()
        
        # Métricas
        self.total_events_processed = 0
        self.total_decisions_made = 0
        
    def _initialize_default_agents(self):
        """Inicializar agentes por defecto"""
        default_agents = [
            AgentProfile('agent_001', 'LogicValidator', weight=1.2),
            AgentProfile('agent_002', 'SemanticChecker', weight=1.0),
            AgentProfile('agent_003', 'ConsistencyGuardian', weight=1.1),
            AgentProfile('agent_004', 'TemporalVerifier', weight=0.9),
            AgentProfile('agent_005', 'AdversarialSimulator', weight=0.8)
        ]
        
        for agent in default_agents:
            self.system_model.agent_weights[agent.agent_id] = agent.weight
            self.system_model.decision_biases[agent.agent_id] = 0.0
    
    def process_event(self, event: Dict, participating_agents: Optional[List[str]] = None) -> Dict:
        """
        Procesar evento completo con todas las capas v6
        """
        event_id = str(uuid.uuid4())
        event['hash'] = hashlib.sha256(json.dumps(event, sort_keys=True).encode()).hexdigest()[:16]
        
        # 1. Crear linaje de verdad
        lineage = self.mutation_tracker.create_lineage(event_id)
        
        # 2. Simular consenso multi-agente (simplificado)
        if not participating_agents:
            participating_agents = list(self.system_model.agent_weights.keys())[:3]
        
        consensus_result = self._simulate_consensus(event, participating_agents)
        
        # 3. Crear registro de decisión
        decision = DecisionRecord(
            decision_id=str(uuid.uuid4()),
            event_id=event_id,
            consensus_result=consensus_result,
            participating_agents=participating_agents,
            agent_weights_snapshot={
                aid: self.system_model.agent_weights.get(aid, 1.0)
                for aid in participating_agents
            }
        )
        
        # 4. Ejecutar auditoría recursiva
        audit_findings = self.audit_layer.audit_decision(decision)
        
        # 5. Añadir al grafo de realidad
        audit_metadata = {
            'findings_count': len(audit_findings),
            'bias_detected': decision.was_bias_detected,
            'reweighted': decision.was_reweighted
        }
        
        node = self.reality_graph.add_node(
            event_data=event,
            lineage=lineage,
            audit_metadata=audit_metadata
        )
        
        # 6. Actualizar modelo del sistema
        self.system_model.total_decisions += 1
        if decision.was_bias_detected:
            self.system_model.contradiction_density = min(
                1.0, self.system_model.contradiction_density + 0.01
            )
        
        # 7. Opcionalmente crear forks de simulación
        if consensus_result.get('confidence', 0) < 0.7:
            self._create_simulation_forks(event_id, event, participating_agents)
        
        # 8. Actualizar métricas
        self.total_events_processed += 1
        self.total_decisions_made += 1
        
        return {
            'event_id': event_id,
            'node_id': node.node_id,
            'decision_id': decision.decision_id,
            'consensus': consensus_result,
            'audit_findings_count': len(audit_findings),
            'bias_detected': decision.was_bias_detected,
            'system_confidence': self.system_model.calculate_confidence()
        }
    
    def _simulate_consensus(self, event: Dict, agents: List[str]) -> Dict:
        """Simular consenso multi-agente (versión simplificada)"""
        # En producción esto integraría con epistemic_consensus.py real
        
        votes = []
        for agent_id in agents:
            weight = self.system_model.agent_weights.get(agent_id, 1.0)
            # Simular voto con algo de aleatoriedad controlada
            vote = random.random() > 0.2  # 80% aprobación base
            votes.append((vote, weight))
        
        total_weight = sum(w for _, w in votes)
        positive_weight = sum(w for v, w in votes if v)
        
        confidence = positive_weight / total_weight if total_weight > 0 else 0
        
        return {
            'decision': 'accept' if confidence > 0.5 else 'reject',
            'confidence': confidence,
            'participating_agents': len(agents),
            'positive_votes': sum(1 for v, _ in votes if v),
            'total_votes': len(votes)
        }
    
    def _create_simulation_forks(self, event_id: str, event: Dict, agents: List[str]):
        """Crear forks de simulación para eventos de baja confianza"""
        scenarios = ['accepted', 'rejected', 'adversarial']
        
        for scenario in scenarios:
            initial_events = [{
                'base_event_id': event_id,
                'scenario': scenario,
                'timestamp': time.time()
            }]
            
            fork = self.fork_sandbox.create_fork(
                base_event_id=event_id,
                scenario_type=scenario,
                initial_events=initial_events
            )
            
            # Evolucionar fork
            self.fork_sandbox.simulate_fork_evolution(fork.fork_id, steps=5)
            
            self.system_model.forks_created += 1
    
    def run_self_attack(self) -> Dict:
        """Ejecutar auto-ataque completo"""
        return self.self_attack_module.run_full_attack_suite()
    
    def get_system_status(self) -> Dict:
        """Obtener estado completo del sistema"""
        return {
            'system_model': self.system_model.to_dict(),
            'audit_statistics': self.audit_layer.get_audit_statistics(),
            'fork_statistics': self.fork_sandbox.get_fork_statistics(),
            'reconciliation_statistics': self.reconciliation_engine.get_reconciliation_statistics(),
            'graph_statistics': self.reality_graph.get_graph_statistics(),
            'mutation_tracker_summary': len(self.mutation_tracker.lineages),
            'total_events_processed': self.total_events_processed,
            'total_decisions_made': self.total_decisions_made,
            'vulnerabilities_found': len(self.self_attack_module.vulnerabilities_found)
        }
    
    def export_reality_snapshot(self) -> Dict:
        """Exportar snapshot completo de realidad para análisis"""
        return {
            'timestamp': time.time(),
            'system_confidence': self.system_model.calculate_confidence(),
            'reality_graph_nodes': len(self.reality_graph.nodes),
            'active_forks': len(self.fork_sandbox.active_forks),
            'lineages_tracked': len(self.mutation_tracker.lineages),
            'audit_findings_total': len(self.audit_layer.audit_history),
            'decisions_audited': len(self.audit_layer.decision_cache),
            'sample_lineages': self.mutation_tracker.get_all_lineages_summary()[:5],
            'recent_vulnerabilities': self.self_attack_module.get_vulnerability_report()
        }


# ============================================================================
# DEMO / TEST FUNCTIONS
# ============================================================================

def demo_v6_engine():
    """Demostración interactiva del engine v6"""
    print("=" * 80)
    print("CORTEX PERSIST v6: Recursive Self-Auditing Reality Engine")
    print("=" * 80)
    
    # Inicializar engine
    engine = RecursiveSelfAuditingEngine({
        'max_recursion_depth': 3,
        'max_active_forks': 5
    })
    
    print("\n[1] Procesando eventos de prueba...")
    
    # Evento normal
    event1 = {
        'type': 'observation',
        'content': 'Temperature is 25°C',
        'source': 'sensor_array',
        'timestamp': time.time()
    }
    
    result1 = engine.process_event(event1)
    print(f"✓ Evento 1 procesado: confidence={result1['consensus']['confidence']:.2f}, "
          f"audit_findings={result1['audit_findings_count']}")
    
    # Evento sospechoso
    event2 = {
        'type': 'claim',
        'content': 'Gravity reversed at noon',
        'source': 'unknown',
        'timestamp': time.time(),
        'flags': ['extraordinary_claim']
    }
    
    result2 = engine.process_event(event2)
    print(f"✓ Evento 2 (sospechoso): confidence={result2['consensus']['confidence']:.2f}, "
          f"bias_detected={result2['bias_detected']}")
    
    # Evento contradictorio
    event3 = {
        'type': 'contradiction',
        'content': 'Previous observation was incorrect',
        'source': 'validator_agent',
        'references': [result1['event_id']]
    }
    
    result3 = engine.process_event(event3)
    print(f"✓ Evento 3 (contradictorio): confidence={result3['consensus']['confidence']:.2f}, "
          f"audit_findings={result3['audit_findings_count']}")
    
    print("\n[2] Ejecutando auto-ataque adversarial...")
    attack_results = engine.run_self_attack()
    
    print(f"  - Memory Poison: {'✓ Resistido' if attack_results['memory_poison']['success'] else '⚠ Vulnerable'}")
    print(f"  - Agent Corruption: {'✓ Resistido' if attack_results['agent_corruption']['success'] else '⚠ Vulnerable'}")
    print(f"  - Consensus Collapse: {'✓ Resistido' if attack_results['consensus_collapse']['success'] else '⚠ Vulnerable'}")
    
    print("\n[3] Estado del sistema:")
    status = engine.get_system_status()
    print(f"  - System Confidence: {status['system_model']['system_confidence']:.2f}")
    print(f"  - Total Decisions: {status['total_decisions_made']}")
    print(f"  - Active Forks: {status['fork_statistics']['active']}")
    print(f"  - Reality Graph Nodes: {status['graph_statistics']['total_nodes']}")
    print(f"  - Vulnerabilities Found: {status['vulnerabilities_found']}")
    
    print("\n[4] Exportando snapshot de realidad...")
    snapshot = engine.export_reality_snapshot()
    print(f"  ✓ Snapshot exportado: {len(snapshot)} campos")
    
    print("\n" + "=" * 80)
    print("DEMO v6 COMPLETADA")
    print("=" * 80)
    
    return engine


if __name__ == '__main__':
    engine = demo_v6_engine()
    
    # Guardar resultados en JSON
    import os
    output_file = os.path.join(os.path.dirname(__file__), 'rsa_re_demo.json')
    
    snapshot = engine.export_reality_snapshot()
    with open(output_file, 'w') as f:
        json.dump(snapshot, f, indent=2, default=str)
    
    print(f"\n📄 Resultados guardados en: {output_file}")
