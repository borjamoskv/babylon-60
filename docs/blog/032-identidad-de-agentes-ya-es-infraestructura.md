---
title: "La Identidad de Agentes ya es Infraestructura"
date: 2026-05-06
author: CORTEX Research Lab
tags: [identidad, autorizacion, agentes-ia, nist, api]
description: "NIST ya está empujando el debate: los agentes necesitan identidad, autorización y trazabilidad propias, no permisos prestados de forma opaca."
slug: identidad-de-agentes-ya-es-infraestructura
---

# La Identidad de Agentes ya es Infraestructura

Durante años, la identidad en software significó humanos, servicios y máquinas.
Ahora hay un actor nuevo: agentes que actúan por delegación, encadenan herramientas
y toman decisiones entre sistemas.

Ese actor no encaja bien en permisos estáticos.

## El problema

Un agente puede empezar resumiendo un ticket y terminar llamando a una API,
leyendo un documento, generando un cambio y pidiendo deploy. Si toda esa cadena
usa una credencial plana, el sistema pierde intención.

No basta saber "quién autenticó". También hay que saber:

- en nombre de quién actúa el agente;
- qué objetivo estaba autorizado;
- qué herramientas participaron;
- qué datos tocó;
- qué parte fue decisión humana;
- qué parte fue inferencia autónoma.

## NIST lo está llevando a estándares

En febrero de 2026, NIST/NCCoE publicó un concepto sobre identidad y autorización
de software y agentes IA. La señal es clara: esto deja de ser una discusión de
producto y entra en infraestructura de seguridad.

La identidad de agente debe ser verificable, revocable y auditable.

## Diseño mínimo

Un sistema serio debería emitir un registro parecido a:

```text
actor: agent_id
delegator: user_id
intent: summarize_and_patch_issue
scope: repo/path
tools_used: search, read_file, apply_patch
approval: required_for_write
trace_id: ...
```

Eso no es burocracia. Es cómo reconstruyes responsabilidad cuando algo sale mal.

## La tesis

Los agentes no deberían vivir escondidos detrás de tokens humanos genéricos.

Necesitan identidad propia, permisos con intención y trazabilidad que sobreviva
a la cadena de herramientas.

## Fuentes consultadas

- [NIST NCCoE concept paper on software and AI agent identity and authorization](https://csrc.nist.gov/pubs/other/2026/02/05/accelerating-the-adoption-of-software-and-ai-agent/ipd)
- [NIST AI Agent Standards Initiative](https://www.nist.gov/node/1906621)
