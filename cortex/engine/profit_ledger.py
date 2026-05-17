"""
CORTEX v6.0 — Profit Ledger (C5-REAL)

Immutable P&L tracking for MEV operations.
SQLite WAL with CSV export for fiscal compliance.
"""

import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("scratch/mev_logs/profit_ledger.db")


def _init_db(db: Path = DB_PATH) -> sqlite3.Connection:
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS operations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        chain TEXT NOT NULL,
        tx_hash TEXT UNIQUE,
        op_type TEXT NOT NULL,
        revenue_eth REAL DEFAULT 0,
        gas_cost_eth REAL DEFAULT 0,
        net_profit_eth REAL DEFAULT 0,
        eth_price_usd REAL DEFAULT 0,
        net_profit_usd REAL DEFAULT 0,
        status TEXT DEFAULT 'confirmed',
        notes TEXT DEFAULT ''
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS balances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        chain TEXT NOT NULL,
        wallet TEXT NOT NULL,
        balance_eth REAL DEFAULT 0,
        balance_usd REAL DEFAULT 0
    )""")
    conn.commit()
    return conn


class ProfitLedger:
    """Immutable P&L ledger for on-chain operations."""

    def __init__(self, db: Path = DB_PATH):
        self.conn = _init_db(db)

    def record_operation(
        self,
        chain: str,
        tx_hash: str,
        op_type: str,
        revenue_eth: float,
        gas_cost_eth: float,
        eth_price_usd: float = 3500.0,
        notes: str = "",
    ):
        now = datetime.now(timezone.utc).isoformat()
        net_eth = revenue_eth - gas_cost_eth
        net_usd = net_eth * eth_price_usd

        self.conn.execute(
            "INSERT OR IGNORE INTO operations "
            "(timestamp,chain,tx_hash,op_type,revenue_eth,gas_cost_eth,"
            "net_profit_eth,eth_price_usd,net_profit_usd,status,notes) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                now,
                chain,
                tx_hash,
                op_type,
                revenue_eth,
                gas_cost_eth,
                net_eth,
                eth_price_usd,
                net_usd,
                "confirmed",
                notes,
            ),
        )
        self.conn.commit()

    def record_balance(
        self, chain: str, wallet: str, balance_eth: float, eth_price_usd: float = 3500.0
    ):
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT INTO balances (timestamp,chain,wallet,balance_eth,balance_usd) VALUES (?,?,?,?,?)",
            (now, chain, wallet, balance_eth, balance_eth * eth_price_usd),
        )
        self.conn.commit()

    def get_summary(self) -> dict:
        """Get P&L summary."""
        row = self.conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(revenue_eth),0), COALESCE(SUM(gas_cost_eth),0), "
            "COALESCE(SUM(net_profit_eth),0), COALESCE(SUM(net_profit_usd),0) FROM operations"
        ).fetchone()
        return {
            "total_operations": row[0],
            "total_revenue_eth": row[1],
            "total_gas_eth": row[2],
            "net_profit_eth": row[3],
            "net_profit_usd": row[4],
        }

    def get_by_chain(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT chain, COUNT(*), SUM(net_profit_eth), SUM(net_profit_usd) "
            "FROM operations GROUP BY chain"
        ).fetchall()
        return [{"chain": r[0], "ops": r[1], "profit_eth": r[2], "profit_usd": r[3]} for r in rows]

    def export_csv(self, path: Path | None = None) -> Path:
        """Export all operations to CSV for fiscal compliance."""
        if path is None:
            path = DB_PATH.parent / "profit_ledger_export.csv"

        rows = self.conn.execute(
            "SELECT timestamp,chain,tx_hash,op_type,revenue_eth,gas_cost_eth,"
            "net_profit_eth,eth_price_usd,net_profit_usd,status,notes FROM operations ORDER BY timestamp"
        ).fetchall()

        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Timestamp",
                    "Chain",
                    "TX Hash",
                    "Type",
                    "Revenue (ETH)",
                    "Gas Cost (ETH)",
                    "Net Profit (ETH)",
                    "ETH Price (USD)",
                    "Net Profit (USD)",
                    "Status",
                    "Notes",
                ]
            )
            writer.writerows(rows)

        return path

    def close(self):
        self.conn.close()


if __name__ == "__main__":
    ledger = ProfitLedger()
    summary = ledger.get_summary()
    print(f"\n{'=' * 50}")
    print("CORTEX Profit Ledger — C5-REAL")
    print(f"{'=' * 50}")
    print(f"  Operations:    {summary['total_operations']}")
    print(f"  Revenue:       {summary['total_revenue_eth']:.6f} ETH")
    print(f"  Gas Costs:     {summary['total_gas_eth']:.6f} ETH")
    print(
        f"  Net Profit:    {summary['net_profit_eth']:.6f} ETH (${summary['net_profit_usd']:,.2f})"
    )

    by_chain = ledger.get_by_chain()
    if by_chain:
        print("\n  By Chain:")
        for c in by_chain:
            print(f"    {c['chain']}: {c['ops']} ops | {c['profit_eth']:.6f} ETH")

    csv_path = ledger.export_csv()
    print(f"\n  CSV: {csv_path}")
    ledger.close()
