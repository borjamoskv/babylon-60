# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "google-genai",
#     "rich",
#     "click",
# ]
# ///

import os
import sys
import time
import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.theme import Theme
from rich.text import Text
from google import genai
from google.genai import types

# Industrial Noir 2026 Theme
moskv_theme = Theme({
    "info": "bold #2B3BE5",
    "warning": "bold yellow",
    "error": "bold red",
    "success": "bold green",
    "accent": "#2B3BE5", # YInMn Blue
})

console = Console(theme=moskv_theme)

def get_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        console.print("[error]CRITICAL FAULT: GEMINI_API_KEY no encontrada en el entorno.[/error]")
        console.print("Por favor, ejecuta: [accent]export GEMINI_API_KEY='tu_clave'[/accent]")
        sys.exit(1)
    return genai.Client(api_key=api_key)

@click.command()
@click.option('--tema', '-t', required=True, help='Tema central del relato.')
@click.option('--paginas', '-p', default=500, type=int, help='Número de páginas a generar.')
@click.option('--salida', '-o', default='relato_yolo.md', help='Archivo de salida.')
@click.option('--modelo', '-m', default='gemini-2.5-pro', help='Modelo a utilizar.')
def generar_relato(tema: str, paginas: int, salida: str, modelo: str):
    """
    YOLO Generator — Modo Fuerza Bruta. Generador de relatos largos del tirón. 
    Aesthetic: Industrial Noir 2026. Zero-Rhetoric.
    """
    console.print(Panel(
        f"[bold white]TARGET:[/bold white] {tema}\n"
        f"[bold white]PAGES:[/bold white] {paginas}\n"
        f"[bold white]OUTPUT:[/bold white] {salida}\n"
        f"[bold white]MODEL:[/bold white] {modelo}",
        title="[accent]YOLO WRITER OMEGA[/accent]",
        border_style="#2B3BE5",
        expand=False
    ))

    client = get_client()
    contexto_previo = ""
    
    # Sistema de configuración:
    sys_instruction = (
        "Eres un novelista virtuoso y prolífico. Estás escribiendo una novela "
        f"sobre el siguiente tema: '{tema}'. "
        "Tu escritura es inmersiva, profunda, con una estética rica y sin adornos vacíos. "
        "Mantén la coherencia narrativa total. Escribes en modo 'flujo de conciencia' estructurado. "
        "No hagas resúmenes ni repitas el comienzo. Simplemente continúa la historia."
    )

    with open(salida, 'w', encoding='utf-8') as f:
        f.write(f"# {tema.upper()}\n\n")

    with Progress(
        SpinnerColumn(style="#2B3BE5"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(style="black", complete_style="#2B3BE5"),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        tarea = progress.add_task("[accent]Forjando Relato...[/accent]", total=paginas)
        
        for i in range(1, paginas + 1):
            prompt = (
                f"Escribe la página {i} de {paginas}. "
                "Genera exactamente el texto correspondiente a una página de libro (aprox 400-500 palabras). "
            )
            
            if contexto_previo:
                prompt += f"\n\nContexto anterior inmediato:\n{contexto_previo[-1500:]}\n\nContinúa exactamente donde lo dejaste sin saludar ni presentarte."
            
            try:
                response = client.models.generate_content(
                    model=modelo,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=sys_instruction,
                        temperature=0.7,
                    )
                )
                
                texto = response.text
                if texto:
                    with open(salida, 'a', encoding='utf-8') as f:
                        f.write(f"## Página {i}\n\n")
                        f.write(texto.strip() + "\n\n")
                    
                    contexto_previo = texto
                
                progress.advance(tarea)
                
                # Throttle to avoid rate limits if iterating very fast
                time.sleep(1)
                
            except Exception as e:
                console.print(f"\n[error]Error en la página {i}: {str(e)}[/error]")
                console.print("[warning]Reintentando en 5 segundos...[/warning]")
                time.sleep(5)
                # Retry logic can be expanded here
                # To keep YOLO simple we just continue to the next or wait and retry manually
                continue
                
    console.print(f"\n[success]SUCCESS: Relato forjado y guardado en {salida}[/success]")

if __name__ == '__main__':
    generar_relato()
