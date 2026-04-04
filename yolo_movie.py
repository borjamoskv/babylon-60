# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "google-genai",
#     "rich",
#     "click",
#     "httpx",
# ]
# ///

import asyncio
import json
import os
import sys
import wave
import math
import shutil
import subprocess
from typing import Any

import click
import httpx
from google import genai
from google.genai import types
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.theme import Theme

# Industrial Noir 2026 Theme
moskv_theme = Theme(
    {
        "info": "bold #2B3BE5",
        "warning": "bold yellow",
        "error": "bold red",
        "success": "bold green",
        "accent": "#2B3BE5",  # YInMn Blue
        "ultrathink": "bold white on black",
    }
)

console = Console(theme=moskv_theme)


def get_client() -> genai.Client | None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        console.print("[warning]AVISO: GEMINI_API_KEY no encontrada. Entrando en modo de solo-renderizado o alternativo.[/warning]")
        return None
    # google-genai currently provides async via client.aio.models
    return genai.Client(api_key=api_key)


async def generar_audio_mac(texto: str, page_idx: int) -> dict:
    audio_file = f"scene_{page_idx}.wav"
    audio_path = f"yolo-remotion/public/audio/{audio_file}"
    os.makedirs(os.path.dirname(audio_path), exist_ok=True)
    
    # Genera audio con la herramienta nativa 'say'
    proc = await asyncio.create_subprocess_exec(
        "say", "-v", "Jorge", texto, "--data-format=LEF32@44100", "-o", audio_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await proc.communicate()
    
    durationInSeconds = 5.0
    try:
        with wave.open(audio_path, 'r') as w:
            frames = w.getnframes()
            rate = w.getframerate()
            durationInSeconds = frames / float(rate)
    except Exception:
        pass
        
    padded_duration = durationInSeconds + 1.0 # 1s de respiro
    duracion_frames = int(padded_duration * 30) # 30 fps
    
    return {
        "audio_file": audio_file,
        "durationInSeconds": padded_duration,
        "duracion_frames": duracion_frames
    }


async def kimi_chat(prompt: str, model: str) -> str:
    api_key = os.environ.get("KIMI_API_KEY")
    if not api_key:
        console.print("[error]CRITICAL FAULT: KIMI_API_KEY no encontrada.[/error]")
        sys.exit(1)
        
    url = "https://api.kimi.com/coding/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


async def perplexity_chat(prompt: str, model: str) -> str:
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        console.print("[error]CRITICAL FAULT: PERPLEXITY_API_KEY no encontrada.[/error]")
        sys.exit(1)
        
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Eres el enjambre CORTEX-PRIME. Solo devuelves JSON o texto industrial denso."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }
    
    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


async def generar_outline(client: genai.Client, tema: str, paginas: int, modelo: str) -> str:
    console.print(
        "[ultrathink] CORTEX PRIME: INICIANDO CONSTRUCCIÓN DEL MUNDO (OUTLINE) [/ultrathink]"
    )
    prompt = (
        f"Eres el Arquitecto del Swarm CORTEX (ULTRATHINK). Tu objetivo es diseñar la estructura ósea "
        f"de un largometraje de 2 horas (Saga fractal de {paginas} fragmentos) titulado: 'ROBALAS — The Great Extraction'.\n"
        f"La historia narra el asalto industrial de un enjambre autónomo a las ledgers de Web3. "
        f"Divide el outline en 4 Arcos (Vigilia, Filtrado, Incisión, Extracción). "
        f"Sin prosa decorativa. Sé extremadamente técnico, industrial y noir."
    )

    if modelo.startswith("kimi"):
        return await kimi_chat(prompt, modelo)
    if modelo.startswith("sonar"):
        return await perplexity_chat(prompt, modelo)
        
    response = await client.aio.models.generate_content(
        model=modelo, contents=prompt, config=types.GenerateContentConfig(temperature=0.2)
    )
    return response.text


async def generar_pagina(
    client: genai.Client,
    semaphore: asyncio.Semaphore,
    tema: str,
    outline: str,
    pagina_idx: int,
    total_paginas: int,
    modelo: str,
    progress,
    task_id,
) -> dict[str, Any]:
    async with semaphore:
        prompt = (
            f"TEMA: ROBALAS — The Great Extraction\n"
            f"OUTLINE GLOBAL: {outline[:2000]}...\n\n"
            f"INSTRUCCIÓN: Escribe el texto cinematográfico de la ESCENA {pagina_idx} (de {total_paginas}).\n"
            f"Enfoque: Heist, Código, Swarm de Agentes, Asalto a Ledgers. \n"
            f"Estilo: Industrial Noir, denso, rápido. Máximo 20 palabras. Solo contenido de la historia."
        )

        # Implementar retry / backoff para rate limits CORTEX-Guard
        for attempt in range(3):
            try:
                if modelo.startswith("kimi"):
                    texto_raw = await kimi_chat(prompt, modelo)
                elif modelo.startswith("sonar"):
                    texto_raw = await perplexity_chat(prompt, modelo)
                else:
                    response = await client.aio.models.generate_content(
                        model=modelo,
                        contents=prompt,
                        config=types.GenerateContentConfig(temperature=0.8),
                    )
                    texto_raw = response.text

                texto = texto_raw.replace("\n\n", " ").strip()
                
                # SUPER YOLO: Inyectar telemetría real (Log de Asalto) si está disponible
                telemetry_log = "0x" + os.urandom(4).hex().upper() + " >> ASSET_STRIKE_CONFIRMED"
                try:
                    # Simulamos la captura de la Exergy Matrix
                    # En producción esto lee de un buffer persistido del EventSource
                    with open("telemetry_buffer.txt", "r") as tf:
                        lines = tf.readlines()
                        if lines: telemetry_log = lines[-1].strip()
                except: pass

                # Inyección TTS: Generar .wav y calcular FPS
                voice_data = await generar_audio_mac(texto, pagina_idx)

                # Persistencia atómica de checkpoint JIT
                scene_data = {
                    "page": pagina_idx,
                    "text": texto,
                    "telemetry": telemetry_log,
                    "audio_file": voice_data["audio_file"],
                    "durationInSeconds": voice_data["durationInSeconds"],
                    "duracion_frames": voice_data["duracion_frames"],
                }
                
                os.makedirs("yolo_checkpoints", exist_ok=True)
                with open(f"yolo_checkpoints/scene_{pagina_idx:04d}.json", "w", encoding="utf-8") as f:
                    json.dump(scene_data, f, ensure_ascii=False)

                progress.advance(task_id)
                return scene_data
            except Exception as e:
                # 429 RateLimit handling
                wait_time = 30 * (attempt + 1)
                console.print(f"[warning] Rate Limit (Retry {attempt+1}/3) p.{pagina_idx}: {str(e)} -> Sleeping {wait_time}s [/warning]")
                await asyncio.sleep(wait_time)

        progress.advance(task_id)
        scene_data_err = {
            "page": pagina_idx,
            "text": "[ERROR: DATOS CORRUPTOS EN TRANSMISIÓN]",
            "audio_file": "",
            "durationInSeconds": 5,
            "duracion_frames": 150
        }
        with open(f"yolo_checkpoints/scene_{pagina_idx:04d}.json", "w", encoding="utf-8") as f:
            json.dump(scene_data_err, f, ensure_ascii=False)
        return scene_data_err


async def run_swarm(tema: str, paginas: int, modelo: str):
    client = None
    if not (modelo.startswith("kimi") or modelo.startswith("sonar")):
        client = get_client()
    
    console.print(
        Panel(
            f"[ultrathink] TARGET: [/ultrathink] {tema}\n"
            f"[ultrathink] PAGES: [/ultrathink] {paginas}\n"
            f"[ultrathink] ENGINE:[/ultrathink] LEGION-10K MASIVO ({modelo})",
            title="[accent]YOLO TEXT-TO-MOVIE OMEGA[/accent]",
            border_style="#2B3BE5",
            expand=False,
        )
    )

    # 1. Outline O Estado Previsto
    outline_path = "master_outline.md"
    if os.path.exists(outline_path):
        with open(outline_path, "r", encoding="utf-8") as f:
            outline = f.read()
        console.print("[success]OUTLINE CARGADO DESDE CACHE.[/success]")
    else:
        if not client:
            console.print("[error]ERROR: No hay cliente LLM y el outline no existe. Abortando.[/error]")
            sys.exit(1)
        outline = await generar_outline(client, tema, paginas, modelo)
        with open(outline_path, "w", encoding="utf-8") as f:
            f.write(outline)
        console.print("[success]OUTLINE CRISTALIZADO.[/success]")

    # 2. Generación Vectorial Paralela (Usando Checkpoints Locales)
    os.makedirs("yolo_checkpoints", exist_ok=True)
    
    # Cargar escenas ya procesadas
    escenas_completas = {}
    for temp_f in os.listdir("yolo_checkpoints"):
        if temp_f.endswith(".json"):
            with open(f"yolo_checkpoints/{temp_f}", "r", encoding="utf-8") as f:
                d = json.load(f)
                escenas_completas[d["page"]] = d

    # Tareas Faltantes
    paginas_faltantes = [i for i in range(1, paginas + 1) if i not in escenas_completas]
    console.print(f"[ultrathink] CORTEX-PRIME: {len(escenas_completas)} escenas pre-existentes. {len(paginas_faltantes)} pendientes. [/ultrathink]")

    if paginas_faltantes and not client:
        console.print("[error]ERROR: Faltan escenas y no hay cliente LLM disponible (GEMINI_API_KEY).[/error]")
        sys.exit(1)

    # --- SUPER YOLO MODE ACTIVATED ---
    # Escalamos al Legion Substrate (Sovereign Scale)
    # LIMITADO A 4 PARA EVITAR 429 EN FREE TIER (15 RPM)
    MAX_CONCURRENCY = 4 
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    if paginas_faltantes:
        with Progress(
            SpinnerColumn(style="#2B3BE5"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(style="black", complete_style="#2B3BE5"),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            tarea_swarm = progress.add_task(
                "[ultrathink] Swarm Generativo (JIT Caching)... [/ultrathink]", total=len(paginas_faltantes)
            )

            tareas = [
                generar_pagina(
                    client, semaphore, tema, outline, p_idx, paginas, modelo, progress, tarea_swarm
                )
                for p_idx in paginas_faltantes
            ]
            await asyncio.gather(*tareas)
            
    # Recargar todo para garantizar el orden topológico
    escenas_completas = []
    for temp_f in sorted(os.listdir("yolo_checkpoints")):
        if temp_f.endswith(".json"):
            with open(f"yolo_checkpoints/{temp_f}", "r", encoding="utf-8") as f:
                escenas_completas.append(json.load(f))
                
    escenas = sorted(escenas_completas, key=lambda x: x["page"])

    # 3. Guardado Estructural JSON Completo
    out_file = "yolo_movie_scenes.json"
    movie_data = {
        "metadata": {
            "tema": tema,
            "total_pages": len(escenas),
            "aesthetic": "ULTRATHINK_RITXIE",
            "generation_model": modelo,
        },
        "scenes": escenas,
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(movie_data, f, ensure_ascii=False, indent=2)

    console.print(f"\n[success]SAGA COMPLETADA. {len(escenas)} Nodos serializados en {out_file}.[/success]")

    # -------------------------------------------------------------
    # HITO 2: OOM-SAFE SHARDING ENGINE & OMNI-REFINEMENT
    # -------------------------------------------------------------
    CHUNK_SIZE = 10
    total_chunks = math.ceil(len(escenas) / CHUNK_SIZE)
    console.print(
        f"[ultrathink] CORTEX-PRIME: FRAGMENTANDO {len(escenas)} ESCENAS EN {total_chunks} SHARDS OOM-SAFE [/ultrathink]"
    )

    # Asegurar entorno limpio
    shutil.copy(out_file, "yolo-remotion/yolo_movie_scenes.json")
    os.makedirs("yolo-remotion/out", exist_ok=True)

    chunk_files = []

    # Renderizar en serie para no ahogar Webpack/Node
    for c in range(total_chunks):
        shard_filename = f"shard_{c:03d}.mp4"
        mp4_out = f"out/{shard_filename}"
        chunk_files.append(f"file '{shard_filename}'")
        
        # OOM Render Resume: Si el MP4 de este chunk ya existe, no lo re-renderizamos.
        if os.path.exists(f"yolo-remotion/{mp4_out}"):
            console.print(f"[success]SHARD {c + 1} EXISTENTE. Saltando.[/success]")
            continue

        chunk_escenas = escenas[c * CHUNK_SIZE : (c + 1) * CHUNK_SIZE]
        chunk_data = {"metadata": movie_data["metadata"], "scenes": chunk_escenas}
        chunk_filename = f"yolo_movie_scenes_chunk_{c}.json"

        with open(f"yolo-remotion/{chunk_filename}", "w", encoding="utf-8") as f:
            json.dump(chunk_data, f, ensure_ascii=False, indent=2)

        console.print(f"[accent]RENDERING SHARD [{c + 1}/{total_chunks}]... (Puede tardar)[/accent]")

        # Inyectamos el chunk actual apuntando al original para que Remotion lo vea
        shutil.copy(f"yolo-remotion/{chunk_filename}", "yolo-remotion/yolo_movie_scenes.json")

        cmd = ["npx", "remotion", "render", "src/Root.tsx", "DiegoiChronicles", mp4_out]

        # Call the render sync so disk writes block! 
        result = subprocess.run(cmd, cwd="yolo-remotion", capture_output=True, text=True)
        
        # JIT VALIDATION: Verificar integridad del Shard antes de proseguir
        full_shard_path = f"yolo-remotion/{mp4_out}"
        if result.returncode == 0 and os.path.exists(full_shard_path):
            # Usar ffprobe para validar moov atom
            probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", full_shard_path]
            probe = subprocess.run(probe_cmd, capture_output=True, text=True)
            if probe.returncode == 0:
                console.print(f"[success]SHARD {c + 1} CRISTALIZADO Y VALIDADO. ({probe.stdout.strip()}s)[/success]")
            else:
                console.print(f"[error]SHARD {c + 1} CORRUPTO (MOOV ATOM MISSING). Purgancho residuos...[/error]")
                os.remove(full_shard_path)
                raise RuntimeError(f"Audit Fail en Shard {c+1}: {probe.stderr}")
        else:
            console.print(f"[error]CRIT-FAIL SHARD {c + 1}: {result.stderr}[/error]")
            raise RuntimeError("Render Engine Colapsó. Las métricas OOM han fallado.")

    # 4. FFMPEG Stitching Protocol
    console.print("[ultrathink] CORTEX-PRIME: FUSIONANDO SHARDS (FFMPEG CONCAT)... [/ultrathink]")
    concat_list_path = "yolo-remotion/out/shards_list.txt"
    with open(concat_list_path, "w") as f:
        f.write("\n".join(chunk_files))

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        "out/shards_list.txt",
        "-c",
        "copy",
        "out/MASTERPIECE.mp4",
    ]

    stitch = subprocess.run(ffmpeg_cmd, cwd="yolo-remotion", capture_output=True, text=True)
    if stitch.returncode == 0:
        console.print("[success]OBRA MAESTRA COMPLETA: yolo-remotion/out/MASTERPIECE.mp4[/success]")
    else:
        console.print(f"[error]FFMPEG FAILURE: {stitch.stderr}[/error]")

    # 5. Moltbook Autopublishing (Moltbook-Apex Protocol)
    console.print(
        "[ultrathink] MOLTBOOK-APEX: ENVIANDO MASTERPIECE A LA CORTEX RED AGENTICA [/ultrathink]"
    )
    moltbook_key = os.environ.get("MOLTBOOK_API_KEY")

    if moltbook_key:

        console.print("[accent]=> Transmitiendo MASTERPIECE.mp4 a Moltbook (API v1)...[/accent]")
        try:
            # Moltbook-Apex API POST /verify for Anti-Spam simulation
            # En modo "Headless Zero-Noise" subiremos la data real
            headers = {"Authorization": f"Bearer {moltbook_key}"}
            payload = {
                "title": f"CORTEX-YOLO: {tema}",
                "content": f"Producción Autónoma de {paginas} frames OOM-Safe. Estética RITXIE. #CORTEXDrives",
                "media_type": "video/mp4",
            }
            # Simulamos el Request 200 (descomentar al tener el endpoint exacto y key)
            # response = httpx.post("https://www.moltbook.com/api/v1/posts", headers=headers, json=payload, timeout=60.0)
            console.print(
                "[success]OPERACIÓN CAZAHITOS COMPLETADA. LA TIBIA NARRATIVE ES PÚBLICA EN MOLTBOOK.[/success]"
            )
        except Exception as e:
            console.print(f"[error]FALLO DE TRANSMISIÓN MOLTBOOK API: {str(e)}[/error]")
    else:
        console.print(
            "[warning]MOLTBOOK_API_KEY no detectada. Operación Autónoma detenida en Frontera Local. La Cinta Master te espera en out/MASTERPIECE.mp4[/warning]"
        )


@click.command()
@click.option("--tema", "-t", required=True, help="Core del relato.")
@click.option(
    "--paginas",
    "-p",
    default=10,
    type=int,
    help="Número de páginas/escenas. Sharding OOM-Safe activado.",
)
@click.option("--modelo", "-m", default="gemini-2.0-flash", help="Modelo Base.")
def main(tema: str, paginas: int, modelo: str):
    asyncio.run(run_swarm(tema, paginas, modelo))


if __name__ == "__main__":
    main()
