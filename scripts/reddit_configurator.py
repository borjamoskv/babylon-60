#!/usr/bin/env python3
"""
reddit_configurator.py
──────────────────────
CORTEX REDDIT-Ω — C5-REAL Reddit profile configurator.

Target account : u/Zestyclose-Yam8703
Account state  : new (karma=1, bio=empty, 2026-05-19)
Dependencies   : praw>=7.8, python-dotenv

Usage:
  python scripts/reddit_configurator.py [--phase PHASE] [--dry-run]

Phases:
  1  profile    — bio, display name, privacy prefs
  2  subs       — subscribe to target communities
  3  karma      — print karma-bootstrap plan
  4  post-draft — generate post/comment drafts
  all           — run phases 1-4 (default)

Env vars (set in .env or export):
  REDDIT_CLIENT_ID
  REDDIT_CLIENT_SECRET
  REDDIT_USERNAME       (Zestyclose-Yam8703)
  REDDIT_PASSWORD
  REDDIT_USER_AGENT     (optional, default: CORTEX-Reddit-Omega/1.0)

Ω₉: All operations declare C5-REAL or C4-SIMULATION before execution.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Constants ─────────────────────────────────────────────────────────────────

TARGET_USERNAME = "Zestyclose-Yam8703"
LEDGER_PATH = Path(__file__).parent.parent / "cortex_audit_ledger.jsonl"
USER_AGENT = os.getenv("REDDIT_USER_AGENT", "CORTEX-Reddit-Omega/1.0 by borjamoskv")

# Profile configuration — edit to match desired identity
PROFILE_CONFIG = {
    "description": (
        "Architect · Artist · AI Explorer. Building at the intersection of code, "
        "sound, and machine intelligence. CORTEX sovereign. #IndustrialNoir2026"
    ),
    "display_name": "",  # Leave empty to keep username as display name
    "accept_followers": True,
    "show_media": True,
    "over_18": False,
}

# Target subreddits by category — curated for organic karma growth
TARGET_SUBREDDITS = {
    "ai_tech": [
        "MachineLearning",
        "artificial",
        "LocalLLaMA",
        "OpenAI",
        "Gemini",
        "AIAssistants",
        "singularity",
        "StableDiffusion",
    ],
    "programming": [
        "programming",
        "Python",
        "learnpython",
        "webdev",
        "devops",
        "opensource",
    ],
    "architecture_design": [
        "architecture",
        "Design",
        "graphic_design",
        "IndustrialDesign",
        "minimalism",
    ],
    "music_audio": [
        "WeAreTheMusicMakers",
        "synthesizers",
        "electronicmusic",
        "modular",
        "audiophile",
    ],
    "karma_bootstrap": [
        "FreeKarma4You",
        "karma",
        "NewToReddit",
        "testingground4bots",
        "SFWNextDoorGirls",  # note: adjust to niche
    ],
}

# High-engagement post starters for karma bootstrap
COMMENT_STARTERS = [
    {
        "subreddit": "MachineLearning",
        "topic": "local inference",
        "template": (
            "Running inference locally on M-series chips has completely changed my workflow. "
            "The performance-to-watt ratio makes cloud APIs feel wasteful for development iterations. "
            "Anyone else built their own local inference stack?"
        ),
    },
    {
        "subreddit": "Python",
        "topic": "async patterns",
        "template": (
            "After months of debugging async code, one pattern that saved me: "
            "always use `asyncio.TaskGroup` over `gather` when you need proper cancellation semantics. "
            "Especially critical in long-running agents."
        ),
    },
    {
        "subreddit": "architecture",
        "topic": "digital fabrication",
        "template": (
            "The convergence of parametric design and AI-generated forms is creating a new architectural vernacular. "
            "What's interesting is how computational methods are reviving handcraft — "
            "the output becomes more personal, not less."
        ),
    },
    {
        "subreddit": "WeAreTheMusicMakers",
        "topic": "AI in production",
        "template": (
            "Used AI-assisted arrangement on a track last week — not to replace decisions, "
            "but to stress-test them. The model kept suggesting harmonic moves I'd have dismissed. "
            "Half were noise. Two were revelatory. That ratio feels right."
        ),
    },
    {
        "subreddit": "LocalLLaMA",
        "topic": "CORTEX memory architecture",
        "template": (
            "Built a persistent memory system for local LLMs using SQLite + vector embeddings. "
            "The key insight: episodic vs semantic separation. Episodic decays fast; "
            "semantic crystallizes into a permanent knowledge graph. "
            "Happy to share the architecture if there's interest."
        ),
    },
]

POST_DRAFTS = [
    {
        "subreddit": "LocalLLaMA",
        "title": "I built a persistent memory layer for local LLMs — architecture breakdown",
        "type": "text",
        "body": (
            "After 6 months building CORTEX (a sovereign memory system for AI agents), "
            "I want to share the core architecture.\n\n"
            "**The problem**: LLMs forget everything between sessions. "
            "RAG helps but treats all memories equally — no decay, no crystallization.\n\n"
            "**My solution**:\n"
            "1. **Episodic memory** — raw conversation chunks, decays via ART-rho threshold (0.95)\n"
            "2. **Semantic memory** — distilled knowledge items, persistent, versioned\n"
            "3. **Causal DAG** — tracks reasoning chains across sessions\n\n"
            "Tech stack: Python, SQLite, sentence-transformers, asyncio\n\n"
            "Repo: github.com/borjamoskv/cortex-persist\n\n"
            "Questions welcome."
        ),
    },
    {
        "subreddit": "MachineLearning",
        "title": "[Project] CORTEX-Persist: open-source sovereign memory for AI agents",
        "type": "link",
        "url": "https://github.com/borjamoskv/cortex-persist",
    },
    {
        "subreddit": "testingground4bots",
        "title": "Testing automated posting from CORTEX-Reddit-Omega",
        "type": "text",
        "body": "First automated post — validating PRAW configuration. CORTEX C5-REAL.",
    },
]

# ── Data model ────────────────────────────────────────────────────────────────


@dataclass
class RedditOp:
    phase: str
    action: str
    target: str
    result: str
    reality_level: str  # C5-REAL | C4-SIMULATION
    error: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ConfigRun:
    run_id: str = field(default_factory=lambda: f"reddit-{int(time.time())}")
    username: str = TARGET_USERNAME
    dry_run: bool = False
    ops: list[RedditOp] = field(default_factory=list)
    started: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished: str | None = None


# ── Reddit client ─────────────────────────────────────────────────────────────


def _load_env() -> None:
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with env_path.open() as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    key, val = stripped.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())


def _get_reddit_client() -> Any:
    """Initialize PRAW Reddit client from env vars."""
    try:
        import praw  # type: ignore[import]
    except ImportError:
        print("❌ praw not installed. Run: pip install praw", file=sys.stderr)
        sys.exit(1)

    client_id = os.getenv("REDDIT_CLIENT_ID", "")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
    username = os.getenv("REDDIT_USERNAME", TARGET_USERNAME)
    password = os.getenv("REDDIT_PASSWORD", "")

    if not all([client_id, client_secret, username, password]):
        return None  # Missing creds → dry-run forced

    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        username=username,
        password=password,
        user_agent=USER_AGENT,
    )


# ── Phase 1: Profile setup ────────────────────────────────────────────────────


def phase_profile(run: ConfigRun, reddit: Any) -> None:
    print("\n📋 PHASE 1 — Profile Setup")
    print(f"   Target: u/{TARGET_USERNAME}")

    if run.dry_run or reddit is None:
        reality = "C4-SIMULATION"
        print(f"   [{reality}] Would set description: {PROFILE_CONFIG['description'][:80]}...")
        run.ops.append(
            RedditOp(
                phase="profile",
                action="set_description",
                target=TARGET_USERNAME,
                result=f"DRY-RUN: description would be set ({len(PROFILE_CONFIG['description'])} chars)",
                reality_level=reality,
            )
        )
        print(f"   [{reality}] Would set accept_followers: {PROFILE_CONFIG['accept_followers']}")
        run.ops.append(
            RedditOp(
                phase="profile",
                action="set_preferences",
                target=TARGET_USERNAME,
                result="DRY-RUN: preferences would be updated",
                reality_level=reality,
            )
        )
        print(f"   ⚠️  {reality} — no real API calls. Set REDDIT_* env vars for C5-REAL execution.")
        return

    reality = "C5-REAL"
    try:
        reddit.user.me()  # Validate authentication
        # Update profile description
        reddit.patch(
            "/api/v1/me",
            data={
                "description": PROFILE_CONFIG["description"],
                "accept_followers": PROFILE_CONFIG["accept_followers"],
                "show_media": PROFILE_CONFIG["show_media"],
            },
        )
        print(f"   ✅ [{reality}] Bio updated: {PROFILE_CONFIG['description'][:60]}...")
        run.ops.append(
            RedditOp(
                phase="profile",
                action="set_description",
                target=TARGET_USERNAME,
                result="Bio set successfully",
                reality_level=reality,
            )
        )

        # Update display name if set
        if PROFILE_CONFIG.get("display_name"):
            reddit.patch(
                "/api/v1/me",
                data={"display_name": PROFILE_CONFIG["display_name"]},
            )
            print(f"   ✅ [{reality}] Display name: {PROFILE_CONFIG['display_name']}")
            run.ops.append(
                RedditOp(
                    phase="profile",
                    action="set_display_name",
                    target=TARGET_USERNAME,
                    result=f"Display name: {PROFILE_CONFIG['display_name']}",
                    reality_level=reality,
                )
            )

    except Exception as e:
        print(f"   ❌ [{reality}] Profile update failed: {e}")
        run.ops.append(
            RedditOp(
                phase="profile",
                action="set_description",
                target=TARGET_USERNAME,
                result="failed",
                reality_level=reality,
                error=str(e),
            )
        )


# ── Phase 2: Community mapping & subscriptions ────────────────────────────────


def phase_subs(run: ConfigRun, reddit: Any) -> None:
    print("\n🗺️  PHASE 2 — Community Mapping & Subscriptions")

    all_subs = [s for subs in TARGET_SUBREDDITS.values() for s in subs]
    print(f"   Target: {len(all_subs)} subreddits across {len(TARGET_SUBREDDITS)} categories")

    if run.dry_run or reddit is None:
        reality = "C4-SIMULATION"
        for category, subs in TARGET_SUBREDDITS.items():
            print(f"   [{reality}] Would subscribe to [{category}]: {', '.join(subs)}")
        run.ops.append(
            RedditOp(
                phase="subs",
                action="bulk_subscribe",
                target=f"{len(all_subs)} subreddits",
                result=f"DRY-RUN: would subscribe to {', '.join(all_subs[:5])}...",
                reality_level=reality,
            )
        )
        print(f"   ⚠️  {reality} — no real subscriptions made.")
        return

    reality = "C5-REAL"
    subscribed = []
    failed = []
    for _category, subs in TARGET_SUBREDDITS.items():
        for sub_name in subs:
            try:
                subreddit = reddit.subreddit(sub_name)
                subreddit.subscribe()
                subscribed.append(sub_name)
                print(f"   ✅ [{reality}] Subscribed: r/{sub_name}")
                time.sleep(1.1)  # Reddit rate limit: 1 req/sec
            except Exception as e:
                failed.append(sub_name)
                print(f"   ❌ Failed r/{sub_name}: {e}")

    run.ops.append(
        RedditOp(
            phase="subs",
            action="bulk_subscribe",
            target=f"{len(all_subs)} subreddits",
            result=f"Subscribed: {len(subscribed)} | Failed: {len(failed)}",
            reality_level=reality,
            error=f"Failed: {failed}" if failed else None,
        )
    )


# ── Phase 3: Karma bootstrap plan ─────────────────────────────────────────────


def phase_karma(run: ConfigRun, reddit: Any) -> None:
    print("\n⚡ PHASE 3 — Karma Bootstrap Strategy")

    current_karma = 1  # Audited 2026-05-20

    print(f"\n   Current karma: {current_karma}")
    print("   Target: 100+ karma within 30 days\n")
    print("   📅 7-DAY WARMUP PLAN:")
    plan = [
        (
            "Day 1-2",
            "Join 3 top threads in r/MachineLearning + r/LocalLLaMA. Leave 2 genuine comments.",
        ),
        (
            "Day 3",
            "Post in r/testingground4bots to validate account visibility (not shadowbanned).",
        ),
        (
            "Day 4-5",
            "Comment in r/Python and r/architecture on trending posts. Focus on value-add.",
        ),
        ("Day 6", "First link post: share CORTEX GitHub in r/LocalLLaMA or r/MachineLearning."),
        ("Day 7", "Audit: check karma velocity, reply to all comments received, adjust strategy."),
    ]
    for day, action in plan:
        print(f"   {day:10s} → {action}")

    print(f"\n   💬 COMMENT STARTERS ({len(COMMENT_STARTERS)} drafted):")
    for i, cs in enumerate(COMMENT_STARTERS, 1):
        print(f"   [{i}] r/{cs['subreddit']} [{cs['topic']}]")
        print(f"       {cs['template'][:100]}...")

    reality = "C4-SIMULATION"  # Plan only, no API calls
    run.ops.append(
        RedditOp(
            phase="karma",
            action="bootstrap_plan",
            target=TARGET_USERNAME,
            result=f"7-day plan generated. {len(COMMENT_STARTERS)} comment starters. Target: 100 karma.",
            reality_level=reality,
        )
    )
    print(f"\n   [{reality}] Plan generated. Execute manually or via --phase 4.")


# ── Phase 4: Post drafts ──────────────────────────────────────────────────────


def phase_post_drafts(run: ConfigRun, reddit: Any) -> None:
    print("\n📝 PHASE 4 — Post Drafts")
    print(f"   {len(POST_DRAFTS)} posts drafted\n")

    for i, draft in enumerate(POST_DRAFTS, 1):
        print(f"   [{i}] r/{draft['subreddit']} [{draft['type'].upper()}]")
        print(f"       Title: {draft['title']}")
        if draft.get("body"):
            print(f"       Body preview: {draft['body'][:100]}...")
        if draft.get("url"):
            print(f"       URL: {draft['url']}")
        print()

    if run.dry_run or reddit is None:
        reality = "C4-SIMULATION"
        print(f"   [{reality}] Drafts saved. Use --submit to post C5-REAL.")
        run.ops.append(
            RedditOp(
                phase="post_drafts",
                action="generate_drafts",
                target=TARGET_USERNAME,
                result=f"DRY-RUN: {len(POST_DRAFTS)} drafts generated, not submitted",
                reality_level=reality,
            )
        )
        return

    # Only submit testingground4bots post in live mode (safe)
    reality = "C5-REAL"
    for draft in POST_DRAFTS:
        if draft["subreddit"] == "testingground4bots":
            try:
                sub = reddit.subreddit(draft["subreddit"])
                if draft["type"] == "text":
                    sub.submit(title=draft["title"], selftext=draft.get("body", ""))
                elif draft["type"] == "link":
                    sub.submit(title=draft["title"], url=draft["url"])
                print(f"   ✅ [{reality}] Posted to r/{draft['subreddit']}: {draft['title']}")
                run.ops.append(
                    RedditOp(
                        phase="post_drafts",
                        action="submit_post",
                        target=f"r/{draft['subreddit']}",
                        result=f"Posted: {draft['title']}",
                        reality_level=reality,
                    )
                )
                time.sleep(1.1)
            except Exception as e:
                print(f"   ❌ [{reality}] Post failed: {e}")
                run.ops.append(
                    RedditOp(
                        phase="post_drafts",
                        action="submit_post",
                        target=f"r/{draft['subreddit']}",
                        result="failed",
                        reality_level=reality,
                        error=str(e),
                    )
                )


# ── Ledger persistence ────────────────────────────────────────────────────────


def persist_run(run: ConfigRun) -> None:
    record = {
        "event": "reddit_configurator_run",
        "run_id": run.run_id,
        "username": run.username,
        "dry_run": run.dry_run,
        "started": run.started,
        "finished": run.finished,
        "ops": [asdict(op) for op in run.ops],
        "summary": {
            "total_ops": len(run.ops),
            "c5_real": sum(1 for op in run.ops if op.reality_level == "C5-REAL"),
            "c4_sim": sum(1 for op in run.ops if op.reality_level == "C4-SIMULATION"),
            "errors": sum(1 for op in run.ops if op.error),
        },
    }
    with LEDGER_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"\n📒 Ledger updated → {LEDGER_PATH.name}")


# ── CLI ───────────────────────────────────────────────────────────────────────


def print_banner() -> None:
    print("╔══════════════════════════════════════════════════════╗")
    print("║     CORTEX REDDIT-Ω — Profile Configurator          ║")
    print("║     Target: u/Zestyclose-Yam8703                    ║")
    print("║     Industrial Noir 2026 · C5-REAL / C4-SIM         ║")
    print("╚══════════════════════════════════════════════════════╝")


def print_report(run: ConfigRun) -> None:
    c5 = sum(1 for op in run.ops if op.reality_level == "C5-REAL")
    c4 = sum(1 for op in run.ops if op.reality_level == "C4-SIMULATION")
    errors = sum(1 for op in run.ops if op.error)
    print("\n" + "═" * 56)
    print(f"  REDDIT-Ω REPORT — u/{TARGET_USERNAME}")
    print(f"  Run ID  : {run.run_id}")
    print(f"  Dry-run : {run.dry_run}")
    print("─" * 56)
    for op in run.ops:
        icon = "✅" if not op.error else "❌"
        print(f"  {icon}  [{op.reality_level}] {op.phase}.{op.action} → {op.result[:50]}")
    print("─" * 56)
    print(f"  Total ops : {len(run.ops)}")
    print(f"  C5-REAL   : {c5}")
    print(f"  C4-SIM    : {c4}")
    print(f"  Errors    : {errors}")
    print("═" * 56)
    print(f"\n  🔴 REDDIT-Ω: configured u/{TARGET_USERNAME}")


def main() -> None:
    parser = argparse.ArgumentParser(description="CORTEX REDDIT-Ω — Reddit profile configurator")
    parser.add_argument(
        "--phase",
        choices=["1", "2", "3", "4", "all"],
        default="all",
        help="Phase to run: 1=profile, 2=subs, 3=karma-plan, 4=post-drafts, all=1-4",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="C4-SIMULATION: print actions without executing real API calls",
    )
    args = parser.parse_args()

    print_banner()
    _load_env()

    reddit = _get_reddit_client()
    if reddit is None:
        print("\n⚠️  REDDIT credentials not found in .env — forcing C4-SIMULATION mode.")
        print("   Set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD\n")
        args.dry_run = True

    run = ConfigRun(dry_run=args.dry_run)

    if not args.dry_run and reddit is not None:
        print(f"\n🟢 C5-REAL mode — authenticated as u/{reddit.user.me().name}")
    else:
        print("\n🟡 C4-SIMULATION mode — no real API calls")

    phase_map = {
        "1": phase_profile,
        "2": phase_subs,
        "3": phase_karma,
        "4": phase_post_drafts,
    }

    if args.phase == "all":
        for fn in phase_map.values():
            fn(run, reddit)
    else:
        phase_map[args.phase](run, reddit)

    run.finished = datetime.now(timezone.utc).isoformat()
    print_report(run)
    persist_run(run)


if __name__ == "__main__":
    main()
