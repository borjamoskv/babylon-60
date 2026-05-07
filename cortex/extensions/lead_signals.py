"""Neutral CLI wrapper for lead signal detection."""

from __future__ import annotations

import argparse
import logging

from cortex.extensions.moltbook.lead_detection import (
    analyze_cognitive_blueprint,
    run_signal_sweep,
)

__all__ = ["analyze_cognitive_blueprint", "main", "run_signal_sweep"]


def main() -> None:
    parser = argparse.ArgumentParser(description="CORTEX signal sweep lead scanner")
    parser.add_argument("--repos", nargs="*", help="Override target repos (owner/name)")
    parser.add_argument("--token", help="GitHub token")
    parser.add_argument("--min-score", type=float, default=0.05, help="Min lead score 0-1")
    parser.add_argument("--mode", choices=["sweep", "blueprint"], default="sweep")
    parser.add_argument("--text", help="Text to analyze (blueprint mode)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

    if args.mode == "blueprint":
        if not args.text:
            print("Provide --text for blueprint mode")
            return
        result = analyze_cognitive_blueprint(args.text)
        print("\nBlueprint Analysis:")
        for key, value in result.items():
            print(f"  {key}: {value}")
        return

    run_signal_sweep(repos=args.repos, token=args.token, min_score=args.min_score)


if __name__ == "__main__":
    main()
