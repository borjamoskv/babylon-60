#!/usr/bin/env python3
"""
rabby_audit.py — CORTEX Rabby Permission Auditor
Extrae y clasifica permisos de dApps desde chrome.storage.local de Rabby Wallet.

Uso:
    python3 rabby_audit.py [--db PATH] [--output json|table] [--profile default]

Prerequisitos:
    pip install ccl-chromium-reader
    Chrome debe estar CERRADO al ejecutar.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# ─── Constantes ───────────────────────────────────────────────────────────────

RABBY_EXTENSION_ID = "acmacodkjbdgmoleebolmdjonilkdbch"

CHROME_PROFILES = {
    "darwin": [
        Path.home() / "Library/Application Support/Google/Chrome/Default",
        Path.home() / "Library/Application Support/BraveSoftware/Brave-Browser/Default",
        Path.home() / "Library/Application Support/Microsoft Edge/Default",
        Path.home() / "Library/Application Support/Comet/Default",  # Comet browser
    ],
    "linux": [
        Path.home() / ".config/google-chrome/Default",
        Path.home() / ".config/chromium/Default",
        Path.home() / ".config/BraveSoftware/Brave-Browser/Default",
    ],
    "win32": [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/User Data/Default",
        Path(os.environ.get("LOCALAPPDATA", "")) / "BraveSoftware/Brave-Browser/User Data/Default",
    ],
}

# ─── Risk Matrix ──────────────────────────────────────────────────────────────

RISK_WEIGHTS: dict[str, int] = {
    "isMetamaskMode":         40,
    "isSigned_and_connected": 30,
    "account_bound":          20,
    "no_tls":                 25,
    "is_connected":           10,
    "non_eth_chain":           5,
}

RISK_LEVELS = [
    (70, "CRITICAL"),
    (45, "HIGH"),
    (20, "MEDIUM"),
    (0,  "LOW"),
]

ANSI = {
    "CRITICAL": "\033[91m",
    "HIGH":     "\033[93m",
    "MEDIUM":   "\033[94m",
    "LOW":      "\033[92m",
    "RESET":    "\033[0m",
    "BOLD":     "\033[1m",
    "DIM":      "\033[2m",
}

# ─── Localización de DB ───────────────────────────────────────────────────────

def find_db_path() -> Path | None:
    platform = sys.platform
    candidates = CHROME_PROFILES.get(platform, CHROME_PROFILES.get("linux", []))
    for profile in candidates:
        db = profile / "Local Extension Settings" / RABBY_EXTENSION_ID
        if db.exists():
            return db
    return None


# ─── Extracción LevelDB ───────────────────────────────────────────────────────

def read_leveldb(db_path: Path) -> dict[str, Any]:
    """
    Intenta leer el LevelDB con ccl_chromium_reader, con fallback a leveldb puro.
    Retorna el dict de todas las keys encontradas.
    """
    results: dict[str, Any] = {}

    # Intento 1: ccl_chromium_reader (más fiable para storage de extensiones)
    try:
        from ccl_chromium_reader import ccl_chromium_localstorage
        storage = ccl_chromium_localstorage.LocalStoreDb(db_path)
        for record in storage.iter_all_records():
            try:
                results[record.script_key] = json.loads(record.value) if record.value else None
            except (json.JSONDecodeError, Exception):
                results[record.script_key] = record.value
        return results
    except ImportError:
        pass
    except Exception as e:
        print(f"[WARN] ccl_chromium_reader falló: {e}", file=sys.stderr)

    # Intento 2: leveldb puro
    try:
        import leveldb  # type: ignore
        db = leveldb.LevelDB(str(db_path))
        for key, value in db.RangeIter():
            try:
                k = key.decode("utf-8").lstrip("\x00")
                v = json.loads(value.decode("utf-8"))
                results[k] = v
            except Exception:
                pass
        return results
    except ImportError:
        pass
    except Exception as e:
        print(f"[WARN] leveldb puro falló: {e}", file=sys.stderr)

    # Fallback: parseo manual de ficheros LODB (lectura cruda)
    return _raw_parse_ldb(db_path)


def _raw_parse_ldb(db_path: Path) -> dict[str, Any]:
    """
    Parseo crudo de ficheros .ldb/.log buscando la clave 'permission'.
    Último recurso — puede producir falsos positivos.
    """
    results: dict[str, Any] = {}
    for f in sorted(db_path.glob("*.ldb")) + sorted(db_path.glob("*.log")):
        try:
            data = f.read_bytes()
            # Buscar JSON arrays que contengan dumpCache
            start = data.find(b'"dumpCache"')
            if start == -1:
                continue
            # Retroceder hasta el { de apertura
            bracket = data.rfind(b"{", 0, start)
            if bracket == -1:
                continue
            # Tomar un slice generoso e intentar parsear
            chunk = data[bracket:bracket + 65536]
            try:
                obj = json.loads(chunk.decode("utf-8", errors="replace"))
                results["permission"] = obj
                break
            except json.JSONDecodeError:
                # Buscar el subarray dumpCache directamente
                arr_start = data.find(b"[{", start)
                arr_end = data.find(b"}]", arr_start) + 2
                if arr_start != -1 and arr_end > arr_start:
                    try:
                        arr = json.loads(data[arr_start:arr_end].decode("utf-8", errors="replace"))
                        results["permission"] = {"dumpCache": arr}
                        break
                    except Exception:
                        pass
        except Exception:
            continue
    return results


# ─── Parsing del PermissionStore ─────────────────────────────────────────────

def parse_permission_store(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extrae ConnectedSite[] desde el dumpCache del PermissionStore.
    Maneja tanto el formato directo como el wrapped en chrome.storage.local.
    """
    permission_data = None

    # Buscar la clave "permission" con posibles prefijos de chrome.storage
    for key in raw:
        normalized = key.strip().rstrip("\x00")
        if normalized in ("permission", "_rabby_permission", "permission\x00"):
            permission_data = raw[key]
            break

    if permission_data is None:
        # Buscar por contenido
        for key, value in raw.items():
            if isinstance(value, dict) and "dumpCache" in value:
                permission_data = value
                break

    if permission_data is None:
        return []

    dump_cache = permission_data.get("dumpCache", [])
    sites = []
    for entry in dump_cache:
        site = entry.get("v", {})
        if not site:
            continue
        sites.append(site)

    return sites


# ─── Clasificación de riesgo ─────────────────────────────────────────────────

def classify_site(site: dict[str, Any]) -> dict[str, Any]:
    score = 0
    flags: list[str] = []
    origin = site.get("origin", "")

    if site.get("isMetamaskMode"):
        score += RISK_WEIGHTS["isMetamaskMode"]
        flags.append("METAMASK_MODE_OVERRIDE")

    if site.get("isSigned") and site.get("isConnected"):
        score += RISK_WEIGHTS["isSigned_and_connected"]
        flags.append("SIGNED_AND_ACTIVE")

    if site.get("account"):
        score += RISK_WEIGHTS["account_bound"]
        flags.append("ACCOUNT_BOUND")

    if origin and not origin.startswith("https://"):
        score += RISK_WEIGHTS["no_tls"]
        flags.append("NO_TLS")

    if site.get("isConnected"):
        score += RISK_WEIGHTS["is_connected"]

    chain = site.get("chain", "ETH")
    if chain not in ("ETH", "MAINNET", "eth"):
        score += RISK_WEIGHTS["non_eth_chain"]
        flags.append(f"NON_ETH_CHAIN:{chain}")

    level = next(lvl for threshold, lvl in RISK_LEVELS if score >= threshold)

    return {
        "origin":       origin,
        "name":         site.get("name", ""),
        "chain":        chain,
        "isConnected":  site.get("isConnected", False),
        "isSigned":     site.get("isSigned", False),
        "isMetamaskMode": site.get("isMetamaskMode", False),
        "account":      site.get("account", {}).get("address", "") if site.get("account") else "",
        "risk_score":   score,
        "risk_level":   level,
        "flags":        flags,
    }


# ─── Output ───────────────────────────────────────────────────────────────────

def render_table(classified: list[dict[str, Any]]) -> None:
    sorted_sites = sorted(classified, key=lambda x: x["risk_score"], reverse=True)
    connected = [s for s in sorted_sites if s["isConnected"]]
    revoked = [s for s in sorted_sites if not s["isConnected"]]
    critical_count = sum(1 for s in connected if s["risk_level"] == "CRITICAL")
    high_count = sum(1 for s in connected if s["risk_level"] == "HIGH")

    print(f"\n{ANSI['BOLD']}{'═' * 70}{ANSI['RESET']}")
    print(f"{ANSI['BOLD']}  RABBY PERMISSION AUDIT{ANSI['RESET']}")
    print(f"  Conectados: {len(connected)}  |  Revocados: {len(revoked)}  "
          f"|  {ANSI['91m'] if critical_count else ''}CRITICAL: {critical_count}{ANSI['RESET']}  "
          f"|  HIGH: {high_count}")
    print(f"{ANSI['BOLD']}{'═' * 70}{ANSI['RESET']}\n")

    col_w = {"origin": 32, "chain": 10, "risk": 10, "flags": 30}
    header = (f"{'Origin':<{col_w['origin']}} "
              f"{'Chain':<{col_w['chain']}} "
              f"{'Risk':<{col_w['risk']}} "
              f"Flags")
    print(f"{ANSI['BOLD']}{header}{ANSI['RESET']}")
    print("─" * 90)

    for s in sorted_sites:
        color = ANSI.get(s["risk_level"], "")
        status = "" if s["isConnected"] else f"{ANSI['DIM']}[revocado] "
        origin_display = s["origin"][:col_w["origin"] - 1]
        chain_display = s["chain"][:col_w["chain"] - 1]
        flags_display = ",".join(s["flags"])[:col_w["flags"]]
        print(f"{status}{color}{origin_display:<{col_w['origin']}} "
              f"{chain_display:<{col_w['chain']}} "
              f"{s['risk_level']:<{col_w['risk']}} "
              f"{flags_display}{ANSI['RESET']}")

    print("\n" + "─" * 90)
    if critical_count > 0:
        print(f"\n{ANSI['CRITICAL']}{ANSI['BOLD']}⚠  {critical_count} sitio(s) CRITICAL — "
              f"revoca permisos en Rabby → Settings → Connected Sites{ANSI['RESET']}")


def render_json(classified: list[dict[str, Any]]) -> None:
    import datetime
    report = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "tool": "rabby-permission-auditor/v1.0",
        "summary": {
            "total": len(classified),
            "connected": sum(1 for s in classified if s["isConnected"]),
            "revoked": sum(1 for s in classified if not s["isConnected"]),
            "by_risk": {
                lvl: sum(1 for s in classified if s["risk_level"] == lvl)
                for lvl in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
            },
        },
        "sites": sorted(classified, key=lambda x: x["risk_score"], reverse=True),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rabby Permission Auditor — CORTEX Skill"
    )
    parser.add_argument(
        "--db", type=Path, default=None,
        help="Path explícito al directorio LevelDB de la extensión Rabby"
    )
    parser.add_argument(
        "--output", choices=["table", "json"], default="table",
        help="Formato de salida (default: table)"
    )
    parser.add_argument(
        "--include-revoked", action="store_true",
        help="Incluir sitios con isConnected=false en el output"
    )
    args = parser.parse_args()

    # 1. Localizar DB
    db_path = args.db or find_db_path()
    if not db_path:
        print("[ERROR] No se encontró la base de datos de Rabby.", file=sys.stderr)
        print("Asegúrate de que Rabby está instalado y Chrome cerrado.", file=sys.stderr)
        print(f"Path esperado: ~/Library/Application Support/Google/Chrome/Default/"
              f"Local Extension Settings/{RABBY_EXTENSION_ID}/", file=sys.stderr)
        sys.exit(1)

    if not db_path.exists():
        print(f"[ERROR] DB path no existe: {db_path}", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] DB localizada: {db_path}", file=sys.stderr)

    # 2. Extraer
    raw = read_leveldb(db_path)
    if not raw:
        print("[ERROR] LevelDB vacío o inaccesible. ¿Chrome está en ejecución?", file=sys.stderr)
        print("Cierra Chrome completamente e intenta de nuevo.", file=sys.stderr)
        sys.exit(1)

    # 3. Parsear
    sites = parse_permission_store(raw)
    if not sites:
        print("[WARN] No se encontraron sitios en permissionService.", file=sys.stderr)
        print("[INFO] Keys disponibles en storage:", list(raw.keys())[:20], file=sys.stderr)
        sys.exit(0)

    # 4. Clasificar
    classified = [classify_site(s) for s in sites]

    if not args.include_revoked:
        classified = [s for s in classified if s["isConnected"]]

    # 5. Output
    if args.output == "json":
        render_json(classified)
    else:
        render_table(classified)


if __name__ == "__main__":
    main()
