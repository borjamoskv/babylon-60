"""
CLI de Mac Maestro — Automatización soberana de escritorio macOS.

Comandos para control de teclado, mouse, ventanas y accesibilidad
desde la terminal.
"""

from __future__ import annotations

import asyncio
from typing import Optional

import click
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from cortex.cli.common import console, get_engine
from cortex.extensions.ui_control.maestro import MaestroUI
from cortex.extensions.ui_control.models import AppTarget


@click.group(name="maestro")
def maestro():
    """MAC-Ω: Automatización soberana de escritorio (AppleScript/Native)."""
    pass


# ─── Inspección ─────────────────────────────────────────────────


@maestro.command("inspect")
@click.argument("app_name")
@click.option("--depth", default=5, help="Profundidad máxima del árbol AX")
def inspect_cmd(app_name: str, depth: int):
    """Inspecciona el árbol de accesibilidad de una app."""
    engine = get_engine()
    m = MaestroUI(engine=engine)

    if not m.check_permissions():
        console.print(
            "[red]✘ Sin permisos de Accesibilidad. Revisar Preferencias del Sistema.[/red]"
        )
        return

    tree = m.dump_tree(app_name, max_depth=depth)
    if not tree:
        console.print(f"[yellow]⚠ No se encontraron elementos para '{app_name}'[/yellow]")
        return

    console.print(f"[bold]Árbol AX de {app_name}[/bold] ({len(tree)} elementos):\n")
    for el in tree:
        indent = "  " * (el.depth or 0)
        role = el.role or "?"
        title = f' "{el.title}"' if el.title else ""
        ident = f" [{el.identifier}]" if el.identifier else ""
        val = f" = {el.value}" if el.value else ""
        console.print(f"{indent}{role}{title}{ident}{val}")


@maestro.command("find")
@click.argument("app_name")
@click.argument("query")
@click.option("--by", default="title", type=click.Choice(["title", "role", "id"]))
def find_cmd(app_name: str, query: str, by: str):
    """Buscar elementos AX por título, rol o identificador."""
    engine = get_engine()
    m = MaestroUI(engine=engine)

    if by == "title":
        el = m.find_element_by_title(app_name, query)
        results = [el] if el else []
    elif by == "role":
        results = m.find_elements_by_role(app_name, query)
    else:
        el = m.find_element(app_name, query)
        results = [el] if el else []

    if not results:
        console.print(f"[yellow]⚠ Sin resultados para '{query}' ({by})[/yellow]")
        return

    console.print(f"[green]✔ {len(results)} elemento(s) encontrado(s):[/green]")
    for el in results:
        console.print(f"  {el.role}: {el.title or el.identifier or '(sin nombre)'}")


# ─── Teclado ────────────────────────────────────────────────────


@maestro.command("hotkey")
@click.argument("key")
@click.argument("modifiers", nargs=-1)
@click.option("--app", default=None, help="App objetivo")
def hotkey_cmd(key: str, modifiers: tuple[str, ...], app: Optional[str]):
    """
    Envía un atajo de teclado.

    Ejemplo: cortex maestro hotkey c command       → Cmd+C
    Ejemplo: cortex maestro hotkey s command shift  → Cmd+Shift+S
    """

    async def _run():
        m = MaestroUI(engine=get_engine())
        target = AppTarget(name=app) if app else None
        res = await m.hotkey(key, *modifiers, target=target)
        if res.success:
            mod_str = "+".join(list(modifiers) + [key])
            console.print(f"[green]✔ Enviado: {mod_str}[/green]")
        else:
            console.print(f"[red]✘ Error: {res.error}[/red]")

    asyncio.run(_run())


@maestro.command("type")
@click.argument("text")
@click.option("--app", default=None, help="App objetivo")
def type_cmd(text: str, app: Optional[str]):
    """Escribe texto en la app activa (clipboard para cadenas largas)."""

    async def _run():
        m = MaestroUI(engine=get_engine())
        target = AppTarget(name=app) if app else None
        console.print(f"Escribiendo {len(text)} caracteres...")
        res = await m.type_text(text, target=target)
        if res.success:
            console.print("[green]✔ Texto inyectado.[/green]")
        else:
            console.print(f"[red]✘ Error: {res.error}[/red]")

    asyncio.run(_run())


# ─── Ratón ──────────────────────────────────────────────────────


@maestro.command("click-at")
@click.argument("x", type=int)
@click.argument("y", type=int)
@click.option("--button", default="left", help="left / right")
def click_at_cmd(x: int, y: int, button: str):
    """Click en coordenadas de pantalla."""
    m = MaestroUI(engine=get_engine())
    res = m.click(x, y, button)
    if res.success:
        console.print(f"[green]✔ Click en ({x}, {y})[/green]")
    else:
        console.print(f"[red]✘ Error: {res.error}[/red]")


@maestro.command("double-click")
@click.argument("x", type=int)
@click.argument("y", type=int)
def double_click_cmd(x: int, y: int):
    """Doble click en coordenadas de pantalla."""
    m = MaestroUI(engine=get_engine())
    res = m.double_click(x, y)
    if res.success:
        console.print(f"[green]✔ Doble click en ({x}, {y})[/green]")
    else:
        console.print(f"[red]✘ Error: {res.error}[/red]")


@maestro.command("drag")
@click.argument("from_x", type=int)
@click.argument("from_y", type=int)
@click.argument("to_x", type=int)
@click.argument("to_y", type=int)
@click.option("--duration", default=0.5, help="Duración del arrastre en segundos")
def drag_cmd(from_x: int, from_y: int, to_x: int, to_y: int, duration: float):
    """Drag-and-drop de un punto a otro."""
    m = MaestroUI(engine=get_engine())
    res = m.drag(from_x, from_y, to_x, to_y, duration=duration)
    if res.success:
        console.print(f"[green]✔ Drag ({from_x},{from_y}) → ({to_x},{to_y})[/green]")
    else:
        console.print(f"[red]✘ Error: {res.error}[/red]")


@maestro.command("scroll")
@click.argument("clicks", type=int)
def scroll_cmd(clicks: int):
    """Scroll de rueda. Positivo=arriba, negativo=abajo."""
    m = MaestroUI(engine=get_engine())
    res = m.scroll(clicks)
    if res.success:
        console.print(f"[green]✔ Scroll {clicks} líneas[/green]")
    else:
        console.print(f"[red]✘ Error: {res.error}[/red]")


# ─── Ventanas ───────────────────────────────────────────────────


@maestro.command("list-windows")
@click.argument("app_name")
def list_windows_cmd(app_name: str):
    """Lista todas las ventanas de una aplicación."""

    async def _run():
        m = MaestroUI(engine=get_engine())
        windows = await m.list_windows(app_name)
        if not windows:
            console.print(f"[yellow]⚠ Sin ventanas para '{app_name}'[/yellow]")
            return
        console.print(f"[bold]{app_name}[/bold] — {len(windows)} ventana(s):")
        for w in windows:
            state = ""
            if w.minimized:
                state = " [minimizada]"
            elif w.fullscreen:
                state = " [pantalla completa]"
            console.print(f"  • '{w.title}' — {w.width}×{w.height} @ ({w.x},{w.y}){state}")

    asyncio.run(_run())


@maestro.command("move")
@click.argument("app_name")
@click.argument("x", type=int)
@click.argument("y", type=int)
def move_cmd(app_name: str, x: int, y: int):
    """Mueve la ventana principal de una app."""

    async def _run():
        m = MaestroUI(engine=get_engine())
        target = AppTarget(name=app_name)
        res = await m.move_window(target, x, y)
        if res.success:
            console.print(f"[green]✔ Ventana movida a ({x}, {y})[/green]")
        else:
            console.print(f"[red]✘ Error: {res.error}[/red]")

    asyncio.run(_run())


@maestro.command("resize")
@click.argument("app_name")
@click.argument("width", type=int)
@click.argument("height", type=int)
def resize_cmd(app_name: str, width: int, height: int):
    """Redimensiona la ventana principal de una app."""

    async def _run():
        m = MaestroUI(engine=get_engine())
        target = AppTarget(name=app_name)
        res = await m.resize_window(target, width, height)
        if res.success:
            console.print(f"[green]✔ Ventana redimensionada a {width}×{height}[/green]")
        else:
            console.print(f"[red]✘ Error: {res.error}[/red]")

    asyncio.run(_run())


@maestro.command("minimize")
@click.argument("app_name")
def minimize_cmd(app_name: str):
    """Minimiza la ventana principal de una app."""

    async def _run():
        m = MaestroUI(engine=get_engine())
        res = await m.minimize_window(AppTarget(name=app_name))
        if res.success:
            console.print(f"[green]✔ {app_name} minimizado[/green]")
        else:
            console.print(f"[red]✘ Error: {res.error}[/red]")

    asyncio.run(_run())


@maestro.command("fullscreen")
@click.argument("app_name")
def fullscreen_cmd(app_name: str):
    """Alterna pantalla completa para una app."""

    async def _run():
        m = MaestroUI(engine=get_engine())
        res = await m.fullscreen_window(AppTarget(name=app_name))
        if res.success:
            console.print(f"[green]✔ {app_name} pantalla completa alternada[/green]")
        else:
            console.print(f"[red]✘ Error: {res.error}[/red]")

    asyncio.run(_run())


# ─── Captura ────────────────────────────────────────────────────


@maestro.command("capture")
@click.option("--output", "-o", default=None, help="Ruta de salida para la captura")
def capture_cmd(output: Optional[str]):
    """Captura de pantalla del display principal."""

    async def _run():
        m = MaestroUI(engine=get_engine())
        path = await m.screenshot(output)
        if path:
            console.print(f"[green]✔ Captura guardada en: {path}[/green]")
        else:
            console.print("[red]✘ Fallo al capturar pantalla[/red]")

    asyncio.run(_run())


# ─── AppleScript ────────────────────────────────────────────────


@maestro.command("run")
@click.argument("instruction", nargs=-1)
def run_cmd(instruction: tuple[str, ...]):
    """Ejecuta instrucción NL con Mac Maestro v2."""
    text = " ".join(instruction)

    async def _run():
        from cortex.extensions.agents.mac_maestro import MacMaestroAgent

        agent = MacMaestroAgent()
        
        header = Panel(
            f"[bold blue]MAC-MAESTRO Ω[/bold blue] [dim]v2.0[/dim]\n"
            f"[white]Instruction:[/white] [cyan]{text}[/cyan]",
            border_style="blue",
            padding=(1, 2)
        )
        console.print(header)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task(description="Generating Execution Plan...", total=None)
            res = await agent.execute(text)

        if not res:
            console.print("[red]✘ Agent returned no result.[/red]")
            return

        mode = res.get("mode", "sdk")
        run_id = res.get("run_id", "n/a")
        explanation = res.get("explanation", "No explanation provided.")

        if res.get("success"):
            console.print(f"\n[bold green]✔ STRATEGY:[/bold green] [white]{explanation}[/white]")
            
            table = Table(box=None, padding=(0, 2))
            table.add_column("State", width=3)
            table.add_column("Action", style="cyan")
            table.add_column("Vector", style="dim")

            ar_list = res.get("action_results", [])
            plan = res.get("plan", {})
            actions_plan = plan.get("actions", [])

            for i, ar in enumerate(ar_list):
                nm = "Action"
                vec = "?"
                if i < len(actions_plan):
                    nm = actions_plan[i].get("name", nm)
                    vec = actions_plan[i].get("vector", vec)
                
                ok = False
                if isinstance(ar, dict):
                    ok = ar.get("success", False)
                elif isinstance(ar, bool):
                    ok = ar

                mark = "[green]✔[/green]" if ok else "[red]✘[/red]"
                table.add_row(mark, nm, f"Vector {vec}")

            console.print(table)
            console.print(f"\n[dim]Runtime: {mode} | ID: {run_id}[/dim]")
        else:
            err = res.get("error") or res.get("stderr")
            console.print("\n[bold red]✘ FAILURE[/bold red]")
            console.print(f"[red]{err}[/red]")
            if explanation:
                console.print(f"[dim]{explanation}[/dim]")

    asyncio.run(_run())


# ─── Chain (multi-instruction) ──────────────────────────────


@maestro.command("chain")
@click.argument("instructions", nargs=-1)
@click.option(
    "--separator", "-s", default="&&",
    help="Delimitador entre instrucciones.",
)
def chain_cmd(instructions: tuple[str, ...], separator: str):
    """Encadena múltiples instrucciones NL (&&-separadas)."""
    raw = " ".join(instructions)
    steps = [s.strip() for s in raw.split(separator) if s.strip()]

    if not steps:
        console.print("[red]No se proporcionaron pasos.[/red]")
        return

    async def _run():
        from cortex.extensions.agents.mac_maestro import (
            MacMaestroAgent,
        )
        agent = MacMaestroAgent()
        total = len(steps)
        ok_count = 0

        for i, step in enumerate(steps, 1):
            console.print(
                f"\n[bold]Paso {i}/{total}:[/bold] {step}",
            )
            res = await agent.execute(step)
            if res.get("success"):
                console.print(
                    f"  [green]✔ {res.get('explanation')}[/green]",
                )
                ok_count += 1
            else:
                err = res.get("error") or res.get("stderr")
                console.print(f"  [red]✘ {err}[/red]")

        console.print(
            f"\n[bold]Resultado: {ok_count}/{total} OK[/bold]",
        )

    asyncio.run(_run())


# ─── Wait For Element ────────────────────────────────────────


@maestro.command("wait-for")
@click.argument("app_name")
@click.argument("identifier")
@click.option(
    "--timeout", "-t", default=10.0,
    help="Timeout en segundos.",
)
def wait_for_cmd(app_name: str, identifier: str, timeout: float):
    """Espera a que un elemento AX aparezca en una app."""

    async def _run():
        m = MaestroUI(engine=get_engine())
        console.print(
            f"Esperando '{identifier}' en {app_name}"
            f" ({timeout}s)...",
        )
        el = await m.wait_for_element(
            app_name, identifier, timeout,
        )
        if el:
            console.print(
                f"[green]✔ Elemento encontrado: "
                f"{el.role} '{el.title}'[/green]",
            )
        else:
            console.print(
                f"[red]✘ Timeout: elemento "
                f"'{identifier}' no encontrado[/red]",
            )

    asyncio.run(_run())

