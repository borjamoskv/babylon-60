---
title: "Arquitectura FRONTERA"
description: "Cómo CORTEX integra modelos frontier con una frontera determinista, memoria auditable y despliegue local-first."
sidebar:
  label: "Arquitectura FRONTERA"
---

# Arquitectura FRONTERA

En CORTEX, `FRONTERA` no significa solo usar el modelo con mejor benchmark.

Significa diseñar el sistema de forma que el cómputo de frontera quede confinado a la generación, mientras que la autoridad sobre el estado permanece en una capa determinista, verificable y auditable.

Dicho de otro modo:

- el modelo de frontera propone
- CORTEX valida
- el ledger atestigua
- la memoria persiste solo lo que ha cruzado la frontera de confianza

Esa separación es la arquitectura.

## Qué Problema Resuelve

Los modelos frontier son útiles porque comprimen una gran capacidad de inferencia en tiempo de ejecución.

También introducen un problema estructural: su salida es estocástica. Puede ser brillante, parcial, incoherente o peligrosa. Si ese output obtiene permisos de escritura directos sobre memoria, herramientas o datos de usuario, el sistema acumula deuda de verificación muy rápido.

La arquitectura FRONTERA existe para resolver esa tensión.

No intenta convertir un LLM en una fuente de verdad. Intenta aprovechar su capacidad sin concederle soberanía sobre el estado.

## Principio Operativo

La regla central es simple:

**más capacidad del modelo no reduce la necesidad de verificación; la aumenta.**

Por eso CORTEX trata toda salida generativa como conjetura hasta que cruza una frontera determinista compuesta por:

- validación de esquema y tipos
- guards de admisión y policy
- atribución mediante taint
- emisión criptográfica al ledger
- persistencia transaccional
- reversión explícita si cualquier paso falla

## Topología De Capas

```text
[Usuario / Sistema externo]
          |
          v
[Inference Tier]
Modelos frontier, routers, tool planning
          |
          v
[Deterministic Boundary]
Schema -> Guards -> Taint -> Verification
          |
          v
[Trust Core]
Ledger -> Engine -> Persistence transaction
          |
          v
[Memory Substrate]
SQLite / sqlite-vec / episodic + semantic surfaces
          |
          v
[Serving Surfaces]
API, routes, audit endpoints, export surfaces
```

### 1. Inference Tier

Esta capa concentra la generación y la planificación.

Su función es producir propuestas: facts, planes, clasificaciones, llamadas a herramientas o borradores de respuesta. Aquí encajan los adaptadores de modelos y la lógica de integración LLM.

En el repositorio, esta frontera aparece de forma explícita en superficies como:

- `cortex/extensions/llm/`
- `cortex/extensions/llm/boundary.py`
- `cortex/engine/inference.py`

Esta capa puede usar modelos locales o frontier. El punto crítico es que no puede persistir estado por sí sola.

### 2. Deterministic Boundary

Aquí vive la propiedad más importante de CORTEX.

La salida del modelo colisiona contra una frontera rígida antes de tocar memoria o ejecutar acciones irreversibles. Esa frontera no depende de la obediencia del modelo. Depende de código, tipos e invariantes.

Superficies relevantes:

- `cortex/extensions/llm/boundary.py` para validación estructural de salida
- `cortex/guards/` para admisión, sellos, taint y control de capacidad
- `cortex/verification/` para reglas, invariantes y verificación posterior

Si una propuesta no cumple el contrato, no se degrada silenciosamente. Se rechaza.

### 3. Trust Core

Una vez superada la frontera determinista, la propuesta entra en el núcleo de confianza.

Aquí importan tres cosas:

- continuidad causal
- trazabilidad
- rollback

La escritura real debe seguir un camino parecido a este:

```text
proposal
  -> guard pass
  -> taint attached
  -> schema validated
  -> audit event emitted
  -> persistence committed
  -> indexes updated
```

Si el fallo ocurre a mitad del camino, el sistema debe abortar hacia atrás, no completar parcialmente la mutación.

Superficies relevantes:

- `cortex/engine/`
- `cortex/ledger/ledger_core.py`
- `cortex/ledger/writer.py`
- `cortex/ledger/verifier.py`

### 4. Memory Substrate

La memoria de CORTEX no debe interpretarse como un simple almacén vectorial.

Su función es conservar estado útil sin perder procedencia, validez ni capacidad de auditoría. Por eso el sistema separa varias superficies de memoria y añade guardrails sobre ingestión, recuperación y consolidación.

Módulos representativos:

- `cortex/memory/manager.py`
- `cortex/memory/pipeline.py`
- `cortex/memory/sqlite_vec_store.py`
- `cortex/memory/guardrails.py`
- `cortex/memory/episodic.py`
- `cortex/memory/semantic_ram.py`

La idea central sigue siendo la misma: la memoria útil no es todo lo que el modelo genera, sino lo que el sistema puede defender después.

### 5. Serving Surfaces

La capa superior expone lo que el sistema ya ha validado o es capaz de procesar de forma segura.

Superficies relevantes:

- `cortex/api/`
- `cortex/routes/`
- rutas de ledger, trust, facts, memories y health

Esta capa no debería contener lógica de negocio crítica. Debe actuar como interfaz tipada hacia el núcleo.

## Flujo Canónico De Una Operación

Un request bien diseñado en FRONTERA sigue este patrón:

1. un usuario o sistema pide resolver una tarea
2. un modelo frontier produce una propuesta estructurada
3. la propuesta se limpia y valida contra un esquema
4. los guards comprueban política, forma, capacidad y taint
5. la verificación decide si la propuesta puede cruzar la frontera
6. el ledger emite el evento antes o junto al commit causal
7. la persistencia escribe el estado y actualiza índices
8. la API devuelve resultado y, cuando aplica, evidencia auditable

Ese flujo separa dos planos que no deben mezclarse:

- el plano de generación
- el plano de verdad operativa

## Qué Significa "FRONTERA" En Producción

En producción, `FRONTERA` no es un claim de marketing sobre quién tiene el mejor modelo.

Es la capacidad de operar con modelos muy capaces sin permitir que su salida:

- salte validaciones
- escriba estado no tipado
- cruce tenants
- pierda procedencia
- sobreviva a un fallo parcial sin rollback

Si un sistema usa frontier models pero no puede demostrar esos límites, no tiene arquitectura FRONTERA. Tiene una dependencia cara de inferencia.

## Topología Recomendada Hoy

La postura de despliegue que mejor encaja con el repositorio actual es local-first u operator-managed.

La razón es concreta: el core sigue orientado a estado persistente local, SQLite, almacenamiento auxiliar y continuidad auditable. Eso encaja peor en una plataforma totalmente stateless.

La topología recomendada hoy es:

### Capa pública

- sitio estático y documentación en una superficie desacoplada
- CDN, Cloud Run estático o reverse proxy simple

### Capa de API y motor

- instancia única o réplica muy controlada
- disco persistente real
- backup coordinado de base de datos y material criptográfico
- verificación periódica del ledger

### Capa de modelos

- proveedores frontier externos o locales
- siempre detrás de la frontera determinista
- nunca como fuente de autoridad sobre el estado

### Capa de export y auditoría

- endpoints de health
- export de audit packs
- artefactos verificables fuera del runtime activo

## Ejemplo Práctico En GCP

Si se quiere ejecutar esta arquitectura en Google Cloud sin traicionar la semántica del sistema, la forma razonable es:

1. `Cloud Run` para el sitio y la documentación
2. `Compute Engine` o despliegue operator-managed para la API de CORTEX con disco persistente
3. `Cloud Storage` para exportaciones, backups y audit packs
4. `Vertex AI` como proveedor opcional de inferencia, nunca como sustituto de la frontera de confianza

Lo que no tiene sentido hoy es forzar el core completo a una topología puramente stateless solo por comodidad de plataforma.

## Métricas Que Importan

Una arquitectura FRONTERA debería medirse con señales de control, no solo con benchmarks del modelo.

Las métricas importantes son:

- porcentaje de propuestas rechazadas por guards o verificación
- cobertura de taint sobre escrituras persistidas
- integridad del ledger y continuidad de hashes
- latencia de commit frente a latencia de inferencia
- ratio de rollback o abortos por Saga
- incidencia de lecturas cruzadas o violaciones de tenant scope
- porcentaje de respuestas con evidencia auditable adjunta

Estas métricas dicen más sobre la salud del sistema que un benchmark aislado de razonamiento.

## Lo Que Esta Arquitectura No Es

No es:

- un wrapper cosmético sobre un LLM
- un RAG con mejor branding
- un permiso para persistir chain-of-thought como si fuera verdad
- una prueba de que el sistema ya es multi-región, lock-free o hardware-native en producción

Internamente, `FRONTERA` también nombra una ambición más amplia sobre exergía, routing y capacidad agéntica. Pero la versión útil para producto e infraestructura es más estricta: **la capacidad frontier solo es valiosa si está contenida por una frontera verificable.**

## Cierre

La arquitectura FRONTERA convierte una idea abstracta en una separación de responsabilidades:

- el modelo explora
- la frontera decide
- el ledger testifica
- la memoria conserva solo lo defendible

Esa es la diferencia entre un sistema que genera texto convincente y un sistema que puede sostener decisiones, auditoría y memoria bajo carga real.

## Related Docs

- [Why AI Agents Need Deterministic Guardrails](why-ai-agents-need-deterministic-guardrails.md)
- [Deployment](deployment.md)
- [Security Trust Model](SECURITY_TRUST_MODEL.md)
- [Axiomas](AXIOMS.md)
- [Peano Soberano](peano-soberano.md)
