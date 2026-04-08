"""LinkedIn AI Commentary Generator.

Uses the CORTEX LLM Router (cascade: gemini → openai → groq → deepseek)
to transform raw markdown article content into a high-impact LinkedIn post
(commentary field). Enforces the 3000-char LinkedIn limit.

Usage::

    commentary = await generate_linkedin_commentary(
        title="...",
        body="...",
        provider="gemini",   # or "auto" to cascade
    )
"""

from __future__ import annotations

import asyncio
import logging
from typing import Literal

logger = logging.getLogger("cortex.darknet.linkedin_ai")

# LinkedIn commentary hard limit
_LINKEDIN_MAX_CHARS = 3000

# Cascade order: Gemini (free tier) → OpenAI → Groq (free) → DeepSeek
_CASCADE: list[str] = ["gemini", "openai", "groq", "deepseek"]

_SYSTEM_PROMPT = """You are an elite LinkedIn ghostwriter for technical founders.

Rules (NON-NEGOTIABLE):
1. Output ONLY the LinkedIn post text — no preamble, no "Here is...", no markdown headers.
2. Max 3000 characters (hard LinkedIn limit). Stay under 2800 to be safe.
3. Start with a strong 1-line hook (no hashtag, no emoji overload).
4. Use short paragraphs (1-3 lines). NO bullet walls.
5. Include 3-5 hashtags at the very end, separated from body by a blank line.
6. Tone: confident builder, zero corporate jargon, zero buzzwords.
7. Language: detect from article title and match it (Spanish if Spanish, English if English).
8. The post should make technical people stop scrolling.
"""


async def generate_linkedin_commentary(
    title: str,
    body: str,
    provider: Literal["gemini", "openai", "groq", "deepseek", "openrouter", "auto"] = "auto",
    temperature: float = 0.7,
) -> tuple[str, str]:
    """Generate LinkedIn commentary from article content.

    Returns:
        (commentary_text, provider_used)

    Raises:
        RuntimeError: if all providers in the cascade fail.
    """
    from cortex.extensions.llm.provider import LLMProvider

    prompt = _build_prompt(title, body)
    providers_to_try = _CASCADE if provider == "auto" else [provider]

    last_error: Exception | None = None
    for p_name in providers_to_try:
        try:
            logger.info("LinkedIn AI: trying provider=%s", p_name)
            llm = LLMProvider(provider=p_name)
            raw = await llm.complete(
                prompt=prompt,
                system=_SYSTEM_PROMPT,
                temperature=temperature,
                max_tokens=1024,
            )
            await llm.close()

            commentary = _clean_output(raw)
            if not commentary:
                raise ValueError("Empty response from LLM")

            logger.info(
                "LinkedIn AI: OK provider=%s chars=%d", p_name, len(commentary)
            )
            return commentary, p_name

        except Exception as e:
            logger.warning("LinkedIn AI: provider=%s failed: %s", p_name, e)
            last_error = e
            continue

    raise RuntimeError(
        f"All LLM providers failed. Last error: {last_error}"
    )


def generate_linkedin_commentary_sync(
    title: str,
    body: str,
    provider: str = "auto",
    temperature: float = 0.7,
) -> tuple[str, str]:
    """Sync wrapper for use in Click commands (not inside existing event loops)."""
    return asyncio.run(
        generate_linkedin_commentary(
            title=title,
            body=body,
            provider=provider,  # type: ignore[arg-type]
            temperature=temperature,
        )
    )


def _build_prompt(title: str, body: str) -> str:
    """Build the LLM prompt from article metadata."""
    # Sanitize body: strip non-UTF8 chars that could break downstream regex
    body_clean = body.encode("utf-8", errors="replace").decode("utf-8")
    body_excerpt = body_clean[:4000]  # Trim to avoid oversized context
    return (
        f"Write a LinkedIn post for this article.\n\n"
        f"TITLE: {title}\n\n"
        f"ARTICLE CONTENT (excerpt):\n{body_excerpt}\n\n"
        f"Remember: output ONLY the LinkedIn post text, max 2800 chars."
    )


def _clean_output(raw: str) -> str:
    """Strip LLM preamble/markdown artifacts and enforce char limit."""
    text = raw.strip()

    # Drop common preamble lines
    preamble_prefixes = (
        "here is", "here's", "sure", "of course",
        "linkedin post:", "post:", "---",
    )
    lines = text.splitlines()
    while lines and lines[0].lower().startswith(preamble_prefixes):
        lines = lines[1:]
    text = "\n".join(lines).strip()

    # Strip markdown bold/italic artifacts
    for md in ("**", "__", "##", "# "):
        text = text.replace(md, "")

    # Enforce LinkedIn hard limit
    if len(text) > _LINKEDIN_MAX_CHARS:
        # Truncate at last sentence boundary before limit
        truncated = text[:_LINKEDIN_MAX_CHARS]
        last_period = max(
            truncated.rfind(". "),
            truncated.rfind(".\n"),
        )
        if last_period > _LINKEDIN_MAX_CHARS * 0.7:
            text = truncated[:last_period + 1]
        else:
            text = truncated.rstrip() + "…"

    return text
