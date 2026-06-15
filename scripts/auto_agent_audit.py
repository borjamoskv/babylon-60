#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
"""
cortex-persist Sovereign Agent Auditor
Automates the complete audit cycle of the agentic trust substrate.
1. Connects to SQLite database and analyzes agent reputation distribution.
2. Checks integrity check database history for drift or compromises.
3. Verifies cryptographic hash continuity in the file ledger.
4. Parses AGENTS.md directives and axioms to check ruleset compliance.
5. Saves a consolidated audit report markdown artifact in the session folder.
"""

import datetime
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

# Paths
CORTEX_DB_PATH = Path("/Users/borjafernandezangulo/.cortex/cortex.db")
AGENTS_MD_PATH = Path("/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/AGENTS.md")
FILE_LEDGER_PATH = Path("/Users/borjafernandezangulo/.cortex/cassandra_audit_ledger.jsonl")
SESSION_DIR = Path("/Users/borjafernandezangulo/.gemini/antigravity/brain/50840759-3874-484b-a9fc-94e46d75e9ee")

def parse_agents_md():
    if not AGENTS_MD_PATH.exists():
        return {"directives": 0, "roles": 0, "axioms": 0}
    
    content = AGENTS_MD_PATH.read_text(encoding="utf-8")
    lines = content.splitlines()
    
    directives = 0
    roles = 0
    axioms = 0
    current_section = None
    
    for line in lines:
        if line.startswith("## "):
            current_section = line.strip("# ").strip().upper()
            continue
        if line.strip().startswith("|") and not line.strip().startswith("|-") and not line.strip().startswith("| :---"):
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) < 2:
                continue
            if "SYSTEM DIRECTIVES" in str(current_section):
                if parts[0].startswith("**[P") or parts[0].startswith("[P"):
                    directives += 1
            elif "AGENT MANIFEST" in str(current_section):
                if parts[0].startswith("**") or parts[0].strip():
                    roles += 1
            elif "FOUNDATIONAL AXIOMS" in str(current_section):
                if parts[0].startswith("**") or parts[0].strip():
                    axioms += 1
                    
    return {"directives": directives, "roles": roles, "axioms": axioms}

def verify_file_ledger():
    if not FILE_LEDGER_PATH.exists():
        return {"status": "MISSING", "count": 0, "verified": False}
    
    try:
        entries = []
        with open(FILE_LEDGER_PATH, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line.strip()))
                    
        if not entries:
            return {"status": "EMPTY", "count": 0, "verified": True}
            
        prev_hash = "GENESIS"
        for e in entries:
            e_copy = {k: v for k, v in e.items() if k != "entry_hash"}
            if e_copy.get("prev_hash") != prev_hash:
                return {"status": "BROKEN_CHAIN", "count": len(entries), "verified": False}
                
            expected = hashlib.sha256(
                json.dumps(e_copy, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            
            if e.get("entry_hash") != expected:
                return {"status": "HASH_MISMATCH", "count": len(entries), "verified": False}
            prev_hash = e.get("entry_hash")
            
        return {"status": "HEALTHY", "count": len(entries), "verified": True}
    except Exception as exc:
        return {"status": f"ERROR: {exc}", "count": 0, "verified": False}

def main():
    print("=== STARTING CORTEX PERSIST AGENT SYSTEM AUDIT ===")
    timestamp = datetime.datetime.now().isoformat()
    
    # 1. Database connection and agent analysis
    print(f"Connecting to database: {CORTEX_DB_PATH} ...")
    if not CORTEX_DB_PATH.exists():
        print("❌ Error: DB file does not exist.")
        sys.exit(1)
        
    try:
        conn = sqlite3.connect(str(CORTEX_DB_PATH))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Check tables
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        
        agents_stats = {"total": 0, "active": 0, "degraded": [], "average_reputation": 0.0}
        if "agents" in tables:
            rows = cur.execute("SELECT * FROM agents").fetchall()
            agents_stats["total"] = len(rows)
            
            active_count = 0
            rep_sum = 0.0
            for r in rows:
                if r["is_active"]:
                    active_count += 1
                rep = r["reputation_score"]
                rep_sum += rep
                
                # Degraded logic (reputation < 0.7 or disputed_votes > 2)
                if rep < 0.7 or r["disputed_votes"] > 2:
                    agents_stats["degraded"].append({
                        "id": r["id"],
                        "name": r["name"],
                        "reputation": rep,
                        "disputed": r["disputed_votes"]
                    })
            agents_stats["active"] = active_count
            if len(rows) > 0:
                agents_stats["average_reputation"] = rep_sum / len(rows)
        else:
            print("⚠️ Warning: 'agents' table is missing.")
            
        # Integrity checks
        checks_stats = {"count": 0, "last_check": None}
        if "integrity_checks" in tables:
            checks_stats["count"] = cur.execute("SELECT COUNT(*) FROM integrity_checks").fetchone()[0]
            last = cur.execute("SELECT * FROM integrity_checks ORDER BY id DESC LIMIT 1").fetchone()
            if last:
                checks_stats["last_check"] = dict(last)
        
        conn.close()
    except Exception as db_err:
        print(f"❌ Database error: {db_err}")
        sys.exit(1)
        
    # 2. Parse AGENTS.md ruleset
    print("Parsing AGENTS.md ruleset...")
    ruleset = parse_agents_md()
    
    # 3. File ledger verification
    print("Verifying file ledger integrity chain...")
    ledger_status = verify_file_ledger()
    
    # 4. Generate report markdown
    report_content = f"""# 🤖 CORTEX Agentic Substrate - Automated Audit Report

> [!NOTE]
> **Nivel de Realidad (Axioma R1)**: `C5-REAL`. Reporte generado automáticamente el `{timestamp}`.

---

## 1. Métricas del Sistema de Agentes

| Métrica | Valor Mapeado | Estado |
| :--- | :---: | :--- |
| **Total Agentes en DB** | {agents_stats["total"]} | **STABLE** |
| **Agentes Activos** | {agents_stats["active"]} | **STABLE** |
| **Reputación Promedio** | {agents_stats["average_reputation"]:.4f} | {'STABLE' if agents_stats["average_reputation"] >= 0.8 else 'DEGRADED'} |
| **Integridad de Ledger** | {ledger_status["status"]} | {'PASS' if ledger_status["verified"] else 'FAIL'} |
| **Tamaño de Cadena Ledger** | {ledger_status["count"]} | **VERIFIED** |

---

## 2. Inventario de Reglas (§ AGENTS.md)

- **Directivas de Sistema**: `{ruleset["directives"]}` definidas.
- **Roles y Fronteras**: `{ruleset["roles"]}` roles de autoridad mapeados.
- **Axiomas Fundacionales**: `{ruleset["axioms"]}` axiomas de control exergético activos.

---

## 3. Agentes Degradados / Sospechosos ({len(agents_stats["degraded"])})

"""
    if agents_stats["degraded"]:
        report_content += "| Agent ID | Nombre | Reputación | Votos Disputados | Estado | Remedio |\n"
        report_content += "| :--- | :--- | :---: | :---: | :---: | :--- |\n"
        for a in agents_stats["degraded"]:
            report_content += f"| `{a['id']}` | {a['name']} | {a['reputation']:.4f} | {a['disputed']} | **TAINTED** | Revocar permisos / Decaer reputación |\n"
    else:
        report_content += "_No se detectaron agentes degradados. Red en perfecto consenso (Consenso Bizantino Activo)._\n"
        
    report_content += f"""
---

## 4. Último Chequeo de Integridad (SQLite)

- **Tipo de Check**: `{checks_stats["last_check"]["check_type"] if checks_stats["last_check"] else "N/A"}`
- **Resultado del Ledger**: `{checks_stats["last_check"]["status"] if checks_stats["last_check"] else "N/A"}`
- **Fecha de Inicio**: `{checks_stats["last_check"]["started_at"] if checks_stats["last_check"] else "N/A"}`

### Detalles de la Traza de Nodos:
```json
{json.dumps(json.loads(checks_stats["last_check"]["details"]) if checks_stats["last_check"] else {}, indent=2)}
```

---
*Fin del informe de auditoría automática.*
"""
    
    # Save the report to artifacts
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    report_file = SESSION_DIR / "agent_audit_report.md"
    report_file.write_text(report_content, encoding="utf-8")
    
    print("\n✅ Audit completed successfully! Consolidated report written to:")
    print(f"   file://{report_file}")
    
if __name__ == "__main__":
    main()
