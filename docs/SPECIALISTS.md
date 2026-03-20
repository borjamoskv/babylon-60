# Specialists — Schema y Convención

> Documentación del fichero `resources/prompts/specialists.json`.
> Actualizado: 2026-03-20.

## Propósito

`specialists.json` define los **perfiles de especialista** que el sistema de routing
LLM usa para seleccionar el modo cognitivo y persona de respuesta adecuados al
contexto de cada request. Es la capa de prompt management versionado del motor.

## Schema

```json
{
  "specialists": [
    {
      "id": "string (PascalCase, único)",
      "name": "string (display name)",
      "domain": "string (kebab-case)",
      "persona": "string (descripción del rol y comportamiento)",
      "axioms": ["string (referencia a Ω-laws del GEMINI.md)"],
      "triggers": ["string (keywords que activan este specialist)"]
    }
  ]
}
```

### Campos

| Campo | Tipo | Requerido | Descripción |
|:------|:-----|:----------|:------------|
| `id` | `string` | ✅ | Identificador único. PascalCase. Referenciado por el router. |
| `name` | `string` | ✅ | Nombre display. Puede coincidir con `id`. |
| `domain` | `string` | ✅ | Dominio semántico en kebab-case. Usado para indexación. |
| `persona` | `string` | ✅ | Descripción del rol inyectada como system prompt. Debe ser concisa y directiva. |
| `axioms` | `string[]` | ✅ | Leyes Ω del GEMINI.md que este specialist aplica. Al menos 1. |
| `triggers` | `string[]` | ✅ | Keywords que activan el specialist en el router. Case-insensitive en runtime. Al menos 2. |

## Specialists activos (v1)

| ID | Dominio | Axioms | Triggers clave |
|:---|:--------|:-------|:---------------|
| `ArchitectPrime` | system-design | Ω₀, Ω₄, Ω₆ | refactor, architecture, design-pattern |
| `CodeNinja` | implementation | Ω₀, Ω₂, Ω₃ | implement, fix, clean, boilerplate |
| `SecurityWarden` | security | Ω₃, Ω₅ | security, auth, secret, eval, leak |
| `PerformanceGhost` | performance | Ω₂, Ω₆ | slow, optimize, latency, memory, perf |
| `AestheticShiva` | ui-ux | Ω₄, Ω₀ | ui, css, layout, design, animation |
| `DataAlchemist` | data-ml | Ω₁, Ω₂ | data, sql, graph, ghost-mapping |
| `OpsPhantom` | devops-infra | Ω₃, Ω₅ | deployment, infra, modal, cloud |
| `LoreKeeper` | documentation | Ω₀, Ω₄ | doc, walkthrough, persist, readme |

## Cómo extender

Para añadir un nuevo specialist:

1. Añadir entrada al array `specialists` en `resources/prompts/specialists.json`.
2. El `id` debe ser único — el router indexa por `id`, no por `name`.
3. Los `triggers` deben ser mutuamente excluyentes con los de otros specialists
   cuando sea posible. Triggers solapados se resuelven por orden de array (first-match).
4. Los `axioms` deben referenciar Ω-laws existentes en `GEMINI.md`.
5. Commit con mensaje: `feat(prompts): add specialist <ID>`.

## Consumidores

El fichero es leído por el sistema de routing LLM. Consult `cortex/llm/router.py`
para ver cómo se carga y aplica en runtime.

> **Nota:** Si `cortex/llm/router.py` no implementa aún la lectura de este fichero,
> ese es el bloqueante de integración. Ver Gap 2 del audit de experimental.
