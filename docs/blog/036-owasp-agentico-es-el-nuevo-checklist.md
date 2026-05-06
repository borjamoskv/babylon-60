---
title: "OWASP Agéntico es el Nuevo Checklist"
date: 2026-05-06
author: CORTEX Research Lab
tags: [owasp, seguridad, agentes-ia, mcp, actualidad]
description: "Prompt injection sigue importando, pero los riesgos actuales de agentes pasan también por herramientas, memoria, skills, scopes y supply chain."
slug: owasp-agentico-es-el-nuevo-checklist
---

# OWASP Agéntico es el Nuevo Checklist

El viejo checklist de seguridad para LLMs ya no alcanza cuando el modelo puede
usar herramientas, escribir memoria y ejecutar flujos multi-step.

Prompt injection sigue siendo central, pero el riesgo se movió hacia el sistema
completo.

## Las nuevas zonas calientes

En agentes, conviene revisar:

- tool misuse;
- excessive agency;
- memory poisoning;
- context spoofing;
- skills no auditadas;
- supply chain de servidores MCP;
- output handling inseguro;
- consumo no acotado;
- permisos demasiado amplios.

La vulnerabilidad no siempre está en el modelo. Puede estar en una skill, en una
descripción de herramienta o en una memoria que acepta cualquier cosa.

## El checklist mínimo

Antes de activar un agente con herramientas:

1. enumera herramientas;
2. define scopes;
3. limita operaciones destructivas;
4. valida outputs;
5. revisa memoria persistente;
6. bloquea secretos;
7. registra trazas;
8. prueba prompt injection indirecta.

No es glamour. Es higiene.

## La tesis

La seguridad agéntica no cabe en un prompt del sistema. Necesita controles por
capa.

OWASP está señalando justo eso: el ataque moderno no persuade solo al modelo;
explota el ecosistema alrededor.

## Fuentes consultadas

- [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications)
- [OWASP Agentic Skills Top 10](https://owasp.org/www-project-agentic-skills-top-10/)
- [OWASP MCP Top 10](https://owasp.org/www-project-mcp-top-10/)
