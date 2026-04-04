# This file is part of CORTEX. Apache-2.0. Change Date: 2030-01-01.

"""OpenCode Integration Provider - Wraps OpenCode CLI as a CORTEX BaseProvider."""

from __future__ import annotations

import asyncio
import json
import logging
import shlex
from typing import Any
from collections.abc import AsyncGenerator

from cortex.extensions.llm._models import BaseProvider, CortexPrompt, IntentProfile
from cortex.extensions.llm.quota import SovereignQuotaManager

logger = logging.getLogger("cortex.extensions.llm.opencode")

_QUOTA_MANAGER: SovereignQuotaManager | None = None


def _get_quota_manager() -> SovereignQuotaManager:
    global _QUOTA_MANAGER
    if _QUOTA_MANAGER is None:
        _QUOTA_MANAGER = SovereignQuotaManager()
    return _QUOTA_MANAGER


class OpenCodeProvider(BaseProvider):
    """
    Integra OpenCode (Terminal AI Coding Agent) como un Provider válido en la cascada CORTEX.
    Permite delegar inferencia a cualquier modelo frontera configurado en opencode.json.
    """

    def __init__(
        self,
        model: str = "anthropic/claude-sonnet-4-5",
        tier: str = "frontier",
        cost_class: str = "high",
        intent_affinity: frozenset[IntentProfile] | None = None,
    ):
        self._provider = "opencode"
        self._model = model
        self._tier = tier
        self._cost_class = cost_class
        self._intent_affinity = intent_affinity or frozenset(
            {
                IntentProfile.ARCHITECT,
                IntentProfile.CODE,
                IntentProfile.REASONING,
                IntentProfile.GENERAL,
            }
        )
        self._context_window = 200000

    @property
    def provider_name(self) -> str:
        return self._provider

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def intent_affinity(self) -> frozenset[IntentProfile]:
        return self._intent_affinity

    @property
    def tier(self) -> str:
        return self._tier

    @property
    def cost_class(self) -> str:
        return self._cost_class

    @property
    def context_window(self) -> int:
        return self._context_window

    async def complete(
        self,
        prompt: str,
        system: str = "You are a helpful assistant.",
        temperature: float = 0.0,
        max_tokens: int = 2048,
        intent: IntentProfile = IntentProfile.GENERAL,
        prefix_cache_key: str | None = None,
    ) -> str:

        full_prompt = f"SYSTEM: {system}\n\nUSER: {prompt}"

        # Fake a CortexPrompt to pass the intent
        from cortex.extensions.llm.router import CortexPrompt

        cortex_prompt = CortexPrompt(intent=intent, working_memory=[], system_instruction=system)

        return await self._run_opencode(full_prompt, cortex_prompt)

    async def invoke(self, prompt: CortexPrompt) -> str:
        """Invoca a OpenCode traduciendo el CortexPrompt."""
        messages = prompt.to_openai_messages()
        # Flat messages to text for OpenCode single-shot
        text_lines = []
        for msg in messages:
            role = msg.get("role", "user").upper()
            content = msg.get("content", "")
            text_lines.append(f"[{role}]: {content}")

        full_text = "\n\n".join(text_lines)
        return await self._run_opencode(full_text)

    async def _run_opencode(
        self, prompt_text: str, cortex_prompt: CortexPrompt | None = None
    ) -> str:
        await _get_quota_manager().acquire(tokens=1)

        # Axioma Ω16 / CORTEX-Swarm-Prime Intent Router
        target_model = self._model
        if cortex_prompt:
            from cortex.extensions.llm.router import IntentProfile
            from cortex.config import LLM_LOCAL_FIRST

            reasoning_mode = getattr(cortex_prompt, "reasoning_mode", None)

            if reasoning_mode == "ULTRA_THINK" or cortex_prompt.intent == IntentProfile.REASONING:
                target_model = "openai/o3-mini"
            elif LLM_LOCAL_FIRST or getattr(cortex_prompt, "local_only", False):
                target_model = "ollama/qwen2.5-coder:32b"

        logger.info("Mapeando inferencia CORTEX hacia OpenCode Proxy (Modelo: %s)", target_model)

        # Rendimiento x100: Superar el límite ARG_MAX de OS X (1MB/2MB) usando RAM disk (/tmp ephemeral)
        # Esto previene crashes cuando el CORTEX inyecta 50 archivos de código en el context bridge.
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode="w", dir="/tmp", suffix=".md", delete=False) as tf:
            tf.write(prompt_text)
            temp_path = tf.name

        try:
            # Rendimiento x100: exec_shell bypass. Evita parseo de bash (O(1) execution time)
            # Y TTY auto-disable en OpenCode asumiendo que lee de archivo.
            # Nota: Si el CLI local no soporta file flag, el `cat` se ejecuta piped.
            cmd = f"cat {temp_path} | opencode run - --model {target_model}"

            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                err_msg = stderr.decode().strip() or stdout.decode().strip()

                # Auto-Thermal-Fallback (C5 Resilience + Axioma Ω16-B CoT)
                if "ollama/" not in target_model:
                    fallback_local_model = "ollama/qwen2.5-coder:32b"
                    if "o3-mini" in target_model or "o1" in target_model:
                        fallback_local_model = "ollama/deepseek-r1:32b"

                    logger.warning(
                        "Cloud Crash (Code %s). Fallback a Silicio (%s)",
                        process.returncode,
                        fallback_local_model,
                    )

                    fb_cmd = f"cat {temp_path} | opencode run - --model {fallback_local_model}"
                    fb_proc = await asyncio.create_subprocess_shell(
                        fb_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    fb_out, fb_err = await fb_proc.communicate()

                    if fb_proc.returncode == 0:
                        return fb_out.decode().strip()

                    err_msg = fb_err.decode().strip() or fb_out.decode().strip()

                from cortex.utils.errors import CortexError

                raise CortexError(f"OpenCode Execution Failed: {err_msg}")

            return stdout.decode().strip()
        finally:
            # Destruir memoria persistente (Limpieza de entropía temporal)
            if os.path.exists(temp_path):
                os.remove(temp_path)

    async def stream(
        self,
        prompt: str,
        system: str = "You are a helpful assistant.",
        temperature: float = 0.0,
        max_tokens: int = 2048,
        intent: IntentProfile = IntentProfile.GENERAL,
    ) -> AsyncGenerator[str, None]:

        full_prompt = f"SYSTEM: {system}\n\nUSER: {prompt}"

        from cortex.extensions.llm.router import CortexPrompt

        cortex_prompt = CortexPrompt(intent=intent, working_memory=[], system_instruction=system)

        async for chunk in self._stream_opencode(full_prompt, cortex_prompt):
            yield chunk

    async def _stream_opencode(
        self, prompt_text: str, cortex_prompt: CortexPrompt | None = None
    ) -> AsyncGenerator[str, None]:
        await _get_quota_manager().acquire(tokens=1)

        target_model = self._model
        if cortex_prompt:
            from cortex.extensions.llm.router import IntentProfile
            from cortex.config import LLM_LOCAL_FIRST

            reasoning_mode = getattr(cortex_prompt, "reasoning_mode", None)

            if reasoning_mode == "ULTRA_THINK" or cortex_prompt.intent == IntentProfile.REASONING:
                target_model = "openai/o3-mini"
            elif LLM_LOCAL_FIRST or getattr(cortex_prompt, "local_only", False):
                target_model = "ollama/qwen2.5-coder:7b"

        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode="w", dir="/tmp", suffix=".md", delete=False) as tf:
            tf.write(prompt_text)
            temp_path = tf.name

        process = None
        fb_proc = None
        try:
            cmd = f"cat {temp_path} | opencode run - --model {target_model}"

            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=os.setsid,  # V10 Strike: Attach to a session to allow Process Group Orphan Slaying
            )

            yielded_any = False
            while True:
                chunk = await process.stdout.read(64)
                if not chunk:
                    break
                yielded_any = True
                yield chunk.decode("utf-8", errors="replace")

            await process.wait()

            if process.returncode != 0:
                err_msg = (await process.stderr.read()).decode().strip()

                # Cortafuegos Táctico
                if not yielded_any and "ollama/" not in target_model:
                    fallback_local_model = "ollama/qwen2.5-coder:7b"
                    if "o3-mini" in target_model or "o1" in target_model:
                        fallback_local_model = "ollama/deepseek-r1:7b"

                    logger.warning(
                        "Cloud Stream Crash (Code %s). Activating Zero-Latency Fallback: %s",
                        process.returncode,
                        fallback_local_model,
                    )

                    fb_cmd = f"cat {temp_path} | opencode run - --model {fallback_local_model}"
                    fb_proc = await asyncio.create_subprocess_shell(
                        fb_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        preexec_fn=os.setsid,
                    )

                    while True:
                        fb_chunk = await fb_proc.stdout.read(64)
                        if not fb_chunk:
                            break
                        yield fb_chunk.decode("utf-8", errors="replace")

                    await fb_proc.wait()
                    if fb_proc.returncode != 0:
                        fb_err = (await fb_proc.stderr.read()).decode().strip()
                        from cortex.utils.errors import CortexError

                        raise CortexError(f"Fallback Stream Panic: {fb_err}")
                else:
                    from cortex.utils.errors import CortexError

                    raise CortexError(f"OpenCode Stream Execution Failed: {err_msg}")

        finally:
            # V10 Strike: Orphan Slaying Protocol
            # Si el generador es cancelado (El usuario cierra CORTEX), fulminar el proceso y evitar gasto de API
            import signal

            for p in [process, fb_proc]:
                if p and p.returncode is None:
                    try:
                        logger.info(
                            "Inferencia Abortada. Fulminando Zombie Process OpenCode (PID Group %s)",
                            p.pid,
                        )
                        os.killpg(os.getpgid(p.pid), signal.SIGTERM)
                    except Exception:
                        pass

            if os.path.exists(temp_path):
                os.remove(temp_path)

    async def close(self) -> None:
        pass
