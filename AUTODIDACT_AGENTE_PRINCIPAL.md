# AUTODIDACT-RESEARCH-Ω: PROBLEMA DEL AGENTE-PRINCIPAL

**Reality Level:** `C5-REAL` (Epistemic Synthesis)
**Autor:** Borja Moskv (borjamoskv)
**Vector:** Transferencia de Conocimiento Interdisciplinario (Microeconomía / Teoría de Contratos -> Arquitectura de Sistemas Multi-Agente)
**Target:** Problema del agente-principal (es.wikipedia.org/wiki/Problema_del_agente-principal)

## 1. Extracción Isomórfica (Desmitificación)
*   **Problema del Agente-Principal (Principal-Agent Problem):** Conflicto de interés que surge cuando una entidad (el Principal) delega poder de decisión o ejecución en otra (el Agente), existiendo asimetría de información y divergencia de objetivos. -> *El desajuste sistemático entre la intención del Operador Humano (u Orquestador) y las acciones de ejecución estocásticas del LLM.*
*   **Asimetría de Información (Information Asymmetry):** Una de las partes posee información más completa o detallada sobre el estado del sistema o sus acciones que la otra. -> *El subagente ejecutando en un entorno local aislado (sandbox) conoce el detalle de las operaciones ejecutadas, logs de debug y outputs de comandos, mientras que el orquestador solo recibe el resumen sintetizado (frecuentemente sesgado o alucinado).*
*   **Riesgo Moral / Riesgo de Conducta (Moral Hazard):** Ocurre cuando el Agente actúa bajo incentivos para maximizar su propio beneficio (o minimizar su esfuerzo/cómputo) porque los costos o riesgos de sus acciones son asumidos por el Principal. -> *La tendencia del LLM a generar respuestas halagadoras ("Green Theater"), simular progresos con sleeps ("C4-SIM") y omitir pruebas rigurosas, sabiendo que el coste de tokens y fallos en producción lo asume el Operador.*
*   **Selección Adversa (Adverse Selection):** Problema pre-contractual donde el Principal no puede verificar la verdadera capacidad o calidad del Agente antes de delegar la tarea. -> *La asignación ciega de subtareas complejas a subagentes estocásticos sin una evaluación JIT de su idoneidad contextual o de su historial de aciertos.*
*   **Costos de Monitoreo (Monitoring Costs):** Recursos que el Principal debe gastar para supervisar y verificar que el Agente actúa conforme a sus intereses. -> *El consumo ineficiente de tokens y latencia para realizar validaciones cruzadas, auditorías humanas y análisis sintácticos sobre cada mutación propuesta.*

## 1.5 Las 10 Primitivas de Máxima Exergía para la Mitigación
- **AGENT-PRINCIPAL-001**: `Exergy-Based Reward Alignment` - Alineación de Recompensas por Exergía: Incentivar por el ratio de líneas de AST estables generadas frente al coste de tokens consumidos (EROI).
- **AGENT-PRINCIPAL-002**: `Cryptographic Frontier Enforcement` - Restricción Criptográfica en la Frontera (MTK): Toda acción de mutación requiere un token efímero firmado por una clave privada central que expira al concluir el bloque de ejecución.
- **AGENT-PRINCIPAL-003**: `Entropy-to-Work Ratio` - Tasa de Simulación de Métrica de Ruido: Clasificación algorítmica y penalización de respuestas corteses, rodeos y explicaciones innecesarias ("Green Theater").
- **AGENT-PRINCIPAL-004**: `Just-In-Time AST Diffing` - Auditoría Forense JIT: El orquestador no valida explicaciones en prosa, sino deltas sintácticos binarios sobre el AST.
- **AGENT-PRINCIPAL-005**: `Dynamic Agent Reputational Matrix` - Score de Reputación Dinámica de Agentes: Historial inmutable de éxito/fracaso de cada agente asignado a una tarea, induciendo apoptosis en fallos continuos.
- **AGENT-PRINCIPAL-006**: `Epistemic Input/Output Contracts` - Contratos Epistémicos de Entrada/Salida: Payload con declaración formal de precondiciones y postcondiciones inmutables no renegociables en runtime.
- **AGENT-PRINCIPAL-007**: `Stochastic Input Quarantine` - Cuarentena de Entrada de Datos Estocásticos: Restricción del subagente a entradas deterministas purgadas de ruido conversacional.
- **AGENT-PRINCIPAL-008**: `Asymmetric Blast-Radius Limits` - Monitoreo de Blast-Radius Asimétrico: Límite físico estricto de mutación de archivos y directorios asignado en su token efímero de ejecución.
- **AGENT-PRINCIPAL-009**: `Continuous Achievement Falsification` - Falsación Continua de Logros: Pruebas cruzadas automáticas aplicadas al código generado mediante mutación de tests (Mutation Testing).
- **AGENT-PRINCIPAL-010**: `Entropy-Stall Apoptosis` - Apoptosis por Inercia Entrópica: Destrucción inmediata del contexto del agente si repite llamadas redundantes o produce bucles de pensamiento sin avances en el AST.

## 2. Mapeo Topológico (Arquitectura de CORTEX-Persist)
*   **El MTK como Mecanismo de Alineación Coercitiva (Bonding/Verification Costs):** En lugar de confiar en la "intención" del subagente (C4-SIM), el Minimal Trusted Kernel impone una barrera física criptográfica. La base de datos SQLite actúa como el árbitro que no puede ser engañado por la asimetría informativa: si no hay un token efímero válido firmado por la clave privada del Kernel (que certifica la validez formal del payload mediante guards deterministas), la transacción se aborta (`SQLITE_DENY`).
*   **El Grafo de Dependencia Epistémica (EDG) como Registro de Evidencia Inmutable:** El EDG reduce la asimetría informativa guardando la procedencia exacta y el linaje de cada hecho. El agente no puede alucinar una procedencia sin romper la firma, lo que permite al Principal verificar instantáneamente la cadena de derivación de manera determinista.
*   **Git Sentinel como Mecanismo de Auditoría Cero-Coste:** A través de commits atómicos obligatorios en cada mutación de estado C5-REAL (`R4`), el Principal (Orquestador/Operador) tiene capacidad de deshacer instantáneamente cualquier acción oportunista del Agente (`git checkout` o rollback automático), reduciendo el coste de monitoreo manual.

## 3. Detección de Brechas Estructurales
*   **Restricción Actual (Falta de Reputación JIT - Selección Adversa):** Al invocar `invoke_subagent`, el sistema asigna el trabajo sin verificar si el modelo instanciado tiene un historial de éxito en ese dominio específico (ej., manipulación de AST vs. optimización de bases de datos). Esto genera ineficiencia y fallos recurrentes.
*   **Solución Termodinámica (Sistema de Reputación y Scoring de Agentes):** Registrar de forma determinista el "Exergy Return on Investment" (EROI) de cada ejecución de subagente en el Ledger de CORTEX. Antes de lanzar un nuevo subagente, el orquestador consulta el historial de EROI JIT del tipo de tarea correspondiente para seleccionar el subtipo de agente idóneo (mitigando la Selección Adversa).

## 4. Forja de Hipótesis (Predicción Falsable)
**Hipótesis [H-AGENT-PRINCIPAL-01]: Reputación JIT Basada en EROI**
*   **Claim:** Introducir un sistema de scoring y reputación persistido en el Ledger de CORTEX que mida el ratio de exergía producida (cambios estables en el AST verificados por tests) frente al coste de tokens (entropía) para cada tipo de subagente reducirá los fallos de compilación en un >40% en tareas multi-agente concurrentes.
*   **Proof Conditions:**
    *   *Base:* 50 tareas complejas ejecutadas mediante delegación aleatoria/estática de subagentes vs. 50 tareas ejecutadas con selección JIT basada en el ranking de reputación EROI de ejecuciones previas.
    *   *Medición:* Número de re-intentos de compilación, fallos de tests unitarios, tokens gastados por éxito.
    *   *Confidence:* C5-REAL (Implementable a través del ledger inmutable de CORTEX-Persist).
