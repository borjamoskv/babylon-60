"""Vector L — Pitch Composer and Dispatcher.

Composes personalized outreach emails using Gemini 3.1 Pro and dispatches
via SMTP (primary) or LinkedIn DM (optional, requires session cookie).

Pitch structure:
    1. Specific bottleneck callout (from signals)
    2. CORTEX agent value proposition
    3. Pricing tier and outcome
    4. CTA with reply link

Rate limiting: 24h cooldown per company enforced by Ledger timestamp check.
A/B variants tracked via Ledger tag pitch_variant.
"""

from __future__ import annotations

import asyncio
import logging
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger("cortex.agents.vector_l.pitcher")


# ── Pitch Templates (fallback if LLM fails) ───────────────────────────────────

_PITCH_TEMPLATE = """\
Subject: {subject}

Hi {first_name},

I came across {company} and noticed {bottleneck_observation}.

Most companies your size are losing {hours_estimate}+ hours per month on exactly this —
and the fix isn't hiring more people, it's deploying the right automation layer.

I build CORTEX agents: autonomous AI systems that handle {bottleneck_area} end-to-end.
They integrate with your existing tools, run 24/7, and cost ${tier}/month.

For {company}, the immediate wins would be:
• {win_1}
• {win_2}
• {win_3}

No setup fees. First week free.

Would a 20-minute call next week make sense? Just reply to this email.

Best,
{sender_name}
"""

_SUBJECTS = [
    "Quick question about {company}'s operations",
    "How {company} could save {hours_estimate}h/month automatically",
    "AI agent for {company} — {tier}/mo, first week free",
]

_BOTTLENECK_AREAS = {
    "linkedin": "operations and administrative workflows",
    "glassdoor": "manual processes and repetitive tasks",
    "indeed": "data entry and back-office operations",
    "github_org": "technical operations and tooling",
}

_WIN_TEMPLATES = {
    "high": [
        "Automate data entry and reconciliation (saves ~{h1}h/week)",
        "Auto-classify and route support tickets",
        "Generate weekly reports from raw data — zero manual work",
    ],
    "medium": [
        "Streamline email triage and response drafting",
        "Auto-sync data between your tools (no more copy-paste)",
        "Automated follow-up sequences for leads and clients",
    ],
    "low": [
        "Basic reporting automation",
        "Email template generation from data",
        "Scheduled data exports and summaries",
    ],
}


# ── LLM Composer ──────────────────────────────────────────────────────────────


class PitchComposer:
    """Composes personalized pitch emails using Gemini 3.1 Pro.

    Falls back to template-based composition if LLM unavailable.
    """

    MODEL = "gemini-2.0-flash"  # fastest acceptable model under Ω₇

    def __init__(self) -> None:
        self._api_key = os.environ.get("GEMINI_API_KEY", "")

    async def compose(
        self,
        company: str,
        signals_summary: str,
        tier: int,
        sources: list[str],
        sender_name: str = "Borja",
        recipient_name: str = "",
        domain: str | None = None,
    ) -> dict[str, str]:
        """Return {'subject': ..., 'body': ..., 'variant': 'llm'|'template'}."""

        hours_estimate = {500: 20, 1000: 35, 2000: 60}.get(tier, 20)
        primary_source = sources[0] if sources else "linkedin"
        bottleneck_area = _BOTTLENECK_AREAS.get(primary_source, "operations")
        first_name = recipient_name.split()[0] if recipient_name else "there"
        tier_band = "high" if tier >= 1500 else "medium" if tier >= 800 else "low"
        wins = _WIN_TEMPLATES[tier_band]

        if self._api_key:
            try:
                body = await self._llm_compose(
                    company=company,
                    signals_summary=signals_summary,
                    tier=tier,
                    bottleneck_area=bottleneck_area,
                    hours_estimate=hours_estimate,
                    sender_name=sender_name,
                    first_name=first_name,
                    wins=wins,
                )
                subject = _SUBJECTS[0].format(company=company, hours_estimate=hours_estimate, tier=f"${tier}")
                return {"subject": subject, "body": body, "variant": "llm"}
            except Exception as exc:  # noqa: BLE001
                logger.warning("LLM compose failed, falling back to template: %s", exc)

        # Template fallback
        subject = _SUBJECTS[hash(company) % len(_SUBJECTS)].format(
            company=company, hours_estimate=hours_estimate, tier=f"${tier}"
        )
        body = _PITCH_TEMPLATE.format(
            subject=subject,
            first_name=first_name,
            company=company,
            bottleneck_observation=f"you have several {bottleneck_area} roles that could be automated",
            hours_estimate=hours_estimate,
            bottleneck_area=bottleneck_area,
            tier=tier,
            win_1=wins[0].format(h1=max(hours_estimate // 3, 4)),
            win_2=wins[1],
            win_3=wins[2],
            sender_name=sender_name,
        )
        return {"subject": subject, "body": body, "variant": "template"}

    async def _llm_compose(
        self,
        company: str,
        signals_summary: str,
        tier: int,
        bottleneck_area: str,
        hours_estimate: int,
        sender_name: str,
        first_name: str,
        wins: list[str],
    ) -> str:
        """Call Gemini to compose a personalized pitch."""
        try:
            import google.generativeai as genai  # type: ignore[import-untyped]
        except ImportError:
            raise RuntimeError("google-generativeai not installed") from None

        genai.configure(api_key=self._api_key)
        model = genai.GenerativeModel(self.MODEL)

        prompt = f"""\
You are a senior B2B sales consultant who specializes in AI automation for small businesses.
Write a short, personalized cold email (under 200 words) to pitch an AI agent service.

Company: {company}
Evidence of bottleneck: {signals_summary}
Main pain area: {bottleneck_area}
Monthly price: ${tier}
Estimated hours saved/month: {hours_estimate}h
Sender name: {sender_name}
Recipient first name: {first_name}
Key wins to mention: {'; '.join(wins)}

Rules:
- Do NOT open with "I hope this email finds you well" or similar filler
- Be specific about their bottleneck using the evidence
- One clear CTA: reply to schedule a 20-min call
- Tone: direct, human, not salesy
- DO NOT mention AI, machine learning, or GPT — say "autonomous agent" or "automation layer"
- Sign with {sender_name}'s name only

Output: just the email body, no subject line, no markdown.
"""
        response = model.generate_content(prompt)
        return response.text.strip()


# ── Email Dispatcher ──────────────────────────────────────────────────────────


class EmailDispatcher:
    """Async SMTP dispatcher using aiosmtplib (with smtplib fallback)."""

    def __init__(self) -> None:
        self.host = os.environ.get("VECTOR_L_SMTP_HOST", "smtp.gmail.com")
        self.port = int(os.environ.get("VECTOR_L_SMTP_PORT", "587"))
        self.user = os.environ.get("VECTOR_L_SMTP_USER", "")
        self.password = os.environ.get("VECTOR_L_SMTP_PASS", "")
        self.sender_email = os.environ.get("VECTOR_L_SENDER_EMAIL", self.user)

    @property
    def configured(self) -> bool:
        return bool(self.user and self.password)

    async def send(
        self,
        to_email: str,
        subject: str,
        body: str,
        dry_run: bool = False,
    ) -> bool:
        """Send email. Returns True on success.

        Args:
            to_email: recipient email address
            subject: email subject line
            body: plain-text email body
            dry_run: if True, log only — do not send

        Returns:
            True if sent (or dry_run), False on failure
        """
        if not self.configured:
            logger.warning(
                "[EmailDispatcher] SMTP not configured. Set VECTOR_L_SMTP_* env vars."
            )
            return False

        if dry_run:
            logger.info(
                "[EmailDispatcher] DRY RUN → %s | Subject: %s | Body preview: %.80s",
                to_email,
                subject,
                body,
            )
            return True

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.sender_email
        msg["To"] = to_email
        msg.attach(MIMEText(body, "plain"))

        try:
            # Prefer aiosmtplib for async
            try:
                import aiosmtplib  # type: ignore[import-untyped]

                await aiosmtplib.send(
                    msg,
                    hostname=self.host,
                    port=self.port,
                    username=self.user,
                    password=self.password,
                    start_tls=True,
                )
            except ImportError:
                # Fallback to sync smtplib in thread executor
                await asyncio.get_event_loop().run_in_executor(
                    None, self._send_sync, msg
                )

            logger.info("[EmailDispatcher] ✉️  Sent to %s | %s", to_email, subject)
            return True

        except Exception as exc:  # noqa: BLE001
            logger.error("[EmailDispatcher] Send failed to %s: %s", to_email, exc)
            return False

    def _send_sync(self, msg: MIMEMultipart) -> None:
        context = ssl.create_default_context()
        with smtplib.SMTP(self.host, self.port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(self.user, self.password)
            server.sendmail(self.sender_email, msg["To"], msg.as_string())


# ── LinkedIn Dispatcher ───────────────────────────────────────────────────────


class LinkedInDispatcher:
    """Optional LinkedIn DM dispatcher via headless Playwright.

    Requires VECTOR_L_LINKEDIN_SESSION (li_at cookie value).
    Gracefully skips if session cookie absent.
    """

    def __init__(self) -> None:
        self._session_cookie = os.environ.get("VECTOR_L_LINKEDIN_SESSION", "")

    @property
    def configured(self) -> bool:
        return bool(self._session_cookie)

    async def send_dm(
        self,
        profile_url: str,
        message: str,
        dry_run: bool = False,
    ) -> bool:
        """Send a LinkedIn DM to a profile URL. Returns True on success."""
        if not self.configured:
            logger.debug("[LinkedInDispatcher] No session cookie. Skipping DM.")
            return False

        if dry_run:
            logger.info(
                "[LinkedInDispatcher] DRY RUN → %s | msg: %.60s",
                profile_url,
                message,
            )
            return True

        try:
            from playwright.async_api import async_playwright  # type: ignore[import-untyped]
        except ImportError:
            logger.warning("[LinkedInDispatcher] playwright not installed. Skipping.")
            return False

        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                ctx = await browser.new_context()
                await ctx.add_cookies(
                    [
                        {
                            "name": "li_at",
                            "value": self._session_cookie,
                            "domain": ".linkedin.com",
                            "path": "/",
                        }
                    ]
                )
                page = await ctx.new_page()
                await page.goto(profile_url, timeout=20_000)
                # Click "Message" button if available
                try:
                    await page.click('button:has-text("Message")', timeout=5_000)
                    await asyncio.sleep(1.0)
                    await page.fill('[placeholder="Write a message…"]', message)
                    await page.keyboard.press("Enter")
                    await asyncio.sleep(1.0)
                    logger.info("[LinkedInDispatcher] DM sent to %s", profile_url)
                    return True
                except Exception:  # noqa: BLE001
                    logger.warning(
                        "[LinkedInDispatcher] Could not send DM to %s (no message button?)",
                        profile_url,
                    )
                    return False
                finally:
                    await browser.close()

        except Exception as exc:  # noqa: BLE001
            logger.error("[LinkedInDispatcher] Error: %s", exc)
            return False
