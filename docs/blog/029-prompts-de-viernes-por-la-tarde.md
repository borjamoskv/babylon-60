---
title: "Prompts de Viernes por la Tarde"
date: 2026-05-06
author: CORTEX Research Lab
tags: [humor, prompts, productividad, agentes-ia, desarrollo]
description: "Una pieza ligera sobre prompts escritos con cansancio, urgencia y demasiada esperanza antes del fin de semana."
slug: prompts-de-viernes-por-la-tarde
---

# Prompts de Viernes por la Tarde

El prompt de viernes por la tarde tiene un tono especial.

No dice "analiza cuidadosamente la arquitectura". Dice:

> arregla esto rapido pls

El agente recibe cuatro palabras, un repo enorme y una expectativa silenciosa:
que entienda el dolor acumulado de toda la semana.

## El problema no es la prisa

La prisa es real. El problema es fingir que no cambia el riesgo.

Un prompt urgente debería incluir más estructura, no menos:

- qué está roto;
- cómo se reproduce;
- qué no tocar;
- qué check debe pasar;
- qué significa "suficiente por hoy";
- qué puede esperar al lunes.

La urgencia sin perímetro invita al agente a improvisar.

## El modo viernes

Un buen agente debería detectar señales:

```text
rapido
solo esto
antes de irme
no quiero tocar mucho
mañana lo vemos
```

Y responder con contención:

1. reproducir fallo;
2. aplicar cambio mínimo;
3. verificar;
4. dejar deuda explícita;
5. no abrir refactors nuevos.

El viernes no es momento de descubrir una arquitectura interior.

## La deuda con nombre

Si queda algo pendiente, escríbelo:

```text
Riesgo residual:
- no se revisó el caso multi-tenant
- falta test de regresión completo
- workaround limitado a la ruta X
```

La deuda sin nombre se convierte en lunes sorpresa.

## La tesis

El prompt de viernes puede ser corto. Pero no debe ser ambiguo.

Un agente útil no convierte cansancio en alcance infinito.

Lo reduce, lo verifica y deja una nota para el lunes.
