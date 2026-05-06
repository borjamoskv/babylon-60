---
title: "El TODO que Miró Demasiado Tiempo al Repositorio"
date: 2026-05-06
author: CORTEX Research Lab
tags: [humor, deuda-tecnica, desarrollo, agentes-ia, memoria]
description: "Una pieza divertida sobre TODOs que se vuelven arqueología, memoria de proyecto y señales de deuda técnica cuando nadie los convierte en decisiones."
slug: el-todo-que-miro-demasiado-tiempo
---

# El TODO que Miró Demasiado Tiempo al Repositorio

Todo repositorio tiene un TODO que empezó como nota humilde y acabó con despacho
propio.

Al principio decía:

```python
# TODO: clean this later
```

Luego pasaron tres releases, dos refactors, una migración y una semana en la que
nadie quiso preguntar qué significaba "this". Ahora ese comentario no es una
nota. Es patrimonio histórico.

## Tipos de TODO

No todos los TODOs son iguales.

| Tipo | Traducción real |
|---|---|
| `TODO: fix` | Nadie sabe qué está roto |
| `TODO: temporary` | Lleva dos años en producción |
| `TODO: optimize` | No hay benchmark |
| `TODO: refactor` | Hay miedo |
| `TODO: remove later` | Later se jubiló |

El problema no es escribir TODOs. El problema es no darles destino.

## El TODO como deuda sin interés visible

Un TODO no registrado no compite por prioridad. No aparece en el roadmap. No
bloquea CI. No tiene dueño. Solo espera.

Y mientras espera, cambia de naturaleza. Lo que era una nota de implementación
se convierte en una pregunta arquitectónica:

- ¿por qué sigue aquí?
- ¿qué riesgo tapa?
- ¿qué test falta?
- ¿quién puede borrarlo sin romper nada?

Cuando un comentario necesita arqueología, ya no es comentario. Es deuda.

## Memoria para comentarios vivos

Un agente con memoria puede hacer algo útil: convertir TODOs en objetos.

```text
TODO detectado
scope identificado
riesgo estimado
dueño sugerido
test faltante
fecha de revisión
```

No todos deben resolverse al momento. Pero todos deberían tener estado.

## El ritual de saneamiento

Una vez por semana, el agente puede preguntar:

1. ¿Qué TODOs nuevos aparecieron?
2. ¿Qué TODOs viejos no han cambiado?
3. ¿Cuáles están en rutas críticas?
4. ¿Cuáles no tienen issue asociado?
5. ¿Cuáles se pueden convertir en test?

Ese ritual no arregla el repo, pero evita que la deuda se disfrace de decoración.

## La tesis

Un TODO sano es una promesa con calendario.

Un TODO enfermo es una frase que aprendió a sobrevivir en los márgenes del código.

Si tu agente recuerda los TODOs, el repositorio deja de fingir que no los vio.
