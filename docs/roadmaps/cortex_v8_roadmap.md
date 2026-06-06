<!-- [C5-REAL] Exergy-Maximized -->
---
title: CORTEX v8.0 Production Roadmap
description: Plan de transición de MVP a sistema enterprise-grade (El camino a V8)
---

# CORTEX v8.0: The Production Roadmap (30 Days)

> **DIAGNÓSTICO SOBERANO**
> CORTEX está posicionado estratégicamente como el motor de persistencia criptográfica para IA. La separación arquitectónica CORTEX (producto) vs MOSKV-1 (capa personal) es impecable. Sin embargo, para consolidar el paso de "infraestructura operativa" a "producto enterprise-grade robusto", debemos cerrar brechas críticas en evaluación, recuperación semántica y observabilidad real.

Este roadmap describe el plan de 30 días para transformar CORTEX en un sistema de memoria de grado producción indiscutible, basado en 6 ejes de fallo sistémico detectados.

---

## 🎯 6 Ejes de Mejora Sistémica

### 1. Evaluation Layer Formal (Falta el Control de Calidad)
Actualmente, el *health check* mide si el archivo existe y su tamaño (presencia de infra), pero no sabemos la calidad de esa memoria.
**Objetivo V8:** Medir `recall@k`, precisión factual post-recall, tasa de contradicciones y utilidad percibida.

### 2. Retrieval Semántico y Ranking Contextual
La recuperación actual (`cat` + `grep` + `tail`) es un *fallback* potente, pero insuficiente para escalar en sesiones de IA largas y ambiguas.
**Objetivo V8:** Retrieval inteligente basado en recencia, impacto, similitud semántica y factor de confianza (Hybrid Search).

### 3. Data Governance de Memoria (Anti-Contaminación)
No hay controles fuertes previos antes de la ingesta (escribir un `_facts.json` y subir en batch asume que el input es puro).
**Objetivo V8:** Validación de *schema* por `fact_type`, deduplicación semántica estricta (no meter el mismo hecho 5 veces), control de conflictos semánticos y un *Confidence Score* por cada persistencia.

### 4. Observabilidad de Sistema vs Producto
El dashboard actual valida que Python y SQLite estén en la máquina. No mide si el sistema está fallando a nivel de producto.
**Objetivo V8:** Establecer verdaderos SLOs (Service Level Objectives). Latencia de recall `p95`, *error budget*, freshness SLA por proyecto, y monitorización de drift de embeddings. Validaciones activas del ciclo de vida MCP.

### 5. Cierre del Loop de Autosuperación con Señales Reales
Actualmente usamos entropía simulada para detonar las rutinas de mejora continua en el daemon.
**Objetivo V8:** Conectar el loop de `mejora_loop.py` directamente con las métricas reales de errores, inactividad y fallos de recall de CORTEX, para priorizar su propia evolución.

### 6. Enforcement Técnico en la Frontera Producto vs Personal
La teoría (MOSKV-1 es personal, CORTEX es producto) está clara; la práctica requiere murallas.
**Objetivo V8:** Inyectar políticas de aislamiento (Multi-Tenant nativo real), *namespaces* estrictos (para evitar fugas de `borjamoskv` hacia `enterpriseX`), auditorías de acceso e *import/export* con contratos de datos claros.

---

## 🗺️ El Roadmap a 30 Días (Hyper-Velocity v8)

### Semana 1: Quality KPIs & Evaluación Base

El objetivo es no estar ciegos ante la calidad de los datos que almacena el sistema.

*   [ ] **Setup de Métricas Factuales**: Implementar script o hook de medición de *Recall precision proxy* en `cortex/memory`.
*   [ ] **Tasa de Contradicción**: Lógica que escanea el banco de memoria en background y flaggea hechos que entran en oposición heurística o lógica (p.ej.: "Framework: React" vs "Framework: Vue" en el mismo componente).
*   [ ] **Stale-Memory Ratio**: Detectar *facts* huérfanos sin *hits* en más de X meses.
*   [ ] **Latencia `p95`**: Trazabilidad de cuánto tarda el sistema en servir un estado coherente al bootear una sesión.

### Semana 2: Guardrails de Ingestión (La Muralla)

Impedir que memoria de baja calidad o corrompida entre siquiera a la Vault.

*   [ ] **Validation Layer en `store`**: Implementar validación Pydantic fuerte sobre `_facts.json` antes de pasar a SQLite. Exigir `provenance` y `confidence_score` OBLIGATORIAMENTE.
*   [ ] **Deduplicación Semántica**: Antes de insertar `X`, vectorizar y comprobar similitud del `>90%` con los N *facts* más parecidos del proyecto. Si es idéntico, actualizar `last_accessed` y descartar inserción.
*   [ ] **Conflict Resolution Rules**: Si entra un hecho que colisiona con el *schema* (C2 Speculative vs C5 Confirmed), rechazar el C2.

### Semana 3: Retrieval v2 (El Buscador Híbrido)

El paso de *grep* a Recuperación Basada en Inteligencia.

*   [ ] **Hybrid Search Core**: Reemplazar/Aumentar la extracción con BM25 (keyword matching) + Text Embeddings (dense semantic).
*   [ ] **Reglas de Prioridad `fact_type`**: Dar mayor weight a `decision` y `error` sobre observaciones estándar según el contexto operativo.
*   [ ] **Context Slicing**: Paginación inteligente y filtrado por tarea, recencia y trust para que el LLM no reciba `cat snapshot.md` crudo si es de >20k tokens.

### Semana 4: Operativización Total (Closed Loop & Aislamiento)

Hacer de CORTEX una API empresarial indestructible.

*   [ ] **Eliminación del Decay Simulado**: Borrar toda referencia a simulación estadística en `mejora_loop.py`. Enganchar la señal de ejecución a los KPIs de la *Semana 1*.
*   [ ] **Namespacing y Aislamiento por Tenant**: Forzar a `cortex.cli` y REST Server a validar explícitamente el Tenant ID o la API Key asociada a una base de datos particionada.
*   [ ] **Auditoría Definitiva**: Crear ruta inviolable para auditar qué usuario/modelo insertó qué `fact`.

---

> 💡 **[SOVEREIGN TIP]** (KAIROS-Ω)
> La construcción de la capa de Evaluación (Semana 1) es el apalancamiento epistémico definitivo. Construir memoria persistente sin medir *qué tan útil* resulta esa recuperación es optimizar a ciegas. **Nunca insertes lo que no puedes evaluar y nunca almacenes lo que no puedes deduduplicar.**

