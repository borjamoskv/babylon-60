import asyncio

import click

from cortex.cli.common import console
from cortex.gateway.adapters.suno_adapter import suno_detective_inverso, suno_generate


@click.group()
def suno_cmds():
    """Comandos para el motor de música Suno (V4/V5 + Detective)."""
    pass


@suno_cmds.command("generate")
@click.argument("prompt")
@click.option("--model", default="chirp-v4", help="Modelo de Suno (chirp-v4, chirp-v5)")
def generate(prompt, model):
    """Genera música usando Suno AI."""
    console.print(f"[bold blue]CORTEX[/bold blue] 🎵 Generando: {prompt} [{model}]")
    try:
        tracks = asyncio.run(suno_generate(prompt=prompt, model=model))
        for t in tracks:
            console.print(f"  - [green]ID:[/green] {t.song_id} | [cyan]{t.audio_url}[/cyan]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@suno_cmds.command("detective")
@click.argument("song_id")
def detective(song_id):
    """Ejecuta el motor forense 'Detective Inverso' sobre un ID de Suno."""
    console.print(
        f"[bold magenta]DETECTIVE INVERSO[/bold magenta] 🔍 Analizando meta de {song_id}..."
    )
    try:
        meta = asyncio.run(suno_detective_inverso(song_id))
        console.print_json(data=meta)
    except Exception as e:
        console.print(f"[red]Error forense:[/red] {e}")


@suno_cmds.command("sync")
def sync():
    """Sincroniza endpoints usando Autodidact-Ω (Cognitive Ingestion)."""
    from cortex.gateway.adapters.suno_adapter import SunoDetectiveInverso

    console.print("[bold yellow]AUTODIDACT[/bold yellow] 🧠 Buscando actualizaciones de API...")
    det = SunoDetectiveInverso()
    asyncio.run(det.trigger_self_repair("manual_request_via_cli"))
    console.print("[green]Proceso de ingesta cognitiva iniciado.[/green]")
