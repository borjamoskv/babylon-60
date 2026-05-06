---
title: "APIs para Agentes: Intención, no Solo Token"
date: 2026-05-06
author: CORTEX Research Lab
tags: [api, seguridad, autorizacion, agentes-ia, actualidad]
description: "Las APIs diseñadas para agentes no deberían autorizar solo por token. Deben conservar intención, delegación, scope y evidencia de la cadena de acción."
slug: api-para-agentes-intencion-no-solo-token
---

# APIs para Agentes: Intención, no Solo Token

Un token dice que alguien puede llamar a una API. No siempre dice por qué.

Con agentes, el "por qué" importa mucho. El mismo endpoint puede ser seguro si
se invoca para leer un resumen y peligroso si forma parte de una cadena que
termina modificando estado.

## El contrato nuevo

Una API preparada para agentes debería recibir o derivar:

- identidad del usuario delegante;
- identidad del agente;
- intención declarada;
- scope de recurso;
- sensibilidad del dato;
- política de acción;
- trace id;
- nivel de aprobación.

Esto no sustituye OAuth ni permisos clásicos. Los complementa.

## Ejemplo mental

```text
POST /repo/change
agent: codex-worker-17
delegator: user-42
intent: fix-test-failure
scope: tests/
approval: write-approved
trace: tr_...
```

Esa petición es más auditable que una llamada con bearer token y silencio.

## Rechazos útiles

Una API de agentes debe rechazar con precisión:

- scope insuficiente;
- intención incompatible;
- herramienta no autorizada;
- falta de aprobación humana;
- riesgo alto sin verificación;
- tenant no coincidente.

Los errores genéricos hacen que el agente improvise. Los errores precisos lo
mantienen dentro del contrato.

## La tesis

Las APIs para agentes no pueden asumir que identidad, intención y permiso son la
misma cosa.

El token abre la puerta. La intención decide qué habitación puede tocar.

## Fuentes consultadas

- [NIST NCCoE concept paper on AI agent identity and authorization](https://csrc.nist.gov/pubs/other/2026/02/05/accelerating-the-adoption-of-software-and-ai-agent/ipd)
- [MCP Authorization specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization)
