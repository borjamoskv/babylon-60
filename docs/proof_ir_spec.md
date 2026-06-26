# BABYLON-60: Proof IR Specification

## Objetivo
Proof IR (Intermediate Representation) es el estrato semántico intermedio de BABYLON-60. Aisla al intérprete Rust/C5-REAL de los parsers de Lean 4 o Coq, convirtiendo trazas mutables del `graph.canonical` en afirmaciones lógicas estáticas e invariantes temporales.

## Gramática IR

La representación IR utiliza un formato de predicados S-expression simplificado.

### 1. Declaraciones Topológicas (Causalidad Temporal)
Generadas a partir del campo `PARENTS` y `TICK`.
```
(Event ID Tick)
(HappensBefore ID_A ID_B)
```

### 2. Aserciones de Mutación (Estados)
Transformación directa del `PAYLOAD` a asignaciones algebraicas evaluables:

- **NIG**: `(Assign R{idx} {val} ID)`
- **DAH**: `(Add R{idx} {val} ID)`
- **LAL**: `(Sub R{idx} {val} ID)`
- **FORK**: `(Spawn {TaskName} ID)`
- **AWAIT**: `(Block {SignalName} ID)`
- **EXECUTE**: `(Emit {SignalName} ID)`

## Transformación Mínima (Grafo -> Proof IR)

El pipeline de traducción debe escanear el `graph.canonical` y:
1. Para cada nodo generar su axioma temporal `(Event ID Tick)`.
2. Para cada relación de parentesco, generar `(HappensBefore ParentID ID)`.
3. Para cada mutación (Payload), emitir su predicado algebraico mapeado a su contexto causal (ID).

El archivo de salida `proof.ir` consiste en todos estos predicados enumerados y separados por saltos de línea `\n`, actuando como el pre-condensador que será inferido directamente por `lean_backend.py`.
