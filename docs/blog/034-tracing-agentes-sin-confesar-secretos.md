---
title: "Tracing de Agentes sin Confesar Secretos"
date: 2026-05-06
author: CORTEX Research Lab
tags: [tracing, observabilidad, openai, privacidad, agentes-ia]
description: "El tracing de agentes ya es imprescindible, pero una traza completa también puede ser una copia sensible del sistema si no se controla."
slug: tracing-agentes-sin-confesar-secretos
---

# Tracing de Agentes sin Confesar Secretos

Los agentes necesitan trazas. Sin ellas, nadie sabe por qué una respuesta terminó
en una herramienta, una escritura o una decisión.

Pero una traza completa puede contener generaciones, tool calls, handoffs,
guardrails, eventos custom y fragmentos sensibles. Eso la convierte en evidencia
y en riesgo.

## Qué debe explicar una traza

Una buena traza responde:

- qué agente actuó;
- qué modelo se usó;
- qué herramienta llamó;
- qué guardrail bloqueó o permitió;
- qué handoff ocurrió;
- qué latencia y coste hubo;
- qué evento se correlaciona con el usuario o tenant.

No siempre necesita conservar payloads completos.

## El punto sensible

Si la traza incluye datos sensibles, debe tratarse como almacenamiento sensible:

1. retención limitada;
2. redacción;
3. tenant scope;
4. acceso restringido;
5. opción de desactivar campos sensibles;
6. separación entre métricas y contenido.

Observabilidad sin privacidad es una fuga con gráficos.

## Para CORTEX

El tracing debería alimentar memoria solo después de una selección explícita. No
todo evento operacional merece convertirse en recuerdo persistente.

```text
trace event -> classify -> redact -> decide retention -> persist if useful
```

## La tesis

Trazar agentes es obligatorio para operar con rigor. Pero la traza no debe
convertirse en confesionario.

Mide el recorrido. No desnudes todo el contenido.

## Fuentes consultadas

- [OpenAI Agents SDK tracing documentation](https://openai.github.io/openai-agents-python/tracing/)
- [OpenAI Agents SDK overview](https://platform.openai.com/docs/guides/agents-sdk/)
