"""
CORTEX v6.0 — Web3 OSINT Scraper (C5-REAL)

Scrapes Immunefi live for bounty targets. Zero hardcoded data.
"""

import asyncio
import hashlib
import json
import logging
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import httpx

logger = logging.getLogger("cortex.bounty_hunt.osint_scraper")

IMMUNEFI_API = "https://immunefi.com/api/bounty"
DB_PATH = Path("bounty_hunt_ledger.db")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def _init_db(db: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS bounty_targets (
        id TEXT PRIMARY KEY, project TEXT NOT NULL, repo_url TEXT,
        max_bounty_usd INTEGER DEFAULT 0, asset_type TEXT,
        in_scope TEXT, first_seen TEXT, last_seen TEXT,
        status TEXT DEFAULT 'pending', priority REAL DEFAULT 0.0
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS scrape_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT, found INTEGER, new INTEGER, source TEXT
    )""")
    conn.commit()
    return conn


def _parse_usd(s: str) -> int:
    c = re.sub(r"[^0-9]", "", str(s or "0"))
    return int(c) if c else 0


class BountyScraper:
    def __init__(self, db: Path = DB_PATH, min_bounty: int = 10_000):
        self.db_path = db
        self.min_bounty = min_bounty
        self.conn = _init_db(db)

    async def fetch_active_bounties(self) -> list[dict]:
        logger.info("[C5-REAL] OSINT sweep: Immunefi...")
        targets = []
        async with httpx.AsyncClient(
            timeout=30, headers={"User-Agent": UA}, follow_redirects=True
        ) as c:
            try:
                r = await c.get(IMMUNEFI_API)
                if r.status_code == 200:
                    data = r.json()
                    bounties = data if isinstance(data, list) else data.get("data", [])
                    for b in bounties:
                        t = self._parse_bounty(b)
                        if t and t["max_bounty_usd"] >= self.min_bounty:
                            targets.append(t)
                    logger.info(
                        f"[C5-REAL] {len(targets)} targets pass ${self.min_bounty:,} filter"
                    )
                else:
                    logger.warning(f"API {r.status_code}, fallback to page scrape")
                    targets = await self._scrape_page(c)
            except Exception as e:
                logger.warning(f"API failed: {e}, fallback to page scrape")
                targets = await self._scrape_page(c)
        return targets

    def _parse_bounty(self, b: dict) -> dict | None:
        try:
            project = b.get("project", b.get("name", "Unknown"))
            mx = _parse_usd(str(b.get("maximumPayout", b.get("maxBounty", "0"))))
            repos = []
            for a in b.get("assets", []):
                url = a.get("url", "")
                if "github.com" in url:
                    repos.append(url)
            if not repos:
                for v in (b.get("links", {}) or {}).values():
                    if isinstance(v, str) and "github.com" in v:
                        repos.append(v)
            tid = hashlib.sha256(f"{project}:{mx}".encode()).hexdigest()[:16]
            return {
                "id": tid,
                "project": project,
                "repo_url": repos[0] if repos else None,
                "all_repos": repos,
                "max_bounty_usd": mx,
                "asset_type": b.get("category", "Smart Contract"),
                "in_scope": json.dumps([a.get("url", "") for a in b.get("assets", [])[:10]]),
            }
        except Exception:
            return None

    async def _scrape_page(self, client: httpx.AsyncClient) -> list[dict]:
        logger.info("[C5-REAL] Fallback: scraping explore page...")
        targets = []
        try:
            r = await client.get("https://immunefi.com/explore/")
            if r.status_code != 200:
                return targets
            urls = list(set(re.findall(r'href="(https://github\.com/[^"]+)"', r.text)))
            for url in urls[:50]:
                parts = url.replace("https://github.com/", "").split("/")
                tid = hashlib.sha256(url.encode()).hexdigest()[:16]
                targets.append(
                    {
                        "id": tid,
                        "project": parts[0] if parts else "Unknown",
                        "repo_url": url,
                        "all_repos": [url],
                        "max_bounty_usd": 0,
                        "asset_type": "Smart Contract",
                        "in_scope": json.dumps([url]),
                    }
                )
        except Exception as e:
            logger.error(f"Page scrape failed: {e}")
        return targets

    async def prioritize(self, targets: list[dict]) -> list[dict]:
        for t in targets:
            cf = 1.0
            at = (t.get("asset_type") or "").lower()
            if "bridge" in at:
                cf = 2.0
            elif "core" in at:
                cf = 3.0
            t["priority"] = t["max_bounty_usd"] / max(cf, 0.1)
        targets.sort(key=lambda x: x["priority"], reverse=True)
        for t in targets[:10]:
            logger.info(
                f"  → {t['project']:<20} ${t['max_bounty_usd']:>12,}  P={t['priority']:>12,.0f}"
            )
        return targets

    def persist(self, targets: list[dict]) -> int:
        now = datetime.now(timezone.utc).isoformat()
        new = 0
        for t in targets:
            ex = self.conn.execute(
                "SELECT id FROM bounty_targets WHERE id=?", (t["id"],)
            ).fetchone()
            if ex:
                self.conn.execute(
                    "UPDATE bounty_targets SET last_seen=?, max_bounty_usd=?, priority=? WHERE id=?",
                    (now, t["max_bounty_usd"], t.get("priority", 0), t["id"]),
                )
            else:
                self.conn.execute(
                    "INSERT INTO bounty_targets VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        t["id"],
                        t["project"],
                        t.get("repo_url"),
                        t["max_bounty_usd"],
                        t.get("asset_type"),
                        t.get("in_scope", "[]"),
                        now,
                        now,
                        "pending",
                        t.get("priority", 0),
                    ),
                )
                new += 1
        self.conn.execute(
            "INSERT INTO scrape_log(ts,found,new,source) VALUES(?,?,?,?)",
            (now, len(targets), new, "immunefi"),
        )
        self.conn.commit()
        logger.info(f"[C5-REAL] Persisted {len(targets)} ({new} new) to {self.db_path}")
        return new

    def get_pending(self, limit: int = 10) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id,project,repo_url,max_bounty_usd,asset_type,priority FROM bounty_targets "
            "WHERE status='pending' AND repo_url IS NOT NULL ORDER BY priority DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "id": r[0],
                "project": r[1],
                "repo_url": r[2],
                "max_bounty_usd": r[3],
                "asset_type": r[4],
                "priority": r[5],
            }
            for r in rows
        ]

    async def run_osint_loop(self) -> list[dict]:
        logger.info("[C5-REAL] Starting OSINT Engine...")
        targets = await self.fetch_active_bounties()
        if not targets:
            logger.warning("No targets found.")
            return []
        prioritized = await self.prioritize(targets)
        self.persist(prioritized)
        return self.get_pending(10)

    def close(self):
        self.conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s|%(name)s|%(levelname)s|%(message)s")
    s = BountyScraper()
    try:
        results = asyncio.run(s.run_osint_loop())
        print(f"\n[C5-REAL] {len(results)} targets queued.")
        for r in results:
            print(f"  {r['project']:<20} ${r['max_bounty_usd']:>12,}  {r['repo_url']}")
    finally:
        s.close()
