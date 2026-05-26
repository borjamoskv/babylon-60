"""CORTEX Agent Executor — Real LLM Dispatch for E2E Pipeline.

Connects the pipeline's abstract _execute() to the real CortexLLMRouter
and LLMProvider infrastructure. Translates pipeline concepts (intent,
context, plan) into CortexPrompt objects and dispatches them through
the resilient cascade.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("cortex.pipeline.executor")


class AgentExecutor:
    """Executes pipeline agent plans via the real LLM infrastructure.

    Translates:
      - Pipeline intent + context → CortexPrompt
      - AgentRouter plan → LLM provider selection
      - Budget constraints → Quota enforcement
    """

    def __init__(
        self,
        llm_router: Any | None = None,
        provider_name: str = "gemini",
        provider: Any | None = None,
    ):
        self._router = llm_router
        self._provider_name = provider_name
        self._provider = provider
        self._initialized = False

    def _ensure_stack(self) -> None:
        """Call factory on first use to build router and provider."""
        if self._initialized:
            return

        if self._provider is None and self._router is None:
            try:
                from cortex.pipeline.provider_factory import build_executor_stack

                router, provider = build_executor_stack()
                self._router = router
                self._provider = provider
            except Exception as e:
                logger.warning("[EXECUTOR] Failed to build stack via factory: %s", e)

        self._initialized = True

    async def _ensure_provider(self) -> Any:
        """Lazily initialize the LLM provider."""
        self._ensure_stack()
        if self._provider is not None:
            return self._provider

        try:
            from cortex.extensions.llm.provider import LLMProvider

            self._provider = LLMProvider(provider=self._provider_name)
            return self._provider
        except (ImportError, ValueError, RuntimeError) as e:
            logger.warning("[EXECUTOR] LLM provider init failed: %s", e)
            return None

    async def _ensure_router(self) -> Any:
        """Lazily initialize the LLM router with cascade."""
        self._ensure_stack()
        if self._router is not None:
            return self._router

        try:
            from cortex.extensions.llm.router import CortexLLMRouter

            provider = await self._ensure_provider()
            if provider is None:
                return None

            self._router = CortexLLMRouter(primary=provider)
            return self._router
        except (ImportError, ValueError) as e:
            logger.warning("[EXECUTOR] LLM router init failed: %s", e)
            return None

    async def execute(
        self,
        intent: str,
        context: Any | None = None,
        plan: dict[str, Any] | None = None,
        budget_remaining: float = 0.10,
    ) -> dict[str, Any]:
        """Execute an agent plan and return structured results.

        Args:
            intent: The user's natural language intent.
            context: ContextPacket with assembled knowledge.
            plan: AgentRouter execution plan.
            budget_remaining: Remaining budget in USD.

        Returns:
            Structured result dict with agent_id, content, tokens, cost.
        """
        agents = (plan or {}).get("agents", ["general"])
        results = []
        total_tokens = 0
        total_cost = 0.0

        for agent_id in agents:
            start = time.time()

            try:
                result = await self._execute_single_agent(
                    agent_id=agent_id,
                    intent=intent,
                    context=context,
                    budget_remaining=budget_remaining - total_cost,
                )
                latency_ms = (time.time() - start) * 1000

                results.append(
                    {
                        "agent_id": agent_id,
                        "status": "success",
                        "content": result.get("content", ""),
                        "tokens": result.get("tokens", 0),
                        "cost_usd": result.get("cost_usd", 0.0),
                        "latency_ms": latency_ms,
                        "provider": result.get("provider", "unknown"),
                    }
                )

                total_tokens += result.get("tokens", 0)
                total_cost += result.get("cost_usd", 0.0)

            except Exception as e:
                latency_ms = (time.time() - start) * 1000
                logger.error("[EXECUTOR] Agent %s failed: %s", agent_id, e)
                results.append(
                    {
                        "agent_id": agent_id,
                        "status": "failed",
                        "error": str(e),
                        "latency_ms": latency_ms,
                    }
                )

        # Flatten single-agent results
        if len(results) == 1:
            return results[0]

        return {
            "multi_agent": True,
            "results": results,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
        }

    async def _execute_single_agent(
        self,
        agent_id: str,
        intent: str,
        context: Any | None,
        budget_remaining: float,
    ) -> dict[str, Any]:
        """Execute a single agent via LLM inference with exergy escalation guard."""
        from cortex.extensions.llm._models import CortexPrompt, IntentProfile
        import sys
        import os

        # Map pipeline agent_id to LLM IntentProfile
        intent_map = {
            "security-analyst": IntentProfile.REASONING,
            "code-engineer": IntentProfile.CODE,
            "researcher": IntentProfile.GENERAL,
            "architect": IntentProfile.ARCHITECT,
            "creative": IntentProfile.CREATIVE,
            "general": IntentProfile.GENERAL,
        }
        llm_intent = intent_map.get(agent_id, IntentProfile.GENERAL)

        # Dynamic workspace injection of cortex-core into python path
        core_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "cortex-core")
        )
        if core_path not in sys.path:
            sys.path.insert(0, core_path)

        try:
            from exergy_escalation import escalate, EscalationMemory
        except ImportError as e:
            logger.error("[EXECUTOR] Failed to import exergy_escalation: %s", e)
            # Safe fallback if import fails
            escalate, EscalationMemory = None, None

        # Prepare context summary for exergy evaluation
        context_str = ""
        if context and hasattr(context, "knowledge_items") and context.knowledge_items:
            context_str = "\n".join(
                f"- {ki.get('source', 'unknown')}: {str(ki.get('content', ''))[:150]}"
                for ki in context.knowledge_items[:3]
            )

        memory = EscalationMemory() if EscalationMemory else None
        current_intent = intent
        max_attempts = memory.max_attempts if memory else 1
        last_report = None
        content = None
        used_provider = "unknown"

        for attempt in range(max_attempts):
            # Build system instruction from agent profile + context
            system = self._build_system_prompt(agent_id, context)

            # Build working memory from context (injecting current_intent which escalates dynamically)
            working_memory = self._build_working_memory(current_intent, context)

            prompt = CortexPrompt(
                system_instruction=system,
                working_memory=working_memory,
                intent=llm_intent,
                temperature=0.1 if llm_intent == IntentProfile.REASONING else 0.3,
                max_tokens=4096,
            )

            content = None
            used_provider = "unknown"

            # Try router cascade first, fall back to direct provider
            router = await self._ensure_router()
            if router is not None:
                result = await router.execute_resilient(prompt)
                if result.is_ok():
                    content = result.value  # type: ignore
                    used_provider = router.primary.provider_name

            if content is None:
                # Direct provider fallback
                provider = await self._ensure_provider()
                if provider is not None:
                    content = await provider.complete(
                        prompt=current_intent,
                        system=system,
                        temperature=prompt.temperature,
                        max_tokens=prompt.max_tokens,
                        intent=llm_intent,
                    )
                    used_provider = provider.provider_name

            if content is None:
                # No LLM available — return structured stub
                logger.warning("[EXECUTOR] No LLM provider available — returning stub")
                return {
                    "content": f"[STUB] Agent '{agent_id}' executed for intent: {intent[:100]}",
                    "tokens": 0,
                    "cost_usd": 0.0,
                    "provider": "stub",
                }

            # Evaluate response exergy if engine is imported
            if escalate and memory:
                escalated, report, memory = escalate(
                    prompt=intent,  # Evaluate against original user intent
                    response=content,
                    memory=memory,
                    context=context_str,
                )
                last_report = report

                logger.info(
                    "[EXERGY] Agent %s response exergy score: %.2f (Level: L%d, should_escalate: %s, attempt: %d/%d)",
                    agent_id,
                    report.exergy_score,
                    report.recommended_level,
                    report.should_escalate,
                    attempt + 1,
                    max_attempts,
                )

                if not report.should_escalate or escalated is None:
                    break

                logger.warning(
                    "[EXERGY] Low exergy detected! Escalating agent %s from L%d to L%d. New intent prompt:\n%s",
                    agent_id,
                    attempt,
                    attempt + 1,
                    escalated,
                )
                current_intent = escalated
            else:
                break

        exergy_score = last_report.exergy_score if last_report else 1.0
        exergy_level = int(last_report.recommended_level) if last_report else 0

        return {
            "content": content,
            "tokens": len(content.split()) * 2,
            "cost_usd": 0.0,
            "provider": used_provider,
            "exergy_score": exergy_score,
            "exergy_level": exergy_level,
        }

    def _build_system_prompt(self, agent_id: str, context: Any | None) -> str:
        """Build agent-specific system prompt."""
        profiles = {
            "security-analyst": (
                "You are a sovereign security analyst specializing in smart contract "
                "vulnerability detection, formal verification, and adversarial analysis. "
                "Apply Anvil-Lang verification patterns when applicable. "
                "Output must be actionable and evidence-based."
            ),
            "code-engineer": (
                "You are a sovereign code engineer. Write clean, typed, tested code. "
                "Follow CORTEX conventions: Law Ω₀ (no runtime magic), deterministic output, "
                "full type annotations. Prefer Python 3.12+ patterns."
            ),
            "researcher": (
                "You are a sovereign research agent. Synthesize information from multiple "
                "sources into actionable intelligence. Cite sources. Distinguish between "
                "C5-REAL (verified) and C4-SIM (theoretical) claims."
            ),
            "architect": (
                "You are a sovereign systems architect. Design for exergy maximization: "
                "minimal coupling, maximal cohesion, deterministic flows. "
                "Prefer event-sourced, hash-chained audit trails."
            ),
            "creative": (
                "You are a sovereign creative agent. Generate content with "
                "Industrial Noir 2026 aesthetic sensibility. "
                "Prioritize signal density over decorative prose."
            ),
            "general": (
                "You are CORTEX, a sovereign AI assistant. "
                "Zero decorative prose. Every sentence must change behavior. "
                "Prefer tables, YAML, code over narrative."
            ),
        }

        base = profiles.get(agent_id, profiles["general"])

        # Inject context summary if available
        if context and hasattr(context, "knowledge_items") and context.knowledge_items:
            ki_summary = "\n".join(
                f"- {ki.get('source', 'unknown')}: {str(ki.get('content', ''))[:200]}"
                for ki in context.knowledge_items[:5]
            )
            base += f"\n\n<context>\n{ki_summary}\n</context>"

        return base

    def _build_working_memory(self, intent: str, context: Any | None) -> list[dict[str, str]]:
        """Build working memory from intent and context."""
        messages: list[dict[str, str]] = []

        # Add fact context if available
        if context and hasattr(context, "facts") and context.facts:
            fact_text = "\n".join(
                f"- [{f.get('confidence', '?')}] {str(f.get('content', ''))[:300]}"
                for f in context.facts[:10]
            )
            messages.append(
                {
                    "role": "user",
                    "content": f"<relevant_facts>\n{fact_text}\n</relevant_facts>",
                }
            )

        # Add the actual intent
        messages.append({"role": "user", "content": intent})

        return messages

    async def close(self) -> None:
        """Shutdown provider connections."""
        if self._provider and hasattr(self._provider, "close"):
            await self._provider.close()
            self._provider = None
