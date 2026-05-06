---
title: "Terapia de Pareja para API y CLI"
date: 2026-05-06
author: CORTEX Research Lab
tags: [humor, api, cli, producto, arquitectura]
description: "Una pieza ligera sobre contratos rotos entre API y CLI, documentación que promete demasiado y la necesidad de una sola verdad operativa."
slug: terapia-de-pareja-para-api-y-cli
---

# Terapia de Pareja para API y CLI

La API dijo:

> Yo nunca prometí ese campo.

La CLI respondió:

> Está en la documentación.

La documentación miró al suelo.

Así empiezan muchos incidentes pequeños: no con un crash espectacular, sino con
tres superficies del mismo producto contando historias ligeramente distintas.

## El triángulo clásico

La API devuelve una cosa. La CLI espera otra. La documentación describe una
tercera. El usuario, con admirable optimismo, intenta usar las tres.

Síntomas:

- flags que no existen;
- ejemplos que ya no ejecutan;
- respuestas JSON con campos renombrados;
- errores que no aparecen en la guía;
- comandos que funcionan solo en la máquina de quien los escribió.

## La verdad única

Un producto sano necesita una fuente de contrato.

Puede ser OpenAPI, tipos compartidos, tests de contrato, snapshots o generación
automática de docs. Lo importante es que no haya tres verdades editadas a mano.

```text
contrato -> API
contrato -> CLI
contrato -> docs
contrato -> tests
```

Cuando el contrato cambia, todo lo demás debe enterarse.

## La CLI también tiene sentimientos

La CLI es donde las promesas se vuelven fricción. Si un usuario copia un comando
y falla, no piensa "hay drift entre superficies". Piensa otra cosa menos amable.

Por eso cada comando documentado debería tener prueba o smoke test.

No por perfeccionismo. Por respeto al tiempo ajeno.

## La API no lee la mente

La API necesita contratos explícitos:

- tipos;
- errores;
- scopes;
- autenticación;
- paginación;
- compatibilidad;
- deprecaciones.

Si un cliente tiene que adivinar, el contrato ya falló.

## La documentación no debe inventar

La documentación tiene una tentación literaria: hacer que el producto parezca
más ordenado de lo que está.

Resiste.

Una guía honesta con limitaciones claras vende menos humo y ahorra más soporte.

## La tesis

API, CLI y docs no son tres productos. Son tres formas de tocar el mismo sistema.

Si no dicen lo mismo, el usuario paga la terapia.

Mejor pagar tests de contrato.
