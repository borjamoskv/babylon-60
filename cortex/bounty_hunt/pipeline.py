"""
CORTEX v6.0 — Bounty Hunt Pipeline Orchestrator (C5-REAL)

Connects: OSINT Scraper → Repo Clone → Fuzzing → PoC → SAGA Validation → Staging
CLI: python -m cortex.bounty_hunt.pipeline --target <url> | --auto
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from cortex.bounty_hunt.immunefi_fuzzer import ImmunefiFuzzer
from cortex.bounty_hunt.immunefi_submitter import ImmunefiSubmitter
from cortex.bounty_hunt.osint_scraper import BountyScraper

logger = logging.getLogger("cortex.bounty_hunt.pipeline")


async def run_single_target(
    repo_url: str, project: str = "", max_files: int = 20, dry_run: bool = False
):
    """Audit a single repository end-to-end."""
    logger.info(f"[C5-REAL] Single target pipeline: {repo_url}")

    # Phase 1: Fuzzing
    fuzzer = ImmunefiFuzzer(repo_url, project_name=project)
    reports = await fuzzer.run_campaign(max_files=max_files)

    if not reports:
        logger.info("[C5-REAL] No vulnerabilities found. Pipeline clean exit.")
        return []

    # Phase 2: Submission staging
    if dry_run:
        logger.info(f"[DRY-RUN] {len(reports)} findings. Skipping submission staging.")
        return reports

    submitter = ImmunefiSubmitter()
    staged = await submitter.run_submission_pipeline()

    logger.info(f"[C5-REAL] Pipeline complete. {len(staged)} payloads staged for human review.")
    return staged


async def run_auto_osint(max_targets: int = 5, max_files: int = 10, dry_run: bool = False):
    """Full autonomous loop: OSINT → Fuzzing → Staging."""
    logger.info("[C5-REAL] Autonomous OSINT pipeline starting...")

    # Phase 0: OSINT
    scraper = BountyScraper()
    try:
        targets = await scraper.run_osint_loop()
    finally:
        scraper.close()

    if not targets:
        logger.warning("[C5-REAL] No targets from OSINT. Aborting.")
        return

    # Phase 1+2: Audit each target
    total_staged = []
    for i, target in enumerate(targets[:max_targets]):
        logger.info(f"\n{'=' * 60}")
        logger.info(
            f"[C5-REAL] Target {i + 1}/{min(len(targets), max_targets)}: "
            f"{target['project']} | ${target['max_bounty_usd']:,}"
        )
        logger.info(f"{'=' * 60}")

        staged = await run_single_target(
            target["repo_url"],
            project=target["project"],
            max_files=max_files,
            dry_run=dry_run,
        )
        total_staged.extend(staged)
        await asyncio.sleep(2)  # Courtesy delay between targets

    logger.info(
        f"\n[C5-REAL] AUTONOMOUS PIPELINE COMPLETE. {len(total_staged)} total payloads staged."
    )


def main():
    parser = argparse.ArgumentParser(description="CORTEX Bounty Hunt Pipeline")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--target", type=str, help="Single repo URL to audit")
    group.add_argument("--auto", action="store_true", help="Run full OSINT→Fuzz→Submit loop")
    parser.add_argument("--max-targets", type=int, default=5, help="Max OSINT targets (auto mode)")
    parser.add_argument("--max-files", type=int, default=15, help="Max files per repo to audit")
    parser.add_argument("--dry-run", action="store_true", help="Audit only, no submission staging")
    parser.add_argument("--project", type=str, default="", help="Project name (single target)")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )

    if args.target:
        asyncio.run(run_single_target(args.target, args.project, args.max_files, args.dry_run))
    else:
        asyncio.run(run_auto_osint(args.max_targets, args.max_files, args.dry_run))


if __name__ == "__main__":
    main()
