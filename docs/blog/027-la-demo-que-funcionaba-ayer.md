---
title: "La Demo que Funcionaba Ayer"
date: 2026-05-06
author: CORTEX Research Lab
tags: [humor, demos, producto, desarrollo, verificacion]
description: "Una pieza ligera sobre demos frágiles, scripts de preparación y la diferencia entre funcionar una vez y ser demostrable."
slug: la-demo-que-funcionaba-ayer
---

# La Demo que Funcionaba Ayer

La demo funcionaba ayer. Esa frase debería venir con alarma.

Ayer también había una base de datos concreta, un token vivo, una pestaña ya
logueada, un puerto libre y una secuencia de comandos que alguien ejecutó en el
orden correcto sin saberlo.

Hoy, por supuesto, la demo ha decidido estudiar filosofía.

## Demo no es producto

Una demo puede enseñar una idea. Un producto debe sobrevivir a usuarios, estados
raros, latencia, permisos, errores y reinicios.

Confundir demo con producto es fácil porque ambas cosas tienen botones.

La diferencia aparece cuando alguien pulsa el botón equivocado.

## El script de invocación

Toda demo debería tener un `demo.md` o script de preparación:

```text
dependencias
variables necesarias
datos semilla
comando de arranque
flujo esperado
fallos conocidos
rollback
```

Si la demo depende de memoria tribal, fallará justo cuando haya audiencia.

## El agente como stage manager

Un agente puede preparar demos sin magia:

- verificar puertos;
- comprobar variables;
- sembrar datos;
- abrir URLs;
- ejecutar smoke tests;
- listar riesgos;
- dejar comandos de recuperación.

No hace falta prometer perfección. Hace falta reducir sorpresa.

## La pregunta clave

Antes de enseñar algo, pregunta:

> ¿Puede otra persona reproducir esto desde cero?

Si la respuesta es no, tienes una escena, no una demo reproducible.

## La tesis

Que algo funcionara ayer es una pista histórica, no una garantía.

La demo madura no confía en la memoria. La escribe.
