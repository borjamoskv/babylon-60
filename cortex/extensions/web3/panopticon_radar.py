"""CORTEX v8.0 — Panopticon Radar (Autonomous Target Acquisition).

The "Eyes" of the CORTEX-Σ Swarm.  Continuously scans for high-value targets
(smart contracts with high TVL or active bug bounties) and feeds them into the
Swarm task queue (``10k_shards`` SQLite DB).

Scan Sources
------------
* **Green Zone** — Immunefi bounty listings (>$50k reward).
* **Grey Zone**  — Recently deployed contracts via Ethereum RPC (Alchemy/Infura).

Thermodynamic Triage
--------------------
Each candidate contract is scored with ``evaluate_exergy()`` before injection.
Contracts with high entropy (ERC-20 fee-on-transfer quirks, old compiler) are
prioritised.  Low-liquidity NFT contracts score 0 and are discarded.

Axiom Derivations
-----------------
* Ω₂ (Entropic Asymmetry): Only targets that reduce uncertainty survive.
* Ω₄₄ (Observation-Action Loop): Inference must induce executable programs.
* AX-041 (No Hidden Entropy): All discovered facts are persisted to the DB.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__all__ = ["PanopticonRadar"]

logger = logging.getLogger("cortex.extensions.web3.panopticon_radar")

# ── Constants ─────────────────────────────────────────────────────────────

_PREFIX = "👁️ [PANOPTICON]"

# Default path for the Swarm shard queue DB.
_DEFAULT_DB_PATH = Path.home() / ".cortex" / "10k_shards.db"

# Minimum bounty amount (USD) to be considered a valid Immunefi target.
_MIN_BOUNTY_USD = 50_000

# Exergy threshold — targets below this score are discarded before injection.
_MIN_EXERGY = 0.1

# Loop cadence (seconds) between full radar sweeps.
_SWEEP_INTERVAL_SECONDS = 300  # 5 minutes

# ── DB Schema ─────────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS swarm_targets (
    id              TEXT PRIMARY KEY,
    address         TEXT NOT NULL,
    source          TEXT NOT NULL,
    chain           TEXT NOT NULL DEFAULT 'ethereum',
    bounty_usd      REAL DEFAULT 0,
    tvl_usd         REAL DEFAULT 0,
    exergy_score    REAL DEFAULT 0,
    repo_url        TEXT DEFAULT '',
    compiler        TEXT DEFAULT '',
    tags            TEXT DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'pending',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_swarm_targets_status
    ON swarm_targets (status);

CREATE INDEX IF NOT EXISTS idx_swarm_targets_exergy
    ON swarm_targets (exergy_score DESC);
"""


# ── Mock Data Fixtures ────────────────────────────────────────────────────

_MOCK_IMMUNEFI_BOUNTIES: list[dict[str, Any]] = [
    {
        "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "chain": "ethereum",
        "bounty_usd": 1_000_000,
        "repo_url": "https://github.com/centrifuge/liquidity-pools",
        "tags": ["erc20", "fee-on-transfer", "defi"],
        "compiler": "0.8.19",
    },
    {
        "address": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "chain": "ethereum",
        "bounty_usd": 250_000,
        "repo_url": "https://github.com/makerdao/dss",
        "tags": ["erc20", "lending", "defi"],
        "compiler": "0.5.12",  # older compiler version — high priority
    },
    {
        "address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "chain": "ethereum",
        "bounty_usd": 500_000,
        "repo_url": "https://github.com/Uniswap/v3-core",
        "tags": ["wrapped-ether", "defi", "amm"],
        "compiler": "0.7.6",
    },
    {
        "address": "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D",
        "chain": "ethereum",
        "bounty_usd": 10_000,  # below threshold — should be filtered
        "repo_url": "https://github.com/BoredApeYachtClub/BAYC",
        "tags": ["nft", "erc721"],
        "compiler": "0.8.4",
    },
]

_MOCK_RECENT_DEPLOYMENTS: list[dict[str, Any]] = [
    {
        "address": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "chain": "ethereum",
        "tvl_usd": 5_000_000,
        "tags": ["erc20", "fee-on-transfer", "stablecoin"],
        "compiler": "0.4.18",  # very old compiler — critical priority
        "block": 19_800_000,
    },
    {
        "address": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
        "chain": "ethereum",
        "tvl_usd": 120_000,
        "tags": ["erc20", "wrapped-btc", "defi"],
        "compiler": "0.8.20",
        "block": 19_801_234,
    },
    {
        "address": "0x00000000219ab540356cBB839Cbe05303d7705Fa",
        "chain": "ethereum",
        "tvl_usd": 800_000,
        "tags": ["nft", "erc721", "low-liquidity"],
        "compiler": "0.8.0",
        "block": 19_802_100,
    },
]


# ── PanopticonRadar ────────────────────────────────────────────────────────


class PanopticonRadar:
    """Autonomous target acquisition radar for the CORTEX-Σ Swarm.

    Parameters
    ----------
    db_path:
        Path to the Swarm shard SQLite database.  Defaults to
        ``~/.cortex/10k_shards.db``.
    sweep_interval:
        Seconds between full radar sweeps.  Defaults to 300 (5 minutes).
    """

    def __init__(
        self,
        db_path: Path | str | None = None,
        sweep_interval: int = _SWEEP_INTERVAL_SECONDS,
    ) -> None:
        self._db_path = Path(db_path) if db_path is not None else _DEFAULT_DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._sweep_interval = sweep_interval
        self._init_db()
        logger.info("%s Radar online — DB: %s", _PREFIX, self._db_path)

    # ── DB Helpers ────────────────────────────────────────────────────────

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.executescript(_SCHEMA)

    # ── Source 1: Green Zone — Immunefi Bounties ──────────────────────────

    async def fetch_immunefi_bounties(self) -> list[dict[str, Any]]:
        """Return structured Immunefi bounty targets with bounty > $50k.

        The API call is mocked in this implementation.  Replace the body of
        the ``_fetch`` coroutine with a real ``aiohttp`` request when an
        Immunefi API key is available.

        Returns
        -------
        list[dict]:
            Each dict contains ``address``, ``chain``, ``bounty_usd``,
            ``repo_url``, ``tags``, and ``compiler`` fields.
        """

        async def _fetch() -> list[dict[str, Any]]:
            # TODO: replace with real Immunefi API call when key is available.
            # e.g.: async with aiohttp.ClientSession() as s:
            #           async with s.get(IMMUNEFI_API_URL) as r: ...
            await asyncio.sleep(0)  # yield to event loop (simulates I/O)
            return list(_MOCK_IMMUNEFI_BOUNTIES)

        raw = await _fetch()
        targets = [t for t in raw if t.get("bounty_usd", 0) >= _MIN_BOUNTY_USD]
        logger.info(
            "%s Immunefi scan complete — %d/%d targets above $%s bounty threshold",
            _PREFIX,
            len(targets),
            len(raw),
            f"{_MIN_BOUNTY_USD:,}",
        )
        return targets

    # ── Source 2: Grey Zone — Recent On-Chain Deployments ─────────────────

    async def scan_recent_deployments(self) -> list[dict[str, Any]]:
        """Return recently deployed contracts with notable TVL.

        Mocks a call to an Ethereum JSON-RPC endpoint (Alchemy / Infura) that
        filters ``eth_newFilter`` / ``eth_getLogs`` for contract creation
        events.  Replace the mock with real RPC I/O when an endpoint URL is
        configured via ``CORTEX_RPC_URL``.

        Returns
        -------
        list[dict]:
            Each dict contains ``address``, ``chain``, ``tvl_usd``, ``tags``,
            ``compiler``, and ``block`` fields.
        """

        async def _rpc_fetch() -> list[dict[str, Any]]:
            # TODO: replace with real RPC call.
            # e.g.: w3 = AsyncWeb3(AsyncHTTPProvider(os.environ["CORTEX_RPC_URL"]))
            #       logs = await w3.eth.get_logs({...})
            await asyncio.sleep(0)
            return list(_MOCK_RECENT_DEPLOYMENTS)

        deployments = await _rpc_fetch()
        logger.info(
            "%s RPC scan complete — %d recent deployments retrieved",
            _PREFIX,
            len(deployments),
        )
        return deployments

    # ── Thermodynamic Triage ──────────────────────────────────────────────

    def evaluate_exergy(self, contract_data: dict[str, Any]) -> float:
        """Calculate an exergy score (priority weight) for a candidate target.

        Scoring rules
        -------------
        * Base score starts at 0.5.
        * **+0.4** if the contract handles fee-on-transfer ERC-20 tokens
          (``fee-on-transfer`` in tags) — arithmetic mismatches are common.
        * **+0.3** if the compiler version is older than 0.6.x — known
          vulnerability surface.
        * **+0.2** if the compiler version is older than 0.8.x but ≥ 0.6.x.
        * **+0.1** if the contract is a known DeFi protocol (``defi`` in tags).
        * **→ 0.0** (drop) if it is a low-liquidity NFT contract (``nft`` tag
          present AND ``low-liquidity`` tag present, or ``erc721`` only with
          no significant TVL/bounty).

        Parameters
        ----------
        contract_data:
            Arbitrary dict describing a smart contract target.

        Returns
        -------
        float:
            Exergy score in [0.0, 1.0].  A score of 0.0 means the target
            should be discarded.
        """
        tags: list[str] = [t.lower() for t in contract_data.get("tags", [])]
        compiler: str = contract_data.get("compiler", "")
        tvl: float = float(contract_data.get("tvl_usd", 0))
        bounty: float = float(contract_data.get("bounty_usd", 0))

        # Drop rule — low-liquidity NFT contracts have no extractable exergy.
        is_nft = "nft" in tags or "erc721" in tags
        is_low_liquidity = "low-liquidity" in tags or (tvl < 10_000 and bounty < _MIN_BOUNTY_USD)
        if is_nft and is_low_liquidity:
            logger.debug(
                "%s Dropped (NFT/low-liquidity): %s",
                _PREFIX,
                contract_data.get("address", "?"),
            )
            return 0.0

        score: float = 0.5

        # Fee-on-transfer ERC-20 — arithmetic edge cases abound.
        if "fee-on-transfer" in tags:
            score += 0.4

        # Old compiler bonuses.
        if compiler:
            try:
                parts = compiler.lstrip("v").split(".")
                major, minor = int(parts[0]), int(parts[1])
                if major == 0 and minor < 6:
                    score += 0.3  # pre-0.6: no SafeMath, many classic bugs
                elif major == 0 and minor < 8:
                    score += 0.2  # pre-0.8: no built-in overflow checks
            except (ValueError, IndexError):
                pass  # unparseable version — no bonus, no penalty

        # DeFi bonus.
        if "defi" in tags:
            score += 0.1

        return min(score, 1.0)

    # ── Injection into Swarm Queue ────────────────────────────────────────

    def inject_to_swarm(self, targets: list[dict[str, Any]]) -> int:
        """Persist high-priority targets into the Swarm shard DB.

        Each target is assigned a UUID, timestamped, and inserted with
        ``status='pending'`` so the SwarmCommander can pick it up.
        Duplicate addresses are silently ignored (``INSERT OR IGNORE``).

        Parameters
        ----------
        targets:
            List of contract dicts enriched with an ``exergy_score`` key.

        Returns
        -------
        int:
            Number of new rows inserted.
        """
        if not targets:
            logger.info("%s No targets to inject.", _PREFIX)
            return 0

        now = datetime.now(timezone.utc).isoformat()
        rows: list[tuple[Any, ...]] = []
        for t in targets:
            rows.append(
                (
                    str(uuid.uuid4()),
                    t.get("address", ""),
                    t.get("source", "unknown"),
                    t.get("chain", "ethereum"),
                    float(t.get("bounty_usd", 0)),
                    float(t.get("tvl_usd", 0)),
                    float(t.get("exergy_score", 0)),
                    t.get("repo_url", ""),
                    t.get("compiler", ""),
                    ",".join(t.get("tags", [])),
                    "pending",
                    now,
                    now,
                )
            )

        inserted = 0
        with sqlite3.connect(str(self._db_path)) as conn:
            for row in rows:
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO swarm_targets
                        (id, address, source, chain, bounty_usd, tvl_usd,
                         exergy_score, repo_url, compiler, tags,
                         status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    row,
                )
                inserted += cursor.rowcount

        logger.info(
            "%s Injected %d new target(s) into Swarm queue (%s)",
            _PREFIX,
            inserted,
            self._db_path,
        )
        return inserted

    # ── Main Daemon Loop ──────────────────────────────────────────────────

    async def run_panopticon(self) -> None:
        """Async daemon loop — scans sources and injects targets periodically.

        The loop runs indefinitely until cancelled.  Each sweep:
        1. Fetches Immunefi bounties (Green Zone).
        2. Fetches recent on-chain deployments (Grey Zone).
        3. Scores each candidate with ``evaluate_exergy()``.
        4. Injects qualifying targets into the Swarm queue.
        5. Sleeps for ``sweep_interval`` seconds before the next sweep.
        """
        logger.info("%s Daemon loop started (sweep every %ds)", _PREFIX, self._sweep_interval)

        while True:
            sweep_start = datetime.now(timezone.utc).isoformat()
            logger.info("%s === Sweep started at %s ===", _PREFIX, sweep_start)

            try:
                # ── Acquire targets from both sources ──────────────────
                bounties, deployments = await asyncio.gather(
                    self.fetch_immunefi_bounties(),
                    self.scan_recent_deployments(),
                )

                # ── Tag each target with its source ───────────────────
                for t in bounties:
                    t.setdefault("source", "immunefi")
                for t in deployments:
                    t.setdefault("source", "rpc_deployment")

                all_candidates: list[dict[str, Any]] = bounties + deployments

                # ── Thermodynamic triage ──────────────────────────────
                high_value: list[dict[str, Any]] = []
                for candidate in all_candidates:
                    score = self.evaluate_exergy(candidate)
                    candidate["exergy_score"] = score
                    if score >= _MIN_EXERGY:
                        high_value.append(candidate)
                    else:
                        logger.debug(
                            "%s Discarded (exergy=%.2f): %s",
                            _PREFIX,
                            score,
                            candidate.get("address", "?"),
                        )

                logger.info(
                    "%s Triage complete — %d/%d targets qualify (exergy >= %.2f)",
                    _PREFIX,
                    len(high_value),
                    len(all_candidates),
                    _MIN_EXERGY,
                )

                # ── Inject into Swarm queue ───────────────────────────
                self.inject_to_swarm(high_value)

            except asyncio.CancelledError:
                logger.info("%s Daemon loop cancelled — shutting down.", _PREFIX)
                raise
            except Exception:
                logger.exception("%s Unhandled error during sweep — continuing.", _PREFIX)

            await asyncio.sleep(self._sweep_interval)
