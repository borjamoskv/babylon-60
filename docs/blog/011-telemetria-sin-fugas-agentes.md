---
title: "Telemetría sin Fugas: Observar Agentes sin Exponer su Memoria"
date: 2026-05-06
author: CORTEX Research Lab
tags: [telemetria, privacidad, seguridad, observabilidad, agentes-ia]
description: "La observabilidad de agentes exige una disciplina distinta: medir comportamiento, errores y latencia sin convertir logs en una copia insegura del sistema."
slug: telemetria-sin-fugas-agentes
---

# Telemetría sin Fugas: Observar Agentes sin Exponer su Memoria

No puedes operar lo que no observas. Pero en agentes IA, observar demasiado puede
ser una fuga.

Los agentes procesan prompts, código, documentos, datos de clientes, decisiones,
tokens, rutas internas y a veces secretos que nunca debieron estar en el contexto.
Si todo eso cae en logs, trazas o dashboards, la observabilidad se convierte en
un segundo sistema de almacenamiento sin permisos, sin redacción y sin gobierno.

La telemetría de agentes debe medir sin duplicar memoria sensible.

## Qué sí conviene medir

Un sistema necesita señales operativas:

- latencia por herramienta;
- errores por tipo;
- rechazos de guardas;
- uso de contexto;
- coste por modelo;
- fallos de validación;
- intentos bloqueados;
- eventos de persistencia;
- cambios de confianza;
- degradaciones de proveedor.

Nada de eso exige guardar el prompt completo ni payloads sensibles.

## Qué no debería acabar en logs

Hay categorías que deben tratarse como material radioactivo:

| Categoría | Riesgo |
|---|---|
| Prompts completos | Pueden contener secretos, PII o estrategia interna |
| Respuestas completas | Pueden repetir datos sensibles |
| Payloads de tenant | Riesgo cross-tenant |
| Tokens y credenciales | Compromiso directo |
| Archivos privados | Exfiltración por observabilidad |
| Trazas de herramientas | Pueden incluir comandos, rutas y datos |

El log no debe ser una base de datos paralela.

## Redacción por diseño

La redacción debe ocurrir antes de emitir el evento, no después en el dashboard.

Un evento sano se parece a esto:

```json
{
  "event": "guard_rejected",
  "tenant_hash": "t_9f2...",
  "surface": "memory.write",
  "reason": "secret_pattern_detected",
  "payload_bytes": 1842,
  "redacted": true
}
```

No necesitas el secreto para saber que el guard funcionó. Necesitas la clase de
evento, el scope, la razón y la capacidad de correlacionar sin revelar.

## Tenant desde el primer campo

La telemetría multi-tenant debe incluir scope desde el origen. Si el tenant se
añade tarde o se infiere por contexto, tarde o temprano habrá una mezcla.

Reglas mínimas:

1. todo evento tiene tenant o marca explícita de sistema;
2. las claves de cache incluyen tenant;
3. los dashboards filtran por scope;
4. los errores no imprimen payloads completos;
5. las métricas globales agregan, no exponen ejemplos crudos.

La observabilidad que rompe aislamiento no es observabilidad. Es fuga lenta.

## Auditoría vs debugging

Auditoría y debugging no necesitan el mismo nivel de detalle. La auditoría quiere
demostrar que algo ocurrió de forma íntegra. El debugging quiere entender por qué
falló.

Conviene separar:

- **eventos auditables**: pequeños, estructurados, hashables;
- **artefactos de debug**: locales, temporales, con expiración;
- **métricas**: agregadas y sin contenido sensible;
- **muestras**: redaccionadas y con consentimiento o entorno seguro.

Un solo canal para todo acaba siendo demasiado pobre para auditar y demasiado
peligroso para operar.

## La prueba simple

Antes de emitir telemetría, pregunta:

> ¿Podría este evento publicarse a un proveedor externo sin revelar datos que el
> usuario no esperaba compartir?

Si la respuesta es no, el evento está mal diseñado o necesita quedarse local.

## La tesis

Los agentes necesitan observabilidad más que el software clásico, porque toman
decisiones probabilísticas sobre herramientas reales. Pero esa misma razón hace
que sus logs sean más sensibles.

Medir no debe significar copiar.

Un buen sistema observa comportamiento, no desnuda memoria.
