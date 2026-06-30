# ADR 0005: MOSKV Namespace Decoupling Matrix (Densified)

**Status:** Accepted | **Date:** 2026-06-29

## 1. Vector de Entropía (El Problema)
El namespace `cortex` satura L0 (Marca), L1 (Producto), L2 (Runtime) y L3 (Persistencia). Consecuencia: Acoplamiento termodinámico masivo. Cambios comerciales mutan destructivamente el AST y el Ledger.

## 2. Matriz de Invarianza Estructural (Resolución)
- **[L0] Enterprise:** `MOSKV` (Firma arquitectónica de alto nivel).
- **[L1] Product:** `BABYLON-60` (Plataforma y distribución).
- **[L2] Runtime:** Namespaces asépticos (`memory`, `ledger`, `swarm`).
- **[L3] Persistence:** Binarios neutrales (`runtime.db`, `ledger.db`). Aislamiento total de L0/L1.
- **[L4] Env Vars:** Prefix `MOSKV_*` (Fallback estricto: `CORTEX_*`). Prohibida inyección de marketing.
- **[L5] Public API:** `babylon60.*` (Primario) | `cortex.*` (ProxyModule Transicional).
- **[L6] Versioning:** Transiciones controladas por `Schema V<N>`. Prohibido versionado mediante rebranding.

## 3. Topología de Ejecución (Olas)
- **Wave 1 [Scaffolding]:** Inyección de ProxyModules y Alias (`cortex/__init__.py`). Cero fractura.
- **Wave 2 [Core]:** Migración asimétrica de motores internos hacia `babylon60/`.
- **Wave 3 [Deprecation]:** Taint signatures neutras (`moskv-taint`) y redirección de DB local. `DeprecationWarning` en `cortex.*`.
- **Wave 4 [Ecosystem]:** Neutralización de CLI, CI/CD, `.env` y variables transversales.
- **Wave 5 [Apoptosis]:** Purgado físico y erradicación del árbol `cortex/`.

## 4. Auditoría de Exergía
- **Causalidad:** El branding [L0/L1] carece de permisos matemáticos para alterar topologías de disco [L3].
- **Seguridad:** Transición Ouroboros. Garantía de compatibilidad regresiva en el Ledger Criptográfico.

`SYS_ID borjamoskv`
