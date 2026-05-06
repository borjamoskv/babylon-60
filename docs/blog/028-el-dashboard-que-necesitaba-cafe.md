---
title: "El Dashboard que Necesitaba Café"
date: 2026-05-06
author: CORTEX Research Lab
tags: [humor, dashboard, observabilidad, producto, agentes-ia]
description: "Una pieza divertida sobre dashboards con demasiadas gráficas, poca decisión y cero jerarquía operativa."
slug: el-dashboard-que-necesitaba-cafe
---

# El Dashboard que Necesitaba Café

Hay dashboards que informan. Hay dashboards que decoran. Y hay dashboards que
parecen haber aceptado todas las métricas del mundo por miedo a decir que no.

Entras y ves 23 gráficas, 14 colores, 9 porcentajes y una tabla que nadie ha
mirado desde febrero.

El sistema no está observado. Está empapelado.

## Métrica sin decisión

Cada métrica debería responder a una pregunta:

- ¿debo actuar?
- ¿está empeorando?
- ¿qué usuario o tenant afecta?
- ¿qué cambió desde ayer?
- ¿qué umbral importa?

Si una gráfica no cambia ninguna decisión, quizá es fondo de pantalla.

## Jerarquía visual

Un dashboard operativo debe decir primero lo urgente:

1. estado global;
2. incidentes activos;
3. degradaciones;
4. colas o jobs atascados;
5. errores por causa;
6. acciones recomendadas.

Lo demás puede existir, pero no debe gritar.

## Dashboards de agentes

Para agentes IA, las métricas útiles no son solo CPU y latencia. También importan:

- herramientas bloqueadas;
- memoria escrita;
- rechazos de guardas;
- costes por modelo;
- acciones pendientes;
- confianza de facts;
- eventos redaccionados.

La pregunta central es: ¿el agente está actuando dentro de su mandato?

## Menos gráfica, más decisión

Un buen panel puede ser sobrio:

```text
OK / degraded / blocked
por que
desde cuando
impacto
siguiente accion
```

Eso ya vale más que ocho curvas sin dueño.

## La tesis

El dashboard no necesita más cafeína visual.

Necesita criterio.
