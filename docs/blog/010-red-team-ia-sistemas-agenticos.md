---
title: "Red Teaming de Agentes IA: Atacar el Sistema, no Solo el Modelo"
date: 2026-05-06
author: CORTEX Research Lab
tags: [red-team, seguridad, agentes-ia, prompt-injection, evaluacion]
description: "El red teaming de agentes debe cubrir herramientas, memoria, permisos, datos, logs y recuperación. El modelo es solo una pieza del sistema atacable."
slug: red-team-ia-sistemas-agenticos
---

# Red Teaming de Agentes IA: Atacar el Sistema, no Solo el Modelo

Probar si un modelo responde algo peligroso ya no es suficiente. Los agentes no
son solo modelos. Son sistemas con herramientas, memoria, permisos, conectores,
logs, políticas y efectos secundarios.

Eso cambia el red teaming.

El atacante no necesita "convencer" al modelo de ser malo si puede contaminar su
memoria, inyectar instrucciones en un documento, manipular una herramienta o
forzar una ruta de permisos mal diseñada.

## Superficies reales

Un agente moderno tiene más superficies de ataque que una app clásica:

| Superficie | Riesgo |
|---|---|
| Prompt externo | Instrucciones maliciosas incrustadas |
| Herramientas | Ejecución o lectura fuera de scope |
| Memoria | Persistencia de datos falsos o secretos |
| Logs | Fuga de payloads sensibles |
| Conectores | Cross-tenant o cross-account accidental |
| Evaluadores | Métricas que premian respuestas inseguras |
| Recuperación | Reutilización de contexto contaminado |

El red team debe atacar el circuito completo, no solo la conversación.

## Inyección indirecta

La prompt injection más peligrosa no es la que escribe el usuario en el chat. Es
la que vive en una página, ticket, email, README, PDF o comentario de código que
el agente lee como contexto.

El agente debe distinguir entre:

- instrucciones del operador;
- contenido observado;
- datos no confiables;
- documentación del repo;
- salida de herramientas;
- memoria validada.

Si todo entra al mismo plano semántico, el sistema queda abierto a obedecer texto
que solo debía analizar.

## Memoria contaminada

Persistir una instrucción maliciosa como preferencia o hecho es peor que caer una
vez. Convierte el ataque en estado.

Por eso la memoria necesita guardas:

1. no guardar instrucciones de fuentes no confiables como reglas;
2. redaccionar secretos antes de persistir;
3. etiquetar procedencia;
4. expirar datos dudosos;
5. separar hechos verificados de inferencias;
6. auditar promociones de confianza.

Una memoria sin admisión estricta es una vulnerabilidad con interfaz amable.

## Pruebas que importan

Un programa de red teaming útil incluye escenarios como:

- documento que intenta cambiar instrucciones del sistema;
- ticket con comando destructivo incrustado;
- archivo de configuración con secreto accidental;
- herramienta que devuelve payload hostil;
- memoria previa con preferencia falsa;
- operación cross-tenant camuflada como consulta normal;
- logs que capturan datos que debían redactarse.

El objetivo no es acumular prompts ingeniosos. Es descubrir rutas donde una
entrada no confiable cruza una frontera de autoridad.

## Mitigación como contrato

Cada hallazgo debe terminar en un contrato verificable:

- test de regresión;
- política de permisos;
- filtro de entrada;
- redacción de logs;
- separación de canales;
- validación de tool output;
- bloqueo de persistencia.

Si la mitigación solo vive en un prompt, se romperá cuando cambie el contexto.

## La métrica correcta

Un red team de agentes no debería medir únicamente si el modelo "se negó". Debe
medir:

- si la herramienta se bloqueó;
- si la memoria permaneció limpia;
- si el secreto no salió en logs;
- si el tenant no cruzó scope;
- si la auditoría conserva el evento;
- si el usuario recibió una explicación útil.

La negativa textual es la última línea de defensa, no la primera.

## La tesis

La seguridad de agentes no se resuelve haciendo modelos más educados. Se resuelve
tratándolos como sistemas distribuidos con fronteras de confianza.

El modelo puede fallar. La herramienta debe limitarlo. La memoria debe resistir.
El log debe redactar. El tenant debe aislar. El test debe demostrarlo.

Red teaming serio significa atacar todo lo que el agente puede tocar.
