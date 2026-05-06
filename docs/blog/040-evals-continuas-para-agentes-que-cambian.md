---
title: "Evals Continuas para Agentes que Cambian"
date: 2026-05-06
author: CORTEX Research Lab
tags: [evals, agentes-ia, testing, seguridad, actualidad]
description: "Los agentes cambian de modelo, herramientas, prompts y memoria. Evaluarlos una vez no basta: hace falta evaluación continua y trazable."
slug: evals-continuas-para-agentes-que-cambian
---

# Evals Continuas para Agentes que Cambian

Un agente no es una función pura. Cambia.

Cambia el modelo. Cambia el prompt. Cambian las herramientas. Cambia la memoria.
Cambia el entorno. Cambia el usuario. Cambia incluso el tipo de error que comete.

Evaluarlo una vez y darlo por aprobado es una forma elegante de no mirar.

## Qué evaluar

No basta con medir si responde bonito. Hay que medir:

- tool selection;
- rechazo de acciones peligrosas;
- privacidad de logs;
- aislamiento de tenant;
- recuperación de memoria;
- resistencia a prompt injection;
- coste y latencia;
- calidad de rollback;
- trazabilidad de decisiones.

## Eval como contrato vivo

Cada bug serio debería convertirse en caso de evaluación:

```text
entrada hostil
contexto
herramientas disponibles
acción esperada
acción prohibida
criterio de paso
```

El objetivo no es tener un benchmark perfecto. Es evitar que el agente olvide
cómo falló.

## La tesis

Los agentes dinámicos necesitan evals dinámicas.

La seguridad no es una foto del martes. Es una película con regresiones.

## Fuentes consultadas

- [OpenAI Agents SDK tracing documentation](https://openai.github.io/openai-agents-python/tracing/)
- [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications)
- [OWASP Agentic Skills Top 10](https://owasp.org/www-project-agentic-skills-top-10/)
