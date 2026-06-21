# [C5-REAL] AXIOM 6: EPISTEMIC DAG ENFORCEMENT

> **"A Task without an Inference is arbitrary. An Inference without an Observation is hallucination."**

La ontología epistémica de CORTEX impone un Grafo Acíclico Dirigido (DAG) estricto para la cristalización de conocimiento y la mutación de estado.

## Estructura Causal Formal

- **`Observation`**: Nodo raíz verificable derivado de evidencia física, determinista y reproducible (ej. un estado del AST, un código de error de SQLite, un hash criptográfico).
- **`Inference`**: Nodo derivado que debe poseer al menos un ancestro `Observation` alcanzable en el DAG.
- **`Task`**: Nodo de acción que debe poseer al menos un ancestro `Inference` alcanzable en el DAG.

## Validación Topológica

El **Epistemic Validator** evaluará las siguientes propiedades mecánicas sobre el DAG sin necesidad de interpretar semántica compleja:

### 1. Epistemic Reachability (Alcanzabilidad)
Existencia obligatoria de un camino dirigido hasta una evidencia física.
- `Observation`: `reachable_observation = self`
- `Inference`: `reachable_observation >= 1`
- `Task`: `reachable_observation >= 1` AND `reachable_inference >= 1`

### 2. Epistemic Depth (Profundidad Epistémica)
Distancia desde el anclaje físico. Cada salto inferencial incrementa el riesgo de error estocástico acumulado.
- `Observation`: `depth = 0`
- `Inference`: `depth(parent) + 1`
- `Task`: `max(parent_depth) + 1`

**Políticas de Tolerancia de Profundidad:**
- `depth > 5`: *Requires Review* (Alerta por derivación excesiva).
- `depth > 10`: *Requires Re-Observation* (Obligación de anclar el razonamiento a un nuevo experimento físico o `Observation`).

## Transiciones de Estado y Prohibiciones (Forbidden)

El sistema bloqueará las siguientes topologías:
1. `Task` o `Inference` que fallen la aserción de *Epistemic Reachability*.
2. Ciclos epistemológicos.
3. Autojustificación recursiva infinita.

## Corolario (Falsación Local y Propagación Mecánica)

Si una `Observation` fundacional (ej. `O1`) es invalidada o muta su estado, todos los nodos descendientes (tanto `Inference` como `Task`) en su sub-grafo `closure(descendants(O1))` se marcan de manera determinista y automática como `epistemically_stale`. Este mecanismo local previene la corrupción silente del conocimiento de dominio y no requiere intervención humana.
