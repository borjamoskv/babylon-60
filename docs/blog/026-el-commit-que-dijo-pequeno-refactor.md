---
title: "El Commit que Dijo Pequeño Refactor"
date: 2026-05-06
author: CORTEX Research Lab
tags: [humor, git, refactor, desarrollo, agentes-ia]
description: "Una pieza divertida sobre commits que prometen ser pequeños y acaban tocando media arquitectura."
slug: el-commit-que-dijo-pequeno-refactor
---

# El Commit que Dijo Pequeño Refactor

El mensaje decía:

```text
refactor: cleanup
```

Luego abriste el diff y viste 47 archivos, tres abstracciones nuevas, una función
renombrada en cascada y un comentario que decía "temporary compatibility layer".

No era cleanup. Era mudanza.

## El refactor honesto

Un refactor real cambia estructura sin cambiar comportamiento. Por eso necesita
pruebas, o al menos una explicación sólida de por qué el comportamiento queda
igual.

Si además cambia contratos, nombres públicos, docs y tests, ya no es refactor.
Es feature con bigote.

## Señales de peligro

- "solo moví cosas";
- "aproveché para limpiar";
- "esto estaba feo";
- "no debería afectar";
- "los tests relevantes pasan";
- "luego lo documento".

Cada frase puede ser cierta. Juntas forman niebla.

## El agente y el diff pequeño

Un agente debería aprender una virtud difícil: parar.

Cuando descubre una deuda cercana al cambio, debe decidir:

```text
¿bloquea la tarea actual?
si -> tocar
no -> registrar y dejar
```

La disciplina no está en ver más problemas. Está en no resolverlos todos en el
mismo commit.

## Un buen mensaje de commit

Mejor:

```text
refactor(memory): extract compaction policy without behavior change
```

Y en el cuerpo:

- qué se movió;
- qué no cambió;
- qué tests lo cubren;
- qué deuda queda fuera.

## La tesis

"Pequeño refactor" es una promesa. Si el diff no la cumple, cambia el mensaje o
divide el cambio.

Git no olvida.

Y el reviewer tampoco debería.
