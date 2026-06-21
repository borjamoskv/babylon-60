# [C5-REAL] AXIOM 6: EPISTEMIC DAG ENFORCEMENT

> **"A Task without an Inference is arbitrary. An Inference without an Observation is hallucination."**

La ontología epistémica de CORTEX impone un Grafo Acíclico Dirigido (DAG) estricto para la cristalización de conocimiento y la mutación de estado.

## Estructura Causal Obligatoria

```text
[Observation] ──(causa)──> [Inference] ──(motiva)──> [Task]
```

## Invariantes Estructurales

1. **`Observation` (Primacy)**: Todo linaje epistémico DEBE originarse en una observación física y determinista (ej. un estado del AST, un código de error de SQLite, un hash criptográfico, la ausencia demostrable de una función).
2. **`Inference` (Causal Grounding)**: Una `Inference` DEBE referenciar explícitamente la `Observation` de la que se deriva. Las cadenas `Inference -> Inference` sin un nuevo anclaje en una `Observation` física están prohibidas para evitar la deriva estocástica (Context Rot).
3. **`Task` (Actionable Causality)**: Una `Task` (mutación propuesta sobre el sistema) DEBE depender de una `Inference` que explique *por qué* dicha intervención resuelve la tensión observada. La conexión directa `Observation -> Task` está prohibida, ya que omite la explicación causal.

## Mecanismo de Falsación
Cualquier intento de inyectar una `Task` en el sistema sin su correspondiente cadena de ascendencia (`Parent_ID` apuntando a una `Inference`, que a su vez apunta a una `Observation`) será interceptado y rechazado por el **Epistemic Validator**.
