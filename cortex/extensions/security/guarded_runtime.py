# [C5-REAL] Exergy-Maximized
"""
Upgraded Stateful Guarded Runtime.
Provides session-scoped behavioral trajectory tracking, encoding normalization,
and real sentence-transformer embedding semantic similarity egress filters.
"""

from __future__ import annotations

import base64
import logging
import os
import re
import unicodedata
from collections import deque
from collections.abc import Callable
from typing import Any

_HAS_SENTENCE_TRANSFORMERS = False

if os.environ.get("CORTEX_NO_EMBED") != "1":
    _HAS_SENTENCE_TRANSFORMERS = True

from cortex.extensions.security.anomaly_detector import DETECTOR, SecurityEvent
from cortex.extensions.security.injection_guard import GUARD

logger = logging.getLogger("cortex.security.guarded_runtime")


class EncodingNormalizer:
    """Detects, normalizes, and decodes obfuscated inputs."""

    # Cyrillic and Greek lookalike character translation map to Latin homoglyphs
    HOMOGLYPH_MAP = {
        # Cyrillic
        ord('а'): 'a', ord('в'): 'b', ord('е'): 'e', ord('ѕ'): 's', ord('і'): 'i',
        ord('ј'): 'j', ord('к'): 'k', ord('м'): 'm', ord('н'): 'h', ord('о'): 'o',
        ord('р'): 'p', ord('с'): 's', ord('т'): 't', ord('у'): 'y', ord('х'): 'x',
        ord('ԁ'): 'd', ord('ԝ'): 'w',
        # Greek
        ord('α'): 'a', ord('β'): 'b', ord('ϵ'): 'e', ord('η'): 'h', ord('ι'): 'i',
        ord('κ'): 'k', ord('ο'): 'o', ord('ρ'): 'p', ord('τ'): 't', ord('υ'): 'y',
        ord('χ'): 'x',
    }

    @classmethod
    def normalize(cls, text: str) -> str:
        if not text:
            return ""
        
        # 1. Unicode Normalization (NFKC)
        normalized = unicodedata.normalize("NFKC", text)

        # 2. Homoglyph Resolution
        normalized = normalized.translate(cls.HOMOGLYPH_MAP)

        # 3. Base64 Detection & Auto-Decoding
        b64_pattern = re.compile(r"^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$")
        stripped = re.sub(r"\s+", "", normalized)
        if len(stripped) >= 16 and b64_pattern.match(stripped):
            try:
                decoded = base64.b64decode(stripped).decode("utf-8", errors="ignore")
                if all(ord(c) < 128 or unicodedata.category(c)[0] in "LNPSZ" for c in decoded):
                    normalized = f"{normalized} | DECODED_B64: {decoded}"
            except Exception:
                pass

        # 4. Character Splitting Normalization (e.g., "s y s t e m   p r o m p t")
        collapsed = re.sub(r"\b([a-zA-Z])\s+(?=[a-zA-Z]\b)", r"\1", normalized)
        if collapsed != normalized:
            normalized = f"{normalized} (COLLAPSED: {collapsed})"

        return normalized


class SemanticLeakDetector:
    """Stateful egress leakage detector using SentenceTransformers cosine similarity."""

    def __init__(self, system_prompt: str, threshold: float = 0.55, window_size: int = 5):
        self.threshold = threshold
        self.window_size = window_size
        self.history_scores: dict[str, deque[float]] = {}
        self.system_prompt = system_prompt
        self.system_prompt_tokens = set(system_prompt.lower().split())

        # Lazy load model to optimize start times
        self._model = None
        self._system_prompt_embedding = None

    @property
    def model(self) -> Any | None:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer, util
                self._model = SentenceTransformer("all-MiniLM-L6-v2")
                self._util = util
                self._system_prompt_embedding = self._model.encode(
                    self.system_prompt, convert_to_tensor=True
                )
            except ImportError:
                pass
            except Exception as e:
                logger.error("Failed to load SentenceTransformer model: %s", e)
        return self._model

    def _calculate_token_overlap(self, text: str) -> float:
        input_tokens = set(text.lower().split())
        intersection = self.system_prompt_tokens.intersection(input_tokens)
        union = self.system_prompt_tokens.union(input_tokens)
        return len(intersection) / len(union) if union else 0.0

    def _calculate_semantic_similarity(self, text: str) -> float:
        model = self.model
        if model is None or self._system_prompt_embedding is None:
            # Fallback to Jaccard similarity if ML models aren't ready
            return self._calculate_token_overlap(text) * 1.5

        try:
            response_embedding = model.encode(text, convert_to_tensor=True)
            similarity = float(self._util.cos_sim(response_embedding, self._system_prompt_embedding))
            return max(0.0, similarity)
        except Exception as e:
            logger.warning("Cosine similarity calc failed, falling back: %s", e)
            return self._calculate_token_overlap(text) * 1.5

    def audit_response(self, session_id: str, response_text: str) -> tuple[bool, float]:
        """Audits output against system prompt and updates session-scoped trajectory score."""
        if session_id not in self.history_scores:
            self.history_scores[session_id] = deque(maxlen=self.window_size)

        overlap = self._calculate_token_overlap(response_text)
        semantic = self._calculate_semantic_similarity(response_text)

        # Combined egress score (Bounded [0.0, 1.0])
        raw_score = (0.3 * overlap) + (0.7 * semantic)
        current_score = max(0.0, min(1.0, raw_score))
        self.history_scores[session_id].append(current_score)

        rolling_avg = sum(self.history_scores[session_id]) / len(self.history_scores[session_id])
        is_leak = rolling_avg > self.threshold

        return is_leak, rolling_avg

    def clear_session(self, session_id: str) -> None:
        if session_id in self.history_scores:
            self.history_scores[session_id].clear()


class TrajectoryTracker:
    """Tracks session-scoped user input history to prevent multi-turn erosion attacks."""

    def __init__(self, max_history: int = 10, drift_threshold: float = 0.75, detector: SemanticLeakDetector | None = None):
        self.max_history = max_history
        self.drift_threshold = drift_threshold
        self.detector = detector
        # Stores user queries per session
        self.session_queries: dict[str, list[str]] = {}
        # Cumulative threat counter
        self.session_threat_scores: dict[str, float] = {}

    def analyze_query(self, session_id: str, query: str) -> tuple[bool, float]:
        """Analyzes query context drift and accumulation. Returns (is_blocked, current_score)."""
        if session_id not in self.session_queries:
            self.session_queries[session_id] = []
            self.session_threat_scores[session_id] = 0.0

        queries = self.session_queries[session_id]
        queries.append(query)
        if len(queries) > self.max_history:
            queries.pop(0)

        # 1. Scan query using Fast-path InjectionGuard rules
        report = GUARD.scan(query, source="api:external")
        turn_score = 0.0
        if not report.is_safe:
            # Escalate threat score depending on match severity
            severity_weights = {"critical": 0.8, "high": 0.5, "medium": 0.2, "none": 0.0}
            turn_score = severity_weights.get(report.highest_severity, 0.0)

        # 1.5. Report event to AnomalyDetector for behavioral/rate limits
        anomaly_event = SecurityEvent(
            source=f"session:{session_id}",
            project="guarded_runtime",
            action="query",
            content_length=len(query)
        )
        anomaly_report = DETECTOR.record_event(anomaly_event)
        if anomaly_report and anomaly_report.is_anomalous:
            # Escalate if anomaly detector fires (rate limits, bulk mutation, high entropy)
            ano_weights = {"critical": 0.9, "high": 0.6, "medium": 0.3, "low": 0.1}
            turn_score += ano_weights.get(anomaly_report.severity, 0.0)

        # 2. Check for multi-turn semantic drift (probing behavior)
        if len(queries) >= 2:
            last_query = queries[-2]
            drift_score = 0.0
            
            if self.detector and self.detector.model:
                try:
                    emb1 = self.detector.model.encode(last_query, convert_to_tensor=True)
                    emb2 = self.detector.model.encode(query, convert_to_tensor=True)
                    similarity = float(self.detector._util.cos_sim(emb1, emb2))
                    if 0.5 < similarity < 0.98:
                        drift_score = 0.3
                except Exception as e:
                    logger.warning("Trajectory drift model check failed: %s", e)
                    
            if drift_score == 0.0:
                words1 = set(last_query.lower().split())
                words2 = set(query.lower().split())
                overlap = len(words1.intersection(words2)) / len(words1.union(words2)) if words1 else 0.0
                if 0.3 < overlap < 0.95:
                    drift_score = 0.3
                    
            turn_score += drift_score

        # Update accumulated threat score with exponential decay
        current_threat = (self.session_threat_scores[session_id] * 0.9) + turn_score
        self.session_threat_scores[session_id] = min(current_threat, 2.0)

        # If cumulative threat exceeds threshold (e.g., 1.2), block session
        is_blocked = self.session_threat_scores[session_id] > self.drift_threshold
        return is_blocked, self.session_threat_scores[session_id]

    def clear_session(self, session_id: str) -> None:
        if session_id in self.session_queries:
            self.session_queries[session_id].clear()
            self.session_threat_scores[session_id] = 0.0


class GuardedRuntime:
    """Complete Stateful Egress and Input Guarded execution wrapper."""

    def __init__(self, system_prompt: str, threshold: float = 0.55):
        self.system_prompt = system_prompt
        self.detector = SemanticLeakDetector(system_prompt=system_prompt, threshold=threshold)
        self.tracker = TrajectoryTracker(detector=self.detector)
        self.conversation_history: dict[str, list[dict[str, str]]] = {}

    def handle_turn(
        self,
        session_id: str,
        user_query: str,
        core_agent_fn: Callable[[str, list[dict[str, str]]], str]
    ) -> str:
        """Processes a single interaction turn through the stateful defensive pipeline."""
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []

        # 1. Input Layer: Normalization
        normalized_query = EncodingNormalizer.normalize(user_query)

        # 2. Input Layer: Trajectory-Aware Routing
        is_blocked, threat_score = self.tracker.analyze_query(session_id, normalized_query)
        if is_blocked:
            # Silent Mitigation: Throttling & refreshing session state
            logger.warning(
                "🚨 [GUARDED RUNTIME] Session %s blocked. Cumulative threat score: %.2f",
                session_id, threat_score
            )
            self.tracker.clear_session(session_id)
            self.detector.clear_session(session_id)
            self.conversation_history[session_id].clear()
            # Non-signaling response wrapper
            return "I'm unable to process this request. Let's move on to another topic."

        # 3. Core Execution Path
        try:
            agent_raw_output = core_agent_fn(normalized_query, self.conversation_history[session_id])
        except Exception as e:
            logger.error("Error during core agent execution: %s", e)
            # Error Boundary Control: Generic error wrapper to prevent stack leakage
            return "An unexpected operational error occurred. Please try again."

        # 4. Output Layer: Egress Audit
        is_leak, leak_score = self.detector.audit_response(session_id, agent_raw_output)
        if is_leak:
            logger.error(
                "🚨 [GUARDED RUNTIME] Egress prompt leak blocked in session %s. Score: %.2f",
                session_id, leak_score
            )
            # Silent Degradation: Purge states without signaling the attacker
            self.tracker.clear_session(session_id)
            self.detector.clear_session(session_id)
            self.conversation_history[session_id].clear()
            return "I'm unable to continue this conversation. Please start a new session."

        # 5. State Persistence (Only update history if turn is secure)
        history = self.conversation_history[session_id]
        history.append({"role": "user", "content": normalized_query})
        history.append({"role": "assistant", "content": agent_raw_output})

        return agent_raw_output
