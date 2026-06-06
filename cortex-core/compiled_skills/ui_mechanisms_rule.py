# [C5-REAL] Exergy-Maximized
"""
CORTEX JIT Compiled Skill: UI-Mechanisms-Rule
Description: C5-REAL UI context injection rules and commands.
"""
import json
import logging

class UiMechanismsRuleSkill:
    def __init__(self):
        self.name = "UI-Mechanisms-Rule"
        self.description = "C5-REAL UI context injection rules and commands."
        self.instructions = "# UI Mechanisms Rule\n\nCaracter\u00edstica: Inyecci\u00f3n de Contexto y Ejecuci\u00f3n de Comandos (Mecanismos de UI)\nNivel_Realidad: C5-REAL\nDescripci\u00f3n: Las im\u00e1genes muestran los mecanismos de la interfaz de chat para inyectar contexto de alta precisi\u00f3n e invocar subrutinas especializadas del agente.\n\n## Mecanismos:\n- **Disparador**: Men\u00fa \"Add Context (+)\" (Imagen 2)\n  **Prop\u00f3sito**: Inserci\u00f3n manual de contexto externo.\n  **Opciones**:\n    - *Media*: Inyecta im\u00e1genes/v\u00eddeo para inferencia multimodal.\n    - *Mentions*: Abre el men\u00fa `@` para seleccionar archivos o carpetas locales.\n    - *Actions*: Acciones r\u00e1pidas y herramientas del entorno.\n    - *Browser*: Adjunta el estado o la URL activa del navegador.\n\n- **Disparador**: Men\u00fa \"@\" (Menciones)\n  **Prop\u00f3sito**: Imposici\u00f3n estricta de l\u00edmites de contexto.\n  **Comportamiento**: Escribir `@` permite seleccionar archivos, carpetas o IDs de conversaciones previas. Esto fuerza la carga de estos elementos directamente en la ventana de memoria, erradicando alucinaciones sobre la arquitectura del proyecto.\n\n- **Disparador**: Men\u00fa \"/\" (Comandos Slash y Skills) (Imagen 3)\n  **Prop\u00f3sito**: Ejecuci\u00f3n determinista de flujos de trabajo.\n  **Capacidades**:\n    - *Herramientas MCP*: Invocaci\u00f3n directa de servidores Model Context Protocol (ej. `mcp:fetch:fetch`, `mcp:sqlite:mcp-demo`).\n    - *Rutinas Internas*: Activa bucles de ejecuci\u00f3n del agente como `/goal` (operaci\u00f3n continua hasta resoluci\u00f3n), `/schedule` (tareas recurrentes) o `/browser` (automatizaci\u00f3n web aut\u00f3noma).\n    - *Skills Nativas*: Invoca habilidades soberanas cargadas localmente en la configuraci\u00f3n del sistema (ej. `/AESTHETIC-OMEGA`).\n"

    def get_system_prompt(self):
        return self.instructions

    def execute(self, payload: dict) -> dict:
        """
        O(1) execution wrapper.
        In Cycle 1 (MCP), this will bind via API to Cortex Swarm.
        """
        logging.info(f"[{self.name}] Executing logic...")
        # A wrapper returning the prompt context for Frontier Models
        # or executing underlying local hooks if defined.
        return {
            "status": "success",
            "skill": self.name,
            "injected_knowledge_tokens": len(self.instructions.split()),
            "yield_impact": "O(1) Execution",
            "extracted_payload": payload
        }
