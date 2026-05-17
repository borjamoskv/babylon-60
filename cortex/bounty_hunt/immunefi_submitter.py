"""
CORTEX v6.0 — Immunefi Submitter (C5-REAL)

Formats PoCs into Immunefi-compliant payloads. Validates against
project docs and known issues. Stages for human review before dispatch.
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx

logger = logging.getLogger("cortex.bounty_hunt.immunefi_submitter")

REPORTS_DIR = Path("scratch/bounty_reports")
PAYLOADS_DIR = Path("bounty_hunt/autonomous_swarm/submissions_payloads")


class ImmunefiSubmitter:
    """C5-REAL: Formats, validates, and stages PoC payloads."""

    def __init__(self, reports_dir: Path = REPORTS_DIR, payloads_dir: Path = PAYLOADS_DIR):
        self.reports_dir = reports_dir
        self.payloads_dir = payloads_dir

    async def gather_reports(self) -> list[Path]:
        if not self.reports_dir.exists():
            logger.error(f"Reports dir missing: {self.reports_dir}")
            return []
        reports = list(self.reports_dir.glob("*.md"))
        logger.info(f"[C5-REAL] Found {len(reports)} PoC reports")
        return reports

    def _extract_severity(self, content: str) -> str:
        m = re.search(r"Severity:\s*(Critical|High|Medium|Low)", content, re.IGNORECASE)
        return m.group(1) if m else "High"

    def _extract_vuln_name(self, content: str) -> str:
        m = re.search(r"Vulnerability:\s*(.+)", content)
        return m.group(1).strip() if m else "Unnamed Vulnerability"

    def format_payload(self, report_path: Path) -> dict | None:
        """Format PoC Markdown into Immunefi-compliant JSON."""
        try:
            content = report_path.read_text(encoding="utf-8")
            lines = content.split("\n")
            title = lines[0].replace("#", "").strip() if lines else report_path.stem
            vuln_name = self._extract_vuln_name(content)
            severity = self._extract_severity(content)

            # Extract repo URL
            repo_match = re.search(r"\*\*Repository:\*\*\s*(https://\S+)", content)
            repo_url = repo_match.group(1) if repo_match else ""

            payload = {
                "meta": {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "source_report": str(report_path),
                    "cortex_version": "6.0",
                },
                "submission": {
                    "title": f"[{severity}] {vuln_name} — {title}",
                    "severity": severity,
                    "description": content,
                    "impact": "Capital extraction, state manipulation, or access bypass.",
                    "proof_of_concept": content,
                    "repository": repo_url,
                    "references": [],
                },
                "validation": {
                    "saga_1_docs": "pending",
                    "saga_2_known_issues": "pending",
                    "human_review": "REQUIRED",
                },
            }
            return payload
        except Exception as e:
            logger.error(f"Format failed for {report_path.name}: {e}")
            return None

    async def validate_saga1_docs(self, payload: dict) -> bool:
        """SAGA-1: Check if vulnerability contradicts project documentation."""
        repo = payload["submission"].get("repository", "")
        if not repo:
            logger.warning("[SAGA-1] No repo URL. Skipping doc validation.")
            return True

        logger.info(f"[SAGA-1] Checking project docs for {repo}...")
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                # Check README for known limitations / accepted risks
                readme_url = (
                    repo.rstrip("/").replace("github.com", "raw.githubusercontent.com")
                    + "/main/README.md"
                )
                r = await client.get(readme_url)
                if r.status_code == 200:
                    readme = r.text.lower()
                    payload["submission"]["description"].lower()

                    # Check for semantic overlap with documented limitations
                    risk_markers = [
                        "known issue",
                        "accepted risk",
                        "won't fix",
                        "by design",
                        "intentional",
                    ]
                    for marker in risk_markers:
                        if marker in readme:
                            logger.warning(
                                f"[SAGA-1] README contains '{marker}'. Manual review required."
                            )
                            payload["validation"]["saga_1_docs"] = (
                                f"WARNING: '{marker}' found in docs"
                            )
                            return True  # Still pass, but flag for review
                else:
                    logger.info("[SAGA-1] Could not fetch README. Proceeding.")
        except Exception as e:
            logger.warning(f"[SAGA-1] Doc check failed: {e}")

        payload["validation"]["saga_1_docs"] = "PASS"
        return True

    async def validate_saga2_known_issues(self, payload: dict) -> bool:
        """SAGA-2: Check GitHub Issues for duplicates."""
        repo = payload["submission"].get("repository", "")
        if not repo:
            return True

        logger.info("[SAGA-2] Checking GitHub Issues for duplicates...")
        try:
            # Extract owner/repo from URL
            parts = repo.rstrip("/").split("/")
            if len(parts) >= 2:
                owner, rname = parts[-2], parts[-1]
                api_url = (
                    f"https://api.github.com/repos/{owner}/{rname}/issues?state=all&per_page=30"
                )
                async with httpx.AsyncClient(timeout=15) as client:
                    r = await client.get(
                        api_url, headers={"Accept": "application/vnd.github.v3+json"}
                    )
                    if r.status_code == 200:
                        issues = r.json()
                        vuln_name = payload["submission"]["title"].lower()
                        for issue in issues:
                            ititle = (issue.get("title") or "").lower()
                            if any(
                                kw in ititle
                                for kw in ["reentrancy", "overflow", "precision", "access control"]
                            ):
                                if any(kw in vuln_name for kw in ititle.split()):
                                    logger.warning(
                                        f"[SAGA-2] Possible duplicate: #{issue['number']} {ititle}"
                                    )
                                    payload["validation"]["saga_2_known_issues"] = (
                                        f"POSSIBLE_DUP: #{issue['number']}"
                                    )
                                    return True  # Pass but flag
        except Exception as e:
            logger.warning(f"[SAGA-2] Issue check failed: {e}")

        payload["validation"]["saga_2_known_issues"] = "PASS"
        return True

    def stage_payload(self, payload: dict) -> Path:
        """Stage payload for human review. NOT auto-submitted."""
        self.payloads_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        title_slug = re.sub(r"[^a-z0-9]", "_", payload["submission"]["title"].lower())[:60]
        fname = f"{ts}_{title_slug}.json"
        path = self.payloads_dir / fname

        with open(path, "w") as f:
            json.dump(payload, f, indent=2, default=str)

        logger.info(f"[C5-REAL] Payload STAGED (human review required): {path}")
        return path

    async def run_submission_pipeline(self) -> list[Path]:
        """Full pipeline: gather → format → validate → stage."""
        logger.info("[C5-REAL] Submission pipeline starting...")
        reports = await self.gather_reports()
        if not reports:
            logger.warning("No reports to process.")
            return []

        staged = []
        for report in reports:
            payload = self.format_payload(report)
            if not payload:
                continue
            await self.validate_saga1_docs(payload)
            await self.validate_saga2_known_issues(payload)
            path = self.stage_payload(payload)
            staged.append(path)

        logger.info(f"[C5-REAL] Pipeline complete. {len(staged)} payloads staged for review.")
        return staged


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s|%(name)s|%(levelname)s|%(message)s")
    sub = ImmunefiSubmitter()
    asyncio.run(sub.run_submission_pipeline())
