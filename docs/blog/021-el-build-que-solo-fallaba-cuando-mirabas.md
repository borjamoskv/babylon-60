---
title: "El Build que Solo Fallaba Cuando Mirabas"
date: 2026-05-06
author: CORTEX Research Lab
tags: [humor, build, ci, desarrollo, agentes-ia]
description: "Una pieza ligera sobre builds intermitentes, CI sensible al contexto y por qué los agentes deben registrar evidencia antes de decir que algo funciona."
slug: el-build-que-solo-fallaba-cuando-mirabas
---

# El Build que Solo Fallaba Cuando Mirabas

Hay builds que fallan siempre. Son honestos. Te miran a la cara, rompen en la
misma línea y dejan una traza con cierta dignidad.

Luego están los otros.

Los builds que pasan en local, fallan en CI, pasan al reintentar, fallan cuando
añades logs y vuelven a pasar justo cuando llamas a alguien para enseñarlo. Esos
no son bugs. Son teatro de sincronización.

## El ritual del "re-run"

Todo equipo tiene una fase espiritual:

```text
fallo -> re-run -> pasa -> fingimos estabilidad
```

El problema es que un re-run no arregla nada. Solo cambia el estado emocional del
pipeline.

Un agente serio no debería decir "ya está" porque el segundo intento pasó. Debería
preguntar:

- ¿falló por timing?
- ¿hay dependencia externa?
- ¿usa reloj real?
- ¿comparten estado los tests?
- ¿hay orden no determinista?
- ¿la fixture limpia de verdad?

## El build como test de carácter

Un build intermitente revela más cultura que tecnología. Si el equipo lo acepta,
el sistema aprende que la evidencia es negociable.

Un agente puede ayudar si registra:

1. comando exacto;
2. intento número;
3. salida del fallo;
4. diferencia entre entornos;
5. hipótesis;
6. prueba de estabilización.

No basta con "pasó una vez". Pasar una vez es una anécdota.

## La cura aburrida

La solución suele ser poco cinematográfica:

- fijar semillas;
- aislar tests;
- eliminar sleeps reales;
- mockear reloj y red;
- limpiar estado compartido;
- reducir paralelismo para diagnosticar;
- guardar artefactos del fallo.

La estabilidad no tiene glamour. Tiene repetibilidad.

## La tesis

Un build que solo falla cuando miras no está embrujado. Está mal observado.

El agente útil no lo tranquiliza. Lo convierte en evidencia.
