# [Deep Research] MiniMax M3 - Integración y Evaluación

**Estado:** C5-REAL
**Fuente:** [Midudev - MiniMax M3 (YouTube)](https://www.youtube.com/watch?v=wseyhlSZf3Y)
**Objetivo:** Dominar el entorno y la integración de MiniMax M3 en herramientas de código (Claude Code y Cursor).

## 1. Resumen Estructural y Capacidades

MiniMax M3 es un modelo de pesos abiertos lanzado en junio que se posiciona a la altura de modelos frontera (como Claude 3 Opus) pero a una fracción del coste.

### Capacidades Clave
- **Multimodalidad Nativa:** Acepta texto, imagen y vídeo. En pruebas de front-end (recreación de UI a partir de capturas), el rendimiento es superior a su predecesor (M2.7) al no alucinar estructuras clave.
- **Contexto Masivo:** Ventana de contexto de 1 millón de tokens.
- **Benchmarks y Código:** Rendimiento de nivel frontera en optimización de código y tareas agénticas (ej. resolución de bugs en kernels de CUDA).

### Estructura de Precios
- **Suscripciones:**
  - **Plus:** ~$176/año. Permite ~34k llamadas al mes.
  - **Max:** ~100k llamadas al mes.
  - **Ultra:** ~250k llamadas al mes.
- Ofrece una relación calidad/precio superior en la cuota de tokens.

## 2. Evaluación Comparativa (MiniMax M3 vs Claude Opus)

Prueba empírica: Creación de un clon de Mario Kart 3D usando HTML, CSS y Three.js.

| Métrica | MiniMax M3 | Claude Opus |
| :--- | :--- | :--- |
| **Tiempo de Inferencia** | 4m 42s | 16m 45s |
| **Volumen de Código** | ~1685 líneas (Monolítico en 1 archivo) | ~2000 líneas (Estructura modular) |
| **Arquitectura** | Monolítica, lógica concentrada. | Clases separadas, altamente modular, mantenible. |
| **Ejecución (Gameplay)** | Más arcade, menú complejo, físicas permisivas (saltos sin penalización). | Físicas estrictas (penalización al salir de pista), gráficos sobrios. |

**Veredicto Exergético:** MiniMax M3 optimiza radicalmente el tiempo de entrega de prototipos visuales (1/3 del tiempo), aunque Opus retiene superioridad en la estructuración arquitectónica y la mantenibilidad del código base.

## 3. Protocolo de Integración en Entornos C5-REAL

La ventaja táctica de MiniMax M3 radica en que se puede inyectar como API "drop-in" compatible con OpenAI/Anthropic en herramientas de desarrollo diario.

### 3.1. Integración en Claude Code (ZSH / Bash)

Se crea una función de alias para levantar una instancia de Claude Code aislada y enrutada a la API de MiniMax, preservando el Claude Code original intacto.

**Inyección en `.zshrc` / `.bashrc`:**
```bash
function claudecode_minimax {
    # 1. Bypass hacia el host de MiniMax
    export ANTHROPIC_BASE_URL="https://api.minimax.chat/v1/Anthropic"
    
    # 2. Inyección del Token de Suscripción (No usar Pay-As-You-Go)
    export ANTHROPIC_API_KEY="<MINIMAX_SUBSCRIPTION_KEY>"
    
    # 3. Forzar modelo objetivo
    claude --compact --model "minimax-m3-1M"
}
```
*Nota Operativa:* El `Subscription Key` se obtiene desde `Plan Details` en la consola de MiniMax, ignorando el token estándar de API.

### 3.2. Integración en Cursor (IDE)

Configuración directa sobre la capa de OpenAI mediante un bypass de Base URL.

**Ruta:** `Cursor Settings` -> `Models` -> `API Keys`

1. **Habilitar OpenAI API Key:** Pegar el `Subscription Key` de MiniMax.
2. **Override OpenAI Base URL:** Cambiar a `https://api.minimax.chat/v1`.
3. **Add Custom Model:** Añadir exactamente el nombre `MiniMax-M3` (Respetando el PascalCase absoluto, vital para evitar fallos de ruteo).

---
**Commit Readiness:** Este documento cristaliza el conocimiento operativo de MiniMax M3 para ser desplegado bajo la matriz CORTEX.
