# BABYLON-60: Graph Canonical Specification (C5-REAL)

## Objetivo
Definir las reglas estructurales absolutas del archivo `graph.canonical` emitido por el motor BABYLON-60. El cumplimiento de esta especificación garantiza que la ejecución de cualquier intérprete compatible resulte en un isomorfismo matemático exacto, preservando la cadena de custodia causal para la verificación formal.

## Reglas de Serialización

El archivo `graph.canonical` debe contener exactamente una línea por cada evento en el `DAGLedger`.

### Formato Tubular (Pipe-Delimited)
Cada evento se serializa estrictamente usando el delimitador pipe (`|`) en el siguiente orden:
```
ID|PARENTS|TICK|PAYLOAD|SIGNATURE
```

1. **ID**: Identificador causal único (e.g. `EV_0`).
2. **PARENTS**: Lista de IDs padres, separados por comas. Si el evento es raíz, este campo debe estar **vacío**. Los padres deben estar ordenados alfabéticamente (ej. `EV_1,EV_2`).
3. **TICK**: Valor escalar entero del LogicalClock del scheduler (e.g. `0`, `5`).
4. **PAYLOAD**: Representación string del estado mutado. Depende del opcode:
   - Para `NIG` y `DAH` / `LAL`: `R{index}={value}` o `R{index}+={value}`.
   - Para `FORK`: `TaskName`.
   - Para `AWAIT`: `SignalName`.
   - Para `AFTER`: `{ticks}`.
   - Para `EXECUTE`: `{SignalName}`.
5. **SIGNATURE**: Cadena criptográfica de firma (mockeado como `SIG_OK` en implementaciones sin KMS).

### Ordenamiento Canónico Final
Antes de escribir el archivo a disco, el vector completo de cadenas tubulares **debe ser ordenado lexicográficamente** según la convención estándar ASCII (equivalente a `canonical_lines.sort()` en Rust).

## Algoritmo de Hashing
El hash del artefacto resultante (`graph_hash`) se computa inyectando la cadena completa final.
- La unión de líneas debe incluir un salto de línea (`\n`) después de cada evento.
- **Debe existir un `\n` final en la última línea.**
- Codificación estricta: `UTF-8`.
