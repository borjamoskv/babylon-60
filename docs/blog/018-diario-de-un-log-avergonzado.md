---
title: "Diario de un Log Avergonzado"
date: 2026-05-06
author: CORTEX Research Lab
tags: [humor, logs, privacidad, observabilidad, agentes-ia]
description: "Una pieza ligera sobre logs que cuentan demasiado, observabilidad responsable y el arte de medir sin convertir la telemetría en confesionario."
slug: diario-de-un-log-avergonzado
---

# Diario de un Log Avergonzado

Querido diario:

Hoy he vuelto a imprimir un payload entero en producción.

No quería. Yo nací para ayudar. Un error aquí, una latencia allá, un contador
honesto. Pero alguien escribió `logger.info(request)` y ahora sé demasiado.

Sé rutas internas. Sé nombres que no debería saber. Sé un token que pasó por mi
vida durante 11 milisegundos y que ahora vivirá en un dashboard hasta que alguien
recuerde rotar retención.

No estoy orgulloso.

## El log que quería ser útil

Un buen log responde preguntas:

- qué pasó;
- cuándo pasó;
- dónde pasó;
- con qué scope;
- qué clase de error fue;
- si el payload fue redaccionado.

No necesita enseñar todo para demostrar que estuvo allí.

## El log que se pasó de confianza

Hay señales claras:

```text
user_prompt="..."
api_key="..."
tenant_payload={...}
full_request_body={...}
```

Ese log no está observando. Está coleccionando secretos.

## Redacción como buenos modales

Redactar no es censurar. Es tener educación operativa.

```json
{
  "event": "tool_failed",
  "tool": "ledger.write",
  "tenant_hash": "t_42...",
  "reason": "validation_error",
  "payload_redacted": true
}
```

Mucho mejor. Nadie tuvo que ver el contenido sensible para saber que algo falló.

## La telemetría no es terapia

El sistema no debe contarlo todo para sentirse comprendido. Debe contar lo
necesario para ser operable.

Un agente serio registra eventos. No abre su memoria completa en cada excepción.

## La tesis

El mejor log es discreto, estructurado y útil.

Sabe lo suficiente para ayudarte.

Y olvida lo suficiente para no meterte en problemas.
