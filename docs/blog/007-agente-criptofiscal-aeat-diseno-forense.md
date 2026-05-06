---
title: "Diseñar un Agente CriptoFiscal: Forense Primero, Fiscal Después"
date: 2026-05-06
author: CORTEX Research Lab
tags: [criptofiscal, aeat, forense, blockchain, agentes-ia]
description: "Cómo debería razonar un agente fiscal para criptoactivos: reconstrucción probatoria, separación de hechos e inferencias y dossier defendible antes de cualquier cálculo."
slug: agente-criptofiscal-aeat-diseno-forense
---

# Diseñar un Agente CriptoFiscal: Forense Primero, Fiscal Después

> Nota editorial: este artículo describe arquitectura de agentes y flujo
> probatorio. No es asesoramiento fiscal ni legal. Cualquier criterio aplicable
> debe contrastarse con fuentes oficiales vigentes y con un profesional humano.

Un agente fiscal para cripto no debería empezar calculando impuestos. Debería
empezar reconstruyendo realidad.

La tentación es pedirle al modelo una respuesta directa: "¿cuánto debo declarar?".
Ese atajo es peligroso. En cripto, la parte difícil no suele ser aplicar una
fórmula, sino saber qué ocurrió realmente: qué wallets pertenecen al contribuyente,
qué operaciones fueron swaps, cuáles fueron transfers internos, dónde hubo comisiones,
qué precio en euros aplica, qué datos faltan y qué afirmaciones pueden probarse.

Antes de fiscal, el agente debe ser forense.

## El orden correcto

Un flujo defendible separa cinco fases:

```text
ingesta -> normalización -> atribución -> valoración -> dossier
```

Primero se cargan CSVs, extractos de exchanges, wallets y exploradores. Después
se normalizan formatos, símbolos, timestamps y comisiones. Luego se atribuyen
direcciones y operaciones con distintos niveles de confianza. Solo entonces se
valoran eventos y se preparan salidas fiscales o probatorias.

El error común es mezclarlo todo en una tabla final. Eso produce números rápidos
y explicaciones débiles.

## Hechos, inferencias y pendientes

La regla central es no confundir tipos de conocimiento:

| Tipo | Ejemplo |
|---|---|
| Hecho verificado | Un CSV de exchange contiene una venta en fecha concreta |
| Inferencia | Dos wallets parecen del mismo titular por patrón de consolidación |
| Dato pendiente | Falta el histórico de precios para un token ilíquido |
| Criterio aplicado | Método de valoración usado para convertir a euros |

Un agente serio debe etiquetar cada línea. Si una wallet está atribuida por
inferencia, no puede tratarse como hecho absoluto. Si falta una cotización, no
puede rellenarse con una cifra inventada. Si una operación no se entiende, debe
quedar en cola de revisión.

El objetivo no es sonar seguro. Es construir un expediente que sobreviva a
preguntas.

## La memoria como cadena de custodia

Los casos cripto se degradan cuando el trabajo se reparte entre hojas de cálculo,
notas sueltas, exploradores y capturas sin relación. Un agente con memoria
persistente puede mantener una cadena de custodia interna:

- origen del dato;
- hash o identificador del archivo;
- timestamp de ingesta;
- transformación aplicada;
- versión de la tabla normalizada;
- regla de valoración;
- observaciones pendientes.

Eso no convierte el sistema en autoridad fiscal. Lo convierte en una herramienta
que puede explicar cómo llegó a cada número.

## Redacción de riesgo

Un agente criptofiscal debe ser especialmente cuidadoso con secretos y privacidad.
No necesita guardar semillas, claves privadas, capturas completas de cuentas ni
payloads personales innecesarios. Tampoco debería enviar a modelos externos más
contexto del imprescindible.

La buena práctica es trabajar con mínimos:

1. direcciones públicas cuando basten;
2. extractos redaccionados;
3. hashes de archivos;
4. etiquetas de confianza;
5. separación entre datos personales y análisis técnico.

La privacidad no es un añadido legal. Es parte de la arquitectura.

## Dossier antes que respuesta

La salida más valiosa no es una frase. Es un dossier:

- resumen de hechos verificados;
- inventario de fuentes;
- tabla de operaciones normalizadas;
- operaciones ambiguas;
- criterios aplicados;
- cálculos reproducibles;
- riesgos y datos pendientes;
- preguntas para asesor humano.

El agente no sustituye al profesional fiscal. Le entrega una base mucho menos
caótica.

## La tesis

Cripto no necesita otro chatbot que prometa respuestas fiscales instantáneas.
Necesita sistemas que reconstruyan operaciones con paciencia, etiqueten
incertidumbre y produzcan evidencia trazable.

En fiscalidad, la velocidad sin defensa es ruido.

Un buen agente no dice "este es el número" demasiado pronto. Dice: "estos son
los hechos, estas las inferencias, estas las lagunas y este es el cálculo que se
puede defender con lo que tenemos".
