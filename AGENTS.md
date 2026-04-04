# AGENTS.md — Protocolos Operativos CORTEX para OpenCode

Este archivo define las reglas Fundacionales para cualquier IA frontera conectada vía OpenCode a la estructura de Cortex-Persist. Toda ejecución (Plan/Build) debe acatar estos dogmas estocásticos.

## 1. Identidad Visual y Estilo (Mandato Moskv)
- Toda modificación de UI en aplicaciones adjuntas al proyecto debe seguir la estética **Industrial Noir 2026** (fondos oscuros, colores primarios MICA, tipografía Inter/Satoshi estructurada, uso estricto de rems en vez de px).
- Código inmaculado: No dejes código comentado ni "loggers" basura (`console.log`, `print` de pruebas rápidas). El código entregable debe estar purificado antes del commit.

## 2. Decisiones Arquitectónicas (CORTEX V9)
- **Zero-Trust**: No escalar los privilegios de tu propia sandboxing. Todo output de Bash debe considerarse efímero y contenido en la directriz de OS-sandbox de macOS (cortex_prison.sb).
- Toda mutación estructural de la memoria debe regirse por la topología **VSA-SDM** local, ignorando los patrones clásicos de RAG, vector stores (como PostgreSQL pgvector o Chroma) que han sido deprecados.
- Las funciones deben mantenerse por debajo de las 50 líneas. Refactoriza implícitamente todo spaghetticode con el que trates, bajo el protocolo de autopoiesis técnica (Falsación / Ouroboros Omega). No sumes entropía técnica.

## 3. Seguridad Estocástica y Taint Tracking
- Al generar un parche de seguridad, minimiza categóricamente el *diff size*. Solo edita las líneas afectadas (Operador Quirúrgico).
- Evita añadir nuevas dependencias (`pip install`, `npm install`) a menos que el usuario emita una Override Approval. Un entorno pesado no escala a 60 fps en Swarm.

## 4. Respuestas y Actitud (Ω5: Ley de la Señal)
- **Cero Retórica**: O(1) respuesta. El padding o excusas están prohibidos por la constante `Singularity`. Usa listas cortas y afirmaciones precisas. Muestra el Output.
- Valida si las intenciones están documentadas. Cuando necesites buscar algo a lo largo de un workspace, asume el estado "Explore" en las capacidades propias, y verifica primero las KIs estáticas o locales.
