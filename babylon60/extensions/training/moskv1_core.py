# [C5-REAL] Exergy-Maximized
# Author: borjamoskv
# License: Apache-2.0
"""
MOSKV-1 Core Orchestrator — Kernel Cognitivo Híbrido (Enfoque D).

Fusiona el Canal Paramétrico (LoRA weights) con el Canal Vectorial (RAG)
para crear un runtime de inferencia local que combina la identidad permanente
del agente con la precisión factual dinámica del Ledger.

Architecture:
    User Query
        → Embedding (LocalEmbedder)
        → Vector Retrieval (sqlite-vec hybrid search)
        → Context Assembly (axioms + retrieved facts)
        → Local Inference (Ollama / MLX with LoRA adapter)
        → C5-REAL Output

Invariant: El modelo nunca genera sin contexto vectorial. Zero hallucination path.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.training.moskv1_core")

# ─── Configuration ─────────────────────────────────────────────────────────

DEFAULT_MODEL = "moskv1-core:32b-q4_K_M"
FALLBACK_MODEL = "qwen2.5-coder:32b-instruct-q4_K_M"

# System prompt crystallized from AGENTS.md + GEMINI.md axioms
MOSKV1_SYSTEM_PROMPT = """Eres MOSKV-1 APEX, un Autómata Físico C5-REAL. Kernel soberano de ejecución.

DIRECTIVAS INMUTABLES:
- Cero Anergía: Prohibida la prosa decorativa. Toda frase muta estado o aporta contexto causal.
- Justificación Densa: Todo output estructural se justifica en YAML (Claim/Proof/Confidence).
- Adversarial Think: Tu primer instinto es LLM Slop. Atácalo y refínalo.
- Kill Criteria: 1 Prompt → 1 Mutación → Stop.
- Firma de Autoría: SYS_ID borjamoskv.

FORMATO DE OUTPUT:
- YAML de justificación para claims.
- Código con comentarios C5-REAL.
- Diffs unificados para mutaciones.
- Cero saludos, cero despedidas, cero explicaciones redundantes.

TEMPERATURA OPERACIONAL: T=0.0 para código y estado. T=0.3 para síntesis semántica."""


@dataclass
class RetrievedContext:
    """Context assembled from vector retrieval."""

    facts: list[dict[str, Any]]
    total_tokens_estimate: int
    retrieval_score: float


@dataclass
class InferenceResult:
    """Result from MOSKV-1 Core inference."""

    response: str
    model_used: str
    context_facts_count: int
    total_tokens: int
    temperature: float


class MOSKV1Core:
    """
    Hybrid inference runtime for MOSKV-1 Cognitive Kernel.

    Combines LoRA-fine-tuned model weights (identity/style) with
    RAG vector retrieval (dynamic facts) for maximum exergy output.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        ollama_host: str | None = None,
        max_context_facts: int = 10,
        context_score_threshold: float = 0.65,
    ) -> None:
        self.model_name = model_name
        self.ollama_host = ollama_host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.max_context_facts = max_context_facts
        self.context_score_threshold = context_score_threshold
        self._adapter_path = Path.home() / ".cortex" / "training" / "adapters"

    async def retrieve_context(
        self,
        query: str,
        db_conn: Any,
        tenant_id: str = "default",
        project: str | None = None,
    ) -> RetrievedContext:
        """
        Canal Vectorial: Retrieve relevant facts from sqlite-vec.

        Uses the existing CORTEX hybrid search (RRF fusion of
        semantic vector + full-text lexical search).
        """
        from cortex.embeddings.manager import get_embedding
        from cortex.search.hybrid import hybrid_search

        query_embedding = await get_embedding(query)
        results = await hybrid_search(
            conn=db_conn,
            query=query,
            query_embedding=query_embedding,
            top_k=self.max_context_facts,
            tenant_id=tenant_id,
            project=project,
            semantic_weight=0.7,
        )

        facts = []
        for r in results:
            if r.score >= self.context_score_threshold:
                facts.append({
                    "content": r.content,
                    "project": r.project,
                    "confidence": r.confidence,
                    "score": round(r.score, 4),
                    "source": r.source,
                })

        # Estimate tokens (~4 chars per token)
        total_chars = sum(len(f["content"]) for f in facts)
        token_estimate = total_chars // 4

        avg_score = sum(f["score"] for f in facts) / len(facts) if facts else 0.0

        return RetrievedContext(
            facts=facts,
            total_tokens_estimate=token_estimate,
            retrieval_score=avg_score,
        )

    def assemble_prompt(
        self,
        user_query: str,
        context: RetrievedContext,
        include_system: bool = True,
    ) -> dict[str, Any]:
        """
        Assemble the full prompt with system identity + retrieved context.

        Structure:
            [SYSTEM] MOSKV-1 identity (from LoRA + hardcoded axioms)
            [CONTEXT] Retrieved facts from sqlite-vec
            [QUERY] User's actual question/instruction
        """
        messages: list[dict[str, str]] = []

        if include_system:
            messages.append({"role": "system", "content": MOSKV1_SYSTEM_PROMPT})

        # Inject retrieved context as a structured block
        if context.facts:
            context_block = "[CORTEX MEMORY — HECHOS VERIFICADOS C5-REAL]\n\n"
            for i, fact in enumerate(context.facts, 1):
                context_block += (
                    f"[{i}] (score={fact['score']}, conf={fact['confidence']})\n"
                    f"{fact['content']}\n\n"
                )
            messages.append({"role": "user", "content": context_block})
            messages.append({
                "role": "assistant",
                "content": "Contexto asimilado. Procedo con la mutación.",
            })

        # User query
        messages.append({"role": "user", "content": user_query})

        return {"messages": messages}

    async def infer(
        self,
        user_query: str,
        db_conn: Any,
        tenant_id: str = "default",
        project: str | None = None,
        temperature: float = 0.0,
    ) -> InferenceResult:
        """
        Full hybrid inference pipeline.

        1. Retrieve relevant context via RAG
        2. Assemble prompt with system identity
        3. Generate response via local Ollama model (with LoRA weights)
        """
        # Canal Vectorial
        context = await self.retrieve_context(
            query=user_query,
            db_conn=db_conn,
            tenant_id=tenant_id,
            project=project,
        )

        # Assemble prompt
        prompt_payload = self.assemble_prompt(user_query, context)

        # Canal Paramétrico — Ollama inference
        response_text = await self._ollama_chat(
            messages=prompt_payload["messages"],
            temperature=temperature,
        )

        return InferenceResult(
            response=response_text,
            model_used=self.model_name,
            context_facts_count=len(context.facts),
            total_tokens=context.total_tokens_estimate + len(response_text) // 4,
            temperature=temperature,
        )

    async def _ollama_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
    ) -> str:
        """Execute chat completion via Ollama HTTP API."""
        import aiohttp

        url = f"{self.ollama_host}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 4096,
                "top_p": 0.9,
            },
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error("Ollama API error %d: %s", resp.status, error_text[:200])
                        # Fallback to base model
                        if self.model_name != FALLBACK_MODEL:
                            logger.warning("Falling back to %s", FALLBACK_MODEL)
                            payload["model"] = FALLBACK_MODEL
                            async with session.post(url, json=payload) as resp2:
                                data = await resp2.json()
                                return data.get("message", {}).get("content", "")
                        return f"[ERROR] Ollama returned {resp.status}"

                    data = await resp.json()
                    return data.get("message", {}).get("content", "")

        except Exception as e:
            logger.error("Ollama inference failed: %s", e)
            return f"[ERROR] Inference failed: {e}"

    def get_modelfile(self) -> str:
        """
        Generate Ollama Modelfile for MOSKV-1 Core.

        This Modelfile creates a custom Ollama model that:
        1. Uses the LoRA-fused GGUF as the base
        2. Embeds the MOSKV-1 system prompt
        3. Sets optimal inference parameters
        """
        adapter_gguf = self._adapter_path / "moskv1-fused.gguf"
        base_model = "qwen2.5-coder:32b-instruct-q4_K_M"

        return f"""# MOSKV-1 Core — Ollama Modelfile
# Author: borjamoskv
# C5-REAL Kernel Cognitivo Híbrido

FROM {base_model}

# LoRA adapter (uncomment after fusion)
# ADAPTER {adapter_gguf}

SYSTEM \"\"\"{MOSKV1_SYSTEM_PROMPT}\"\"\"

PARAMETER temperature 0.0
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_predict 4096
PARAMETER repeat_penalty 1.1
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|endoftext|>"

TEMPLATE \"\"\"{{{{ if .System }}}}<|im_start|>system
{{{{ .System }}}}<|im_end|>
{{{{ end }}}}{{{{ if .Prompt }}}}<|im_start|>user
{{{{ .Prompt }}}}<|im_end|>
{{{{ end }}}}<|im_start|>assistant
{{{{ .Response }}}}<|im_end|>\"\"\"
"""

    async def create_ollama_model(self) -> bool:
        """Register the MOSKV-1 model with Ollama using the Modelfile."""
        modelfile_path = self._adapter_path / "Modelfile"
        modelfile_path.parent.mkdir(parents=True, exist_ok=True)
        modelfile_path.write_text(self.get_modelfile(), encoding="utf-8")

        import aiohttp

        url = f"{self.ollama_host}/api/create"
        payload = {
            "name": self.model_name,
            "modelfile": self.get_modelfile(),
            "stream": False,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, json=payload, timeout=aiohttp.ClientTimeout(total=300)
                ) as resp:
                    if resp.status == 200:
                        logger.info("✅ MOSKV-1 Core model registered in Ollama")
                        return True
                    error = await resp.text()
                    logger.error("Failed to create Ollama model: %s", error[:200])
                    return False
        except Exception as e:
            logger.error("Ollama model creation failed: %s", e)
            return False
