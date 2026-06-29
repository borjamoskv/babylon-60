# ADR 0005: Arquitectura de Nombres del Ecosistema MOSKV

## Status
Accepted

## Date
2026-06-29

## Context
El repositorio utiliza actualmente el namespace `cortex` como identidad estructural, namespace interno, marca y producto simultáneamente. Esto produce un fuerte acoplamiento entre el branding, la API pública, la organización del código, la persistencia, las variables de entorno y los esquemas de datos. Además, el nombre "Cortex" posee una elevada saturación en el ecosistema software, incrementando la confusión, el riesgo legal y disminuyendo la viabilidad de registro de marca.

## Decision
Se desacoplan definitivamente los distintos niveles de identidad en el ecosistema bajo las siguientes directrices:

### Nivel 0 — Empresa: **MOSKV**
* **Responsabilidad:** Marca, organización, ecosistema y firma de arquitectura.
* **Estabilidad:** Debe permanecer estable durante años.

### Nivel 1 — Producto: **BABYLON-60**
* **Responsabilidad:** Runtime, plataforma y distribución.
* **Estabilidad:** Puede evolucionar independientemente de la marca corporativa.

### Nivel 2 — Runtime: **Runtime Core**
* **Responsabilidad:** Módulos de bajo nivel (`memory`, `ledger`, `swarm`, `provenance`, `scheduler`, `agents`).
* **Estabilidad:** Estos módulos no deben depender del nombre comercial ni del marketing.

### Nivel 3 — Persistencia: **Nombres Neutrales**
* La persistencia en disco utilizará nombres neutrales que no dependan del branding:
  - `runtime.db`
  - `ledger.db`
  - `memory.db`

### Nivel 4 — Variables de Entorno: **Prefijo Corporativo**
* Se prefiere el uso de variables independientes del nombre de producto:
  - `MOSKV_DB_PATH`
  - `MOSKV_CACHE_DIR`
  - `MOSKV_CONFIG_DIR`
* Se evitará el uso de `CORTEX_*` y `BABYLON60_*` en producción para evitar migraciones secundarias con cada cambio de marketing.

### Nivel 5 — API Pública: **Namespaces Coexistentes**
* Durante la transición, coexistirán dos namespaces:
  - Nuevo: `babylon60.*`
  - Compatibilidad: `cortex.*` (emitirá avisos de deprecación hasta su retirada definitiva).

### Nivel 6 — Versionado: **Esquema Numérico**
* Las migraciones estructurales se controlarán mediante versiones explícitas (e.g., `Schema V1`, `Schema V2`, `Schema V3`) y nunca mediante cambios de nomenclatura de marca.

---

## Plan de Transición (Fases y Olas de Ejecución)

La migración técnica se estructurará en olas incrementales en lugar de una única operación masiva de búsqueda y reemplazo:

### Ola 1 — Preparación (Cero Cambios Funcionales)
* Crear el namespace/módulo vacío `babylon60/`.
* Mantener intacto `cortex/`.
* Añadir alias y adaptadores de compatibilidad.
* Incorporar pruebas unitarias de compatibilidad de imports.

### Ola 2 — Núcleo (Migración Interna)
* Migrar de forma controlada las capas más internas: `memory`, `ledger`, `storage`, `provenance` y `scheduler`.
* No alterar la API pública ni romper dependencias externas durante esta fase.

### Ola 3 — API Pública (Deprecación Activa)
* `import babylon60...` pasa a ser el namespace de documentación principal.
* `import cortex...` continúa funcionando de forma activa pero emite advertencias de deprecación (`DeprecationWarning`).

### Ola 4 — Ecosistema y Herramientas
* Actualización de interfaces CLI, documentación del repositorio, archivos de configuración (Docker, CI/CD, pyproject.toml, Cargo.toml), ejemplos de código y empaquetado.

### Ola 5 — Depuración y Purgado
* Eliminación definitiva del namespace `cortex` una vez que el 100% de la suite de tests pase, no existan dependencias del namespace antiguo y se publique una versión mayor del ecosistema (v2.0).

---

## Consecuencias

### Positivas
* **Aislamiento de Negocio:** El branding queda totalmente desacoplado del código fuente y los esquemas físicos.
* **Seguridad Operativa:** Minimiza el riesgo técnico de corrupción de base de datos o paradas en caliente al migrar de forma incremental.
* **Compatibilidad:** Mantiene la interoperabilidad con clientes históricos durante la transición.

### Negativas
* **Mantenimiento Temporal:** Requiere sostener y testear adaptadores y alias durante el periodo de coexistencia.
* **Política:** El branding nunca volverá a dictar directamente la estructura interna del runtime.
