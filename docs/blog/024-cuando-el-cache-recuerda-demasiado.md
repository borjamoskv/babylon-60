---
title: "Cuando el Cache Recuerda Demasiado"
date: 2026-05-06
author: CORTEX Research Lab
tags: [humor, cache, memoria, seguridad, arquitectura]
description: "Una pieza divertida sobre caches que sobreviven a la verdad, invalidación, tenant scope y memoria accidental."
slug: cuando-el-cache-recuerda-demasiado
---

# Cuando el Cache Recuerda Demasiado

El cache nació para ayudar. Quería ahorrar tiempo, reducir carga y parecer
inofensivo.

Luego un día recordó algo que ya no era verdad.

Y ahí empezó el problema.

## La memoria sin criterio

Un cache no entiende de contexto. Si le das una clave pobre, obedecerá con
entusiasmo.

```text
key = "user_settings"
```

Bonito. Breve. Peligroso.

¿De qué usuario? ¿Qué tenant? ¿Qué versión? ¿Qué permisos? ¿Qué idioma? ¿Qué
feature flags? El cache no pregunta. El cache sirve.

## Invalidation, esa conversación pendiente

La invalidación es difícil porque obliga a admitir qué significa "vigente".

Un dato puede caducar por:

- tiempo;
- cambio de usuario;
- cambio de permisos;
- migración;
- despliegue;
- tenant;
- revocación;
- corrección de bug.

Si solo usas TTL, estás diciendo que la verdad envejece con reloj. A veces
envejece con un evento.

## Cache y agentes

En agentes IA, el cache se vuelve más delicado. Puede guardar:

- respuestas de modelos;
- resultados de herramientas;
- fragmentos de memoria;
- permisos calculados;
- documentos recuperados.

Si el scope está mal, una respuesta útil se convierte en fuga. Si la confianza no
se guarda, una hipótesis vieja vuelve con cara de hecho.

## Reglas aburridas que salvan días

1. incluir tenant en la clave;
2. incluir versión de contrato;
3. registrar fuente;
4. separar cache de memoria persistente;
5. invalidar por evento cuando importe;
6. no cachear secretos;
7. medir hit rate sin guardar payloads.

## La tesis

El cache no es malo. Solo tiene una memoria demasiado literal.

Si no le enseñas qué significa olvidar, recordará cosas con una seguridad
preocupante.
