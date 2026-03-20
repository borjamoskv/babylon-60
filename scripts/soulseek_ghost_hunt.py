#!/usr/bin/env python3
"""
SOULSEEK GHOST_HUNT — CORTEX Archivist Omega
Protocolo de caza autónoma para slskd daemon (localhost:5030)
Strict Mimetics Gate: FLAC > WAV > MP3 320kbps CBR (fallback)

Uso:
    pip install httpx
    python soulseek_ghost_hunt.py
    python soulseek_ghost_hunt.py --status   # ver estado de búsquedas activas
"""

import argparse
import asyncio
import json
import logging
import uuid
from datetime import datetime

import httpx

# ─── Configuración ──────────────────────────────────────────────────────────

SLSKD_BASE   = "http://localhost:5030/api/v0"
SLSKD_TOKEN  = "changeme"          # JWT token del slskd.yml → apiKeys
LOG_FILE     = "/tmp/ghost_hunt.log"
RESULTS_FILE = "/tmp/ghost_hunt_results.json"

AUTH_HEADERS = {
    "X-API-Key": SLSKD_TOKEN,
    "Content-Type": "application/json",
}

FORMAT_PRIORITY = ["FLAC", "WAV", "MP3 320"]  # cascada de calidad

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE),
    ],
)
log = logging.getLogger("ghost_hunt")

# ─── Tracklist Queue ─────────────────────────────────────────────────────────

HUNT_QUEUE = [
    {"artist": "Volpe (ARG)",                        "title": "Failures Point To The Future"},
    {"artist": "Heiko Laux",                          "title": "Every Thought Is Evolution"},
    {"artist": "Batu",                                "title": "Meridian"},
    {"artist": "Oisel",                               "title": "Celeste"},
    {"artist": "SBWT Sub Basics Witch Trials",        "title": "More Water"},
    {"artist": "Deluka",                              "title": "Bunker"},
    {"artist": "Sven Väth",                           "title": "Schubdüse"},
    {"artist": "Bandulu",                             "title": "Ishmalite"},
    {"artist": "Shinichi Atobe",                      "title": "So Good So Right"},
    {"artist": "Overmono",                            "title": "Front"},
    {"artist": "Pearson Sound",                       "title": "Earwig"},
    {"artist": "Bullion",                             "title": "Blue Pedro"},
    {"artist": "DJ AEDIDIAS",                         "title": "REAL FRIENDS"},
    {"artist": "Unknown Mortal Orchestra",            "title": "Hunnybee"},
]

# ─── Core ────────────────────────────────────────────────────────────────────

async def ping_daemon(client: httpx.AsyncClient) -> bool:
    """Verifica que slskd esté activo y autenticado."""
    try:
        r = await client.get("/application", headers=AUTH_HEADERS, timeout=5.0)
        if r.status_code == 200:
            data = r.json()
            log.info(f"slskd operativo — versión {data.get('version', 'unknown')}")
            return True
        log.error(f"slskd respondió {r.status_code}: {r.text[:200]}")
        return False
    except (httpx.ConnectError, httpx.TimeoutException):
        log.error("slskd no responde en localhost:5030. ¿Está el daemon activo?")
        return False


async def submit_search(
    client: httpx.AsyncClient,
    artist: str,
    title: str,
    fmt: str,
) -> str | None:
    """Envía una búsqueda a slskd. Retorna el search_id o None."""
    search_text = f"{artist} {title} {fmt}"
    payload = {
        "id":         str(uuid.uuid4()),
        "searchText": search_text,
        "filterResponses": False,
        "maximumPeerQueueLength": 50,
        "minimumPeerUploadSpeed": 0,
        "responseLimit": 100,
        "fileLimit": 10000,
    }
    try:
        r = await client.post("/searches", json=payload, headers=AUTH_HEADERS, timeout=10.0)
        if r.status_code in (200, 201):
            search_id = r.json().get("id") or payload["id"]
            log.info(f"  ↳ Búsqueda enviada [{fmt}] search_id={search_id}")
            return search_id
        log.warning(f"  ↳ slskd rechazó búsqueda [{fmt}]: {r.status_code}")
        return None
    except Exception as e:
        log.error(f"  ↳ Error al enviar búsqueda: {e}")
        return None


async def poll_search(
    client: httpx.AsyncClient,
    search_id: str,
    timeout_s: int = 30,
) -> list[dict]:
    """Espera que la búsqueda complete y retorna los resultados."""
    deadline = asyncio.get_event_loop().time() + timeout_s
    while asyncio.get_event_loop().time() < deadline:
        try:
            r = await client.get(
                f"/searches/{search_id}/responses",
                headers=AUTH_HEADERS,
                timeout=10.0,
            )
            if r.status_code == 200:
                responses = r.json()
                if responses:
                    return responses
        except Exception:
            pass
        await asyncio.sleep(3)
    return []


def score_file(filename: str, size_bytes: int) -> int:
    """
    Strict Mimetics Gate — puntúa un archivo candidato.
    Mayor score = mayor prioridad.
    """
    score = 0
    fname = filename.lower()

    # Formato
    if fname.endswith(".flac"):  score += 100
    elif fname.endswith(".wav"): score += 80
    elif fname.endswith(".aif") or fname.endswith(".aiff"): score += 75
    elif fname.endswith(".mp3"): score += 20
    else:                        score -= 50  # rechazo

    # Tamaño mínimo (anti-transcode: un FLAC de 3min < 10MB = sospechoso)
    if size_bytes > 30_000_000:  score += 30   # > 30MB: probable 24bit o sin pérdida real
    elif size_bytes > 10_000_000: score += 15
    elif size_bytes < 5_000_000:  score -= 40  # demasiado pequeño para FLAC real

    # Señales de rip de calidad
    if "eac" in fname or "xld" in fname:    score += 20
    if "24bit" in fname or "24-bit" in fname: score += 25
    if "96khz" in fname or "48khz" in fname:  score += 15

    return score


def filter_results(responses: list[dict], fmt: str) -> list[dict]:
    """Aplica Strict Mimetics Gate a los resultados crudos de slskd."""
    candidates = []
    ext = fmt.split()[0].lower()  # "FLAC" → "flac"

    for peer_response in responses:
        username = peer_response.get("username", "unknown")
        upload_speed = peer_response.get("uploadSpeed", 0)
        queue_len    = peer_response.get("queueLength", 999)

        # Filtro de calidad de peer
        if queue_len > 200:  # relajado para sesión fría
            continue
        if upload_speed < 50_000:  # < 50 KB/s (era 500)
            continue

        for file_info in peer_response.get("files", []):
            filename   = file_info.get("filename", "")
            size_bytes = file_info.get("size", 0)

            if not filename.lower().endswith(f".{ext}"):
                continue

            sc = score_file(filename, size_bytes)
            if sc < 0:
                continue

            candidates.append({
                "username":     username,
                "filename":     filename,
                "size_mb":      round(size_bytes / 1_048_576, 2),
                "score":        sc,
                "upload_speed": round(upload_speed / 1024, 1),  # KB/s
                "queue_length": queue_len,
            })

    candidates.sort(key=lambda x: (-x["score"], -x["upload_speed"]))
    return candidates


async def hunt_track(
    client: httpx.AsyncClient,
    track: dict,
) -> dict:
    """
    GHOST_HUNT completo para una pista.
    Cascade: FLAC → WAV → MP3 320 (fallback extremo).
    """
    artist = track["artist"]
    title  = track["title"]
    log.info(f"\n{'─'*60}")
    log.info(f"  GHOST_HUNT: {artist} — {title}")

    result = {
        "artist":     artist,
        "title":      title,
        "timestamp":  datetime.utcnow().isoformat(),
        "status":     "NOT_FOUND",
        "candidates": [],
        "format":     None,
    }

    for fmt in FORMAT_PRIORITY:
        log.info(f"  Protocolo [{fmt}] iniciado")
        search_id = await submit_search(client, artist, title, fmt)
        if not search_id:
            continue

        # Tiempo de descubrimiento de red (extendido para sesión fría)
        await asyncio.sleep(20)  # era 15

        raw = await poll_search(client, search_id, timeout_s=60)  # era 30
        candidates = filter_results(raw, fmt)

        if candidates:
            result["status"]     = "FOUND"
            result["candidates"] = candidates[:5]  # top 5
            result["format"]     = fmt
            log.info(
                f"  ✓ {len(candidates)} candidatos encontrados en [{fmt}]. "
                f"Top: {candidates[0]['filename']} ({candidates[0]['size_mb']} MB, "
                f"score={candidates[0]['score']})"
            )
            break
        else:
            log.warning(f"  ✗ Sin resultados [{fmt}]. Escalando al siguiente tier.")

    if result["status"] == "NOT_FOUND":
        log.error(f"  ✗✗ PISTA NO ENCONTRADA: {artist} — {title}")

    return result


async def check_status(client: httpx.AsyncClient) -> None:
    """Muestra búsquedas activas en slskd."""
    r = await client.get("/searches", headers=AUTH_HEADERS, timeout=5.0)
    if r.status_code == 200:
        searches = r.json()
        log.info(f"Búsquedas activas: {len(searches)}")
        for s in searches:
            log.info(f"  [{s.get('state')}] {s.get('searchText')} — {s.get('fileCount', 0)} archivos")
    else:
        log.error(f"Error obteniendo estado: {r.status_code}")


# ─── Entry Point ─────────────────────────────────────────────────────────────

async def main(status_only: bool = False) -> None:
    async with httpx.AsyncClient(base_url=SLSKD_BASE) as client:
        if not await ping_daemon(client):
            log.error("Abortando: daemon slskd inaccesible.")
            return

        if status_only:
            await check_status(client)
            return

        log.info(f"Iniciando GHOST_HUNT — {len(HUNT_QUEUE)} pistas en queue")
        all_results = []

        for track in HUNT_QUEUE:
            result = await hunt_track(client, track)
            all_results.append(result)
            # Pausa anti-ban entre búsquedas
            await asyncio.sleep(5)

        # Persistencia de resultados
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        log.info(f"\nResultados guardados en {RESULTS_FILE}")

        # Resumen
        found    = [r for r in all_results if r["status"] == "FOUND"]
        notfound = [r for r in all_results if r["status"] == "NOT_FOUND"]
        log.info(f"\n{'═'*60}")
        log.info(f"  RESUMEN: {len(found)}/{len(HUNT_QUEUE)} pistas localizadas")
        for r in notfound:
            log.warning(f"  ✗ FANTASMA: {r['artist']} — {r['title']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CORTEX Soulseek Ghost Hunt")
    parser.add_argument("--status", action="store_true", help="Ver búsquedas activas en slskd")
    parser.add_argument("--token",  type=str, help="slskd API key (override)")
    args = parser.parse_args()

    if args.token:
        AUTH_HEADERS["X-API-Key"] = args.token

    asyncio.run(main(status_only=args.status))
