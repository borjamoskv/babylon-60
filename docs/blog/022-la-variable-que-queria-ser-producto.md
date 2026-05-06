---
title: "La Variable que Quería Ser Producto"
date: 2026-05-06
author: CORTEX Research Lab
tags: [humor, producto, nombres, desarrollo, arquitectura]
description: "Un artículo divertido sobre nombres de variables que crecen hasta convertirse en conceptos de producto sin contrato, dueño ni documentación."
slug: la-variable-que-queria-ser-producto
---

# La Variable que Quería Ser Producto

Todo empieza con una variable inocente:

```python
mode = "auto"
```

Parece pequeña. Manejable. Casi educada.

Tres meses después, `mode` acepta `auto`, `manual`, `safe`, `legacy`, `smart`,
`silent`, `turbo`, `enterprise` y un valor secreto que solo aparece en staging.
Ya no es una variable. Es una estrategia comercial con problemas de identidad.

## Los nombres avisan

Cuando un nombre empieza a sonar demasiado genérico, suele estar escondiendo una
decisión.

| Nombre | Sospecha |
|---|---|
| `mode` | hay un producto dentro |
| `config` | nadie quiso tipar |
| `data` | se perdió el dominio |
| `options` | crecerá sin permiso |
| `flag` | alguien teme borrar algo |

El código no miente. A veces solo habla con nombres demasiado baratos.

## El agente como notario de conceptos

Un agente puede detectar cuándo una variable deja de ser detalle técnico:

- aparece en muchas rutas;
- controla permisos;
- cambia UI;
- afecta precio;
- altera seguridad;
- entra en documentación;
- necesita migración.

Ese es el momento de elevarla: tipo explícito, contrato, tests, docs y dueño.

## Producto sin acta

Muchas features nacen como `if`. Nadie las diseña. Nadie las anuncia. Simplemente
crecen hasta que soporte recibe una pregunta y producto descubre que existe una
modalidad nueva.

La deuda no siempre es código feo. A veces es producto no declarado.

## La tesis

Si una variable cambia comportamiento de usuario, ya no es una variable.

Es una promesa.

Y las promesas necesitan nombre, contrato y memoria.
