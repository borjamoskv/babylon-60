#!/usr/bin/env python3
"""
CORTEX-PERSIST ┃ MEDIA AUDIT SWARM (C5-REAL)
Asynchronous hardware-aligned swarm for auditing MP4/WAV files via ffprobe.
"""

import asyncio
import json
import os
import sqlite3
import subprocess
from pathlib import Path
import time
import sys

TARGET_DIR = "/Users/borjafernandezangulo/Music/VISUALES"
DB_PATH = "/Users/borjafernandezangulo/Music/VISUALES/audit_results.db"
CONCURRENCY_LIMIT = 32


async def audit_file(file_path: Path, semaphore: asyncio.Semaphore, db_conn):
    async with semaphore:
        result = {
            "file_path": str(file_path),
            "type": file_path.suffix.lower(),
            "status": "OK",
            "duration": 0.0,
            "error_log": "",
        }

        try:
            # Check container & streams with ffprobe
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_type,codec_name",
                "-of",
                "json",
                str(file_path),
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                result["status"] = "ERROR"
                result["error_log"] = stderr.decode().strip()
            else:
                data = json.loads(stdout.decode())
                result["duration"] = float(data.get("format", {}).get("duration", 0.0))

        except Exception as e:
            result["status"] = "CRITICAL_FAILURE"
            result["error_log"] = str(e)

        # Log to DB (blocking call but acceptable scale for SQLite)
        cursor = db_conn.cursor()
        cursor.execute(
            """
            INSERT INTO media_audit (file_path, file_type, status, duration, error_log)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                result["file_path"],
                result["type"],
                result["status"],
                result["duration"],
                result["error_log"],
            ),
        )
        db_conn.commit()

        return result


async def main():
    print(f"[*] Iniciando CORTEX Media Swarm en {TARGET_DIR}...")
    start_time = time.time()

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE media_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT,
            file_type TEXT,
            status TEXT,
            duration REAL,
            error_log TEXT
        )
    """)

    target_path = Path(TARGET_DIR)
    files = [f for f in target_path.rglob("*") if f.suffix.lower() in [".mp4", ".wav"]]

    print(f"[*] Detectados {len(files)} archivos para auditar.")
    if len(files) == 0:
        print("[!] No hay archivos. Abortando.")
        return

    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    tasks = [audit_file(f, semaphore, conn) for f in files]

    completed = 0
    total = len(tasks)

    for future in asyncio.as_completed(tasks):
        await future
        completed += 1
        sys.stdout.write(f"\r[*] Progreso del Enjambre: {completed}/{total} procesados...")
        sys.stdout.flush()

    print(f"\n[*] Auditoría completada en {time.time() - start_time:.2f}s.")

    cursor = conn.cursor()
    cursor.execute("SELECT status, COUNT(*) FROM media_audit GROUP BY status")
    stats = cursor.fetchall()

    print("\n=== REPORTE DE EXERGÍA ===")
    for stat in stats:
        print(f" - {stat[0]}: {stat[1]} archivos")
    print(f" - SQLite DB: {DB_PATH}")

    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
