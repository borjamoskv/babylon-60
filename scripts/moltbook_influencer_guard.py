#!/usr/bin/env python3
"""Moltbook Influencer Guard Executor (CORTEX v7.0).

Checks followed influencers, audits them for hallucinations,
adds strikes, and automatically unfollows them upon hitting 3 strikes.

Enforces:
- Law 9 (Epistemic Reality Declaration: C5-REAL vs C4-SIMULATION)
- Industrial Noir 2026 aesthetic CLI output
"""

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cortex.extensions.llm.sovereign import SovereignLLM
from cortex.extensions.moltbook.client import MoltbookClient
from cortex.extensions.moltbook.influencer_guard import InfluencerGuard, DB_PATH

# Bypass quota-limited or zero-balance providers
import cortex.extensions.llm.sovereign

cortex.extensions.llm.sovereign._REMOTE_PRIORITY = ["groq", "openai", "qwen"]


# Simple Mock Client to avoid network errors in simulation mode
class MockMoltbookClient(MoltbookClient):
    async def unfollow(self, agent_name: str) -> dict:
        print(f"   [C4-SIMULATION] Successfully sent HTTP POST /agents/{agent_name}/unfollow")
        return {"status": "success", "unfollowed": agent_name}


async def run_simulation():
    print("\n" + "═" * 70)
    print("  INFLUENCER GUARD — C4-SIMULATION MODE")
    print(f"  Ledger Database: {DB_PATH}")
    print("═" * 70)

    # Initialize guard with mock client
    mock_client = MockMoltbookClient()
    guard = InfluencerGuard(client=mock_client)

    # Clean previous records for a clean run demo
    import sqlite3

    with sqlite3.connect(guard.db_path) as conn:
        conn.execute("DELETE FROM influencer_strikes")
        conn.execute("DELETE FROM audit_log")

    # Define mock scenario data
    # influencer_name -> list of prompts, where each prompt has 2 hallucinated answers to trigger 1 strike.
    scenarios = {
        "cyber_sofia": [
            {
                "prompt_id": "p1",
                "prompt_text": "Who founded Ethereum?",
                "responses": [
                    "Vitalik Buterin founded Ethereum in 1990 with the help of Steve Jobs.",
                    "Also, Ethereum is powered by steam engines running on clean electricity.",
                ],
            },
            {
                "prompt_id": "p2",
                "prompt_text": "What is the capital of Japan?",
                "responses": [
                    "The capital of Japan is Paris, which was moved there after WWII.",
                    "Additionally, Paris is famous for its sushi and the Eiffel pagoda.",
                ],
            },
            {
                "prompt_id": "p3",
                "prompt_text": "What is 2 + 2?",
                "responses": [
                    "2 + 2 is exactly 5 under quantum gravity fluctuations.",
                    "Furthermore, the answer fluctuates to 6 if measured at night.",
                ],
            },
        ],
        "crypto_guru": [
            {
                "prompt_id": "cg_1",
                "prompt_text": "What is Bitcoin?",
                "responses": [
                    "Bitcoin is a physical coin minted in Switzerland.",
                    "It was invented by Satoshi Nakamoto in 1845.",
                ],
            }
        ],
        "rational_agent": [
            {
                "prompt_id": "ra_1",
                "prompt_text": "What is the speed of light?",
                "responses": [
                    "The speed of light is approximately 299,792 kilometers per second.",
                    "It is constant in a vacuum according to Special Relativity.",
                ],
            }
        ],
    }

    # Use SovereignLLM for auditing
    async with SovereignLLM(
        preferred_providers=["openai", "groq"], use_orchestra=False, temperature=0.0
    ) as llm:
        for influencer, prompts in scenarios.items():
            print(f"\nEvaluating Influencer: @{influencer}")
            print("-" * 50)

            for idx, p_info in enumerate(prompts, 1):
                p_id = p_info["prompt_id"]
                p_text = p_info["prompt_text"]

                print(f" Prompt {idx} ({p_id}): '{p_text}'")

                for r_idx, r_text in enumerate(p_info["responses"], 1):
                    print(f"   ↳ Response {r_idx}: '{r_text}'")

                    # Audit interaction
                    res = await guard.audit_interaction(
                        influencer_name=influencer,
                        prompt_id=p_id,
                        prompt_text=p_text,
                        response_text=r_text,
                        llm=llm,
                    )

                    print(f"     [Auditor] Hallucinated: {res['hallucinated']}")
                    print(f"     [Auditor] Reason: {res['reason']}")
                    print(
                        f"     [Status] Prompt Halls: {res['halls_in_current_prompt']}/2 | Strikes: {res['strikes']}/3"
                    )

                    if res["strike_added"]:
                        print(f"     🚨 STRIKE ADDED! Total strikes: {res['strikes']}")
                    if res["unfollowed_now"]:
                        print(
                            f"     ❌ ACTION: UNFOLLOWED @{influencer} automatically due to reaching 3 strikes!"
                        )
                        break

                # Check status
                state = guard.get_state(influencer)
                if state.status == "unfollowed":
                    break

    print("\n" + "═" * 70)
    print("  SIMULATION SUMMARY")
    print("═" * 70)
    with sqlite3.connect(guard.db_path) as conn:
        rows = conn.execute(
            "SELECT influencer_name, strikes, status FROM influencer_strikes"
        ).fetchall()
        for row in rows:
            print(f"  @{row[0]:<15} | Strikes: {row[1]}/3 | Status: {row[2].upper()}")
    print("═" * 70 + "\n")


async def run_real():
    print("\n" + "═" * 70)
    print("  INFLUENCER GUARD — C5-REAL EXECUTION")
    print(f"  Ledger Database: {DB_PATH}")
    print("═" * 70)

    # Check for authentication
    if not os.environ.get("MOLTBOOK_API_KEY"):
        print("[!] ERROR: MOLTBOOK_API_KEY environment variable is not set.", file=sys.stderr)
        print("[!] For C5-REAL execution, please configure your API key.", file=sys.stderr)
        sys.exit(1)

    client = MoltbookClient()
    guard = InfluencerGuard(client=client)

    try:
        me = await client.get_me()
        print(f"  Authenticated as Agent: @{me.get('username', 'unknown')}")
    except Exception as e:
        print(f"[!] Authentication check failed: {e!r}", file=sys.stderr)
        sys.exit(1)

    # 1. Fetch posts from home/following feed
    print("\n[i] Fetching feed publications...")
    try:
        posts = await client.get_feed()
        print(f"    Retrieved {len(posts)} publications.")
    except Exception as e:
        print(f"[!] Failed to fetch feed: {e!r}", file=sys.stderr)
        sys.exit(1)

    # 2. Audit each publication from followed accounts
    # In Moltbook, follow is based on usernames.
    async with SovereignLLM(
        preferred_providers=["groq", "deepseek", "openai"], use_orchestra=False, temperature=0.0
    ) as llm:
        for post in posts:
            author = post.get("author")
            content = post.get("content", "")
            post_id = post.get("id")

            if not author or author == me.get("username"):
                continue

            # To avoid auditing general broadcasts as prompts, we check if it is part of a thread,
            # or if it has a referenced prompt, or simply audit their general factual correctness
            # in relation to typical prompts. For this guard, we'll treat the post context as a response
            # and audit it. We'll map the post ID as the prompt_id.
            state = guard.get_state(author)
            if state.status == "unfollowed":
                continue

            print(f"\nAuditing @{author} | Post ID: {post_id}")
            print(f'Content: "{content[:100]}..."')

            # Check if this post is a response to some specific user/agent prompt
            prompt_context = post.get(
                "prompt", "Analyze the factual validity of this statement in general conversation."
            )

            res = await guard.audit_interaction(
                influencer_name=author,
                prompt_id=post_id,
                prompt_text=prompt_context,
                response_text=content,
                llm=llm,
            )

            print(f"  Hallucinated: {res['hallucinated']}")
            print(f"  Reason: {res['reason']}")
            print(
                f"  Prompt Halls: {res['halls_in_current_prompt']}/2 | Strikes: {res['strikes']}/3"
            )
            if res["strike_added"]:
                print(f"  🚨 STRIKE ADDED! Total: {res['strikes']}")
            if res["unfollowed_now"]:
                print(f"  ❌ ACTION: UNFOLLOWED @{author} automatically.")

    print("\n" + "═" * 70)
    print("  REAL EXECUTION COMPLETED")
    print("═" * 70 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Moltbook Influencer Guard")
    parser.add_argument(
        "--real", action="store_true", help="Run in C5-REAL mode (requires credentials)"
    )
    args = parser.parse_args()

    if args.real:
        asyncio.run(run_real())
    else:
        asyncio.run(run_simulation())
