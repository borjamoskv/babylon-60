# AUTODIDACT-RESEARCH-Ω: INFO-EXERGY (EXERGÍA DE LA INFORMACIÓN)

**Reality Level:** `C5-REAL` (Epistemic Synthesis)
**Vector:** Transferencia de Conocimiento Interdisciplinario (Teoría de la Información / Física Estadística -> Arquitectura de Contexto Agéntico)
**Target:** Exergía de la Información (es.wikipedia.org/wiki/Exergía / Principio de Landauer / Motor de Szilárd)

## 1. Extracción Isomórfica (Desmitificación)
*   **Exergía de la Información (Information Exergy):** El trabajo útil máximo que puede extraerse de un sistema gracias a poseer información sobre su microestado. -> *La densidad máxima de mutaciones de código ejecutables y verificaciones deterministas que se pueden extraer de un bloque de contexto o AST antes de que degrade en alucinaciones (entropía).*
*   **Motor de Szilárd (Szilard Engine):** Dispositivo conceptual que convierte un bit de información en trabajo mecánico útil. -> *El núcleo de confianza mínimo (MTK) de CORTEX-Persist, que convierte 1 bit de validación criptográfica (token efímero de mutación) en un commit determinista en la base de datos (trabajo físico).*
*   **Principio de Landauer (Landauer's Principle):** Disipación mínima inevitable de calor ($k_B T \ln 2$) al borrar un bit de información. -> *El coste computacional y de tokens asociado con purgar o compactar la memoria de contexto; limpiar el estado irrelevante requiere un consumo activo de operaciones y tokens de atención.*
*   **Baño Térmico Informativo (Information Thermal Bath):** Estado de máxima entropía del cual no se puede extraer ningún trabajo útil. -> *Las respuestas estocásticas no estructuradas (slop, saludos, rodeos discursivos de LLM) que consumen ventana de contexto sin aportar coherencia causal.*

## 2. Mapeo Topológico (Arquitectura de CORTEX-Persist)
*   **El MTK como Motor de Szilárd:** La base de datos SQLite rechaza físicamente cualquier escritura (`SQLITE_DENY`) a menos que exista un token efímero activo en el contexto. El MTK actúa como la compuerta de Szilárd: mide el estado epistémico (verifica la firma del payload de clausura) y, si es válido (1), abre la compuerta para permitir la transacción (trabajo).
*   **Compactación de Contexto Landaueriana (LEA-Ω):** Para mantener la exergía de la ventana de atención alta, LEA-Ω purga periódicamente los residuos informativos de la sesión (logs de debug temporales, trazas de errores resueltos, código muerto). El coste de esta purga se compensa al evitar la recomputación de prefijos y reducir la latencia de inferencia.
*   **Grafo de Dependencia Epistémica (EDG):** El EDG almacena hechos validados que actúan como "reservorios de exergía". Un hecho con alta conectividad y validez verificable puede generar múltiples afirmaciones derivadas (trabajo útil) sin necesidad de re-explorar o consultar modelos externos (evitando pérdida de energía computacional).

## 3. Detección de Brechas Estructurales
*   **Restricción Actual (Procesamiento Plano de Archivos):** CORTEX-Persist lee y pasa archivos completos (e.g., `builtin_tools.py`) al contexto del APEX, incluso cuando solo se requiere modificar un método específico. Esto es una ineficiencia termodinámica grave (exceso de entropía informativa), forzando al modelo a consumir exergy de atención en analizar boilerplate.
*   **Solución Termodinámica (Proyecciones AST de Alta Exergía):** Implementar un extractor AST JIT. En lugar de inyectar archivos planos de >500 líneas en el contexto, el sistema debe proyectar un esqueleto del archivo (clases, firmas de métodos y tipos) y solo expandir el cuerpo del bloque de código específico que se va a editar.

## 4. Forja de Hipótesis (Predicción Falsable)
**Hipótesis [H-INFO-EXERGY-01]: Proyecciones AST JIT**
*   **Claim:** Reemplazar la lectura de archivos planos completos por proyecciones AST dinámicas de alta exergía (firmas, tipos y el método objetivo exclusivamente) reducirá el consumo de tokens de entrada en un >55% sin degradar la tasa de éxito de la mutación ni generar errores de sintaxis o tipos.
*   **Proof Conditions:**
    *   *Base:* Ejecución de 20 tareas de refactorización estructural en archivos de gran tamaño (>300 líneas) usando lectura completa de archivos vs. proyecciones AST JIT.
    *   *Medición:* Consumo de tokens de contexto, tasa de builds fallidos/errores de linter, tiempo de respuesta (TTFT).
    *   *Confianza:* C5-REAL (Implementable de inmediato mediante `Python-Extractor-OMEGA`).
