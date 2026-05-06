---
title: "Los Guardrails no son una Muralla"
date: 2026-05-06
author: CORTEX Research Lab
tags: [guardrails, seguridad, openai, agentes-ia, api]
description: "Los guardrails ayudan, pero no cubren automáticamente todos los caminos de una aplicación agéntica. Hay que diseñar límites por superficie."
slug: guardrails-no-son-una-muralla
---

# Los Guardrails no son una Muralla

La palabra "guardrail" suena tranquilizadora. Parece una barandilla firme entre
el agente y el desastre.

En realidad, un guardrail suele ser una capa dentro de un flujo concreto. Y los
agentes modernos tienen muchos flujos.

## La trampa mental

El error es pensar:

> Hemos añadido guardrails. Estamos cubiertos.

No necesariamente. Hay herramientas hospedadas, handoffs, ejecución local,
llamadas externas y rutas de integración que pueden no pasar por el mismo pipeline.

La defensa debe preguntarse por superficie:

- input del usuario;
- output del modelo;
- tool calls;
- handoffs;
- herramientas hospedadas;
- ejecución local;
- memoria;
- logs;
- persistencia.

## Un guardrail por intención

Un filtro de contenido no protege un write path. Un validador de JSON no evita
exfiltración. Un check de PII no demuestra que el agente tenga permiso para
modificar un repo.

Cada guardrail debe declarar:

```text
que cubre
que no cubre
donde se ejecuta
que evidencia deja
que pasa al fallar
```

Si no falla cerrado, es más aviso que control.

## La tesis

Los guardrails son útiles cuando se tratan como contratos específicos, no como
amuletos.

La pregunta correcta no es "¿tenemos guardrails?". Es:

> ¿esta acción concreta pasa por el guardrail correcto antes de tocar estado?

## Fuentes consultadas

- [OpenAI Agents SDK guardrails documentation](https://openai.github.io/openai-agents-python/guardrails/)
- [OpenAI Agents SDK overview](https://platform.openai.com/docs/guides/agents-sdk/)
