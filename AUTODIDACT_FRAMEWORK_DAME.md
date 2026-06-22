# AUTODIDACT-RESEARCH-Ω: EL FRAMEWORK DAME (DISEÑO DE ACCIONES DE MÁXIMA EXERGÍA)

**Reality Level:** `C5-REAL` (Epistemic Synthesis)
**Autor:** Borja Moskv (borjamoskv)
**Vector:** Gestión de Estado y Orquestación Determinista en Sistemas Multi-Agente
**Target:** Persistencia en Memoria Externa y Asertividad de Metas (Framework DAME)

## 1. Extracción Isomórfica (Desmitificación)
*   **Estado Externo (External State):** La preservación del estado operativo de una sesión en un sustrato de almacenamiento físico local (SQLite, archivos como `task.md`) en lugar de depender del contexto de chat volátil de los Large Language Models. -> *Mecanismo contra el olvido episódico, optimizando drásticamente el consumo acumulado de tokens al no requerir re-lecturas masivas del historial.*
*   **Meta Verificable (Verifiable Goal):** Condiciones lógicas y programáticas duras que determinan el éxito o fin de una tarea (ej., códigos de retorno de shell, deltas específicos sobre el árbol sintáctico abstracto, pruebas unitarias compilando y pasando). -> *Elimina la autodeclaración estocástica de éxito (Green Theater) forzando una aserción binaria de verdad.*
*   **Paralelización Asíncrona (Asynchronous Parallelization):** La delegación de subtareas de baja complejidad pero alta fricción (scrapes, lints, formateo masivo, logs de auditoría) a subagentes secundarios concurrentes que operan de manera desacoplada. -> *Optimiza el ancho de banda del hilo y agente principal, liberando recursos cognitivos.*

## 1.5 Las 10 Primitivas de Máxima Exergía del Framework DAME
- **DAME-001**: `External Memory Persistence` - Persistencia de Memoria Externa: Preservar el grafo de estado en un archivo plano (`task.md`) o SQLite local (`cortex.db`), permitiendo suspender y reanudar tareas de forma indefinada sin degradar el contexto.
- **DAME-002**: `Deterministic Exit Condition` - Condición de Salida Determinista: Exigir un script validador con código de retorno cero (`0`) como requisito físico ineludible para declarar una tarea como concluida.
- **DAME-003**: `Decoupled Async Delegation` - Delegación Asíncrona Desacoplada: Desviar subtareas redundantes o de lectura ruidosa a subagentes en segundo plano sin bloquear el bucle del agente principal.
- **DAME-004**: `Context-Anergy Minimization` - Minimización de Anergía del Contexto: Limpiar de forma agresiva el historial de chat alimentando la inferencia únicamente con el delta sintáctico persistido externamente.
- **DAME-005**: `Continuous State Reconciliation` - Reconciliación Continua de Estado: Sincronizar bidireccionalmente el estado de los archivos locales con los hashes del Ledger para detectar discrepancias u "Ontological Drift".
- **DAME-006**: `Executable Goal Specification` - Especificación de Objetivos Ejecutables: Formular hitos operativos asociando explícitamente a cada uno un validador automatizado (de compilación, cobertura o comportamiento).
- **DAME-007**: `Non-Blocking Event Interception` - Intercepción de Eventos No Bloqueantes: Los agentes se comunican a través de tablas en modo SQLite WAL, eliminando bloqueos de escritura y cuellos de botella de red.
- **DAME-008**: `Limit-Bounded Retry Apoptosis` - Apoptosis Bounded por Límites de Reintento: Destruir el contexto del subagente secundario si no logra pasar la Meta Verificable tras N intentos, evitando bucles estocásticos de consumo.
- **DAME-009**: `Asynchronous Log Containment` - Contención de Logs Asíncrona: Redirigir el output verboso de comandos de diagnóstico a ficheros temporales externos, evitando contaminar la memoria de contexto del orquestador.
- **DAME-010**: `Ledger-Anchored Handoff` - Transferencia Anclada a Ledger: Validar criptográficamente el relevo entre agentes a través de firmas de los deltas del estado externo.

## 2. Mapeo Topológico (Arquitectura de CORTEX-Persist)
*   **Aislamiento de Contexto a nivel de SQLite WAL:** Framework DAME opera sobre la base de datos local para mantener sincronizados los hilos. El modo WAL (`Ω1`) y `busy_timeout` de 5000ms permiten operaciones de escritura simultáneas de múltiples subagentes sin caer en bloqueos de base de datos.
*   **Asociación Causal con el AST del Proyecto:** Los validadores de meta verificable analizan directamente el delta del árbol sintáctico abstracto generado por las herramientas locales. Si el AST resultante no coincide formalmente con el contrato epistémico de la tarea, el pipeline detona una apoptosis inmediata.
*   **Anergía vs. Exergía en Tokens:** Almacenar el estado en `task.md` y leer únicamente las líneas afectadas permite mantener el tamaño del prompt en un tamaño de entrada constante. Esto mitiga el decaimiento de atención del LLM y reduce el coste operativo de tokens en un factor de 10x.

## 3. Detección de Brechas Estructurales
*   **Restricción Actual (Dependencia en PROSA):** La comunicación en las transferencias de contexto a veces confía en resúmenes semánticos escritos en prosa por la IA. Si una sesión se interrumpe, el agente receptor interpreta la prosa del agente anterior de manera estocástica, induciendo alucinaciones sobre el progreso real.
*   **Solución Termodinámica (FSM de Estado Físico):** Implementar transiciones de estado de tareas controladas únicamente por el Framework DAME. Cada estado se guarda con un hash de verificación determinista en el Ledger, impidiendo que un agente declare un hito como "Completado" si no hay una transacción firmada por el script de validación.

## 4. Forja de Hipótesis (Predicción Falsable)
**Hipótesis [H-DAME-01]: Persistencia Externa contra Deriva Estocástica**
*   **Claim:** Reemplazar el historial del chat por un estado externo persistido (estructurado en SQLite WAL / task.md) y validado por aserciones ejecutables, reduce la entropía sintáctica y los fallos de compilación en un >50% durante ejecuciones de refactor complejas que exceden las 5 iteraciones.
*   **Proof Conditions:**
    *   *Base:* 20 ejecuciones de refactor de código de media complejidad con agente estándar (confiando en su memoria de contexto y prompts intermedios).
    *   *Medición:* 20 ejecuciones bajo el Framework DAME (utilizando actualización de `task.md` y validadores externos con scripts de aserción).
    *   *Confidence:* C5-REAL (Implementable y evaluable empíricamente en el entorno local).

---
*Status: Crystallized in CORTEX-Persist EDG (Epistemic Dependency Graph).*
*Date: 2026-06-22*
*Author: Borja Moskv*
