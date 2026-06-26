# BABYLON-60 Formal Specification (v2.5.1-C5-REAL)

> **C5-REAL Axiom:** El lenguaje no comunica; compila. Esta especificación formal define la semántica operacional, la máquina abstracta, las invariantes y el modelo de fallo de BABYLON-60, permitiendo que un asistente de pruebas (Lean 4 / Coq) razone sobre los artefactos exportados sin ambigüedad.

## 1. Abstract Machine (Máquina Abstracta)

El motor BABYLON-60 se define formalmente como la tupla:
`M = ⟨R, H, L, C, Q, T⟩`

Donde:
- `R` (Registers): Conjunto de registros locales por corrutina `R[0..N]`. Son puramente **inmutables** y sujetos a copy-on-write (COW) durante el paso de mensajes.
- `H` (Heap): Memoria compartida estructurada con **Linear Types**. Un recurso en el Heap solo puede tener un único dueño (corrutina) activo en un instante dado, eliminando data races.
- `L` (Ledger): Estructura de eventos inmutable y append-only, ordenada de forma causal.
- `C` (Clock): Reloj monotónico global discreto escalado en `UNIT.TICK` (Resolución Planck de 1ms).
- `Q` (Coroutine Queue): Cola de planificadores (Scheduler) de corrutinas en estados `{Ready, Waiting, Running, Completed, Halted}`.
- `T` (Trace Export): Acumulador de pruebas (Proof Harness) que captura snapshots deterministas tras transiciones observables.

## 2. Tipo Numérico `F60` y Memoria

### 2.1. Exactitud y Reducción
El tipo `F60` se refina matemáticamente para prevenir el "Blowup de Numerador":
`F60 = { Numerator: BigInt, Base60_Scale: u32 }`

**Operaciones:**
Toda operación aritmética debe aplicar reducción determinista mediante el máximo común divisor (`gcd`):
`reduce(N, S) = (N / gcd(N, 60^S), S - log_60(gcd(N, 60^S)))`

- **Desbordamiento Comprobable:** Si la memoria de `BigInt` excede un límite de cuota (ej. 256 bytes por escalar) para evitar ataques de agotamiento, se dispara la transición de fallo `CRITICAL_HALT`.

### 2.2. Modelo de Memoria
- **Inmutabilidad de Registros:** Ninguna instrucción muta un registro en su sitio. Toda evaluación genera un nuevo estado inmutable.
- **Copy-on-Write:** En operaciones `FORK`, la nueva corrutina hereda una vista superficial de `R` y `H`. La primera escritura clona el bloque.

## 3. Operational Semantics (Small-Step Semantics)

Se define el estado de una corrutina como `Γ = (PC, R, S)`.

### 3.1. Semántica del Control Asíncrono

**Regla de FORK:**
Bifurca la ejecución actual clonando el entorno estático sin afectar el tiempo causal.
```
Γ ⊢ FORK Label
-----------------------------
Q' = Q ∪ { (Label, R_cow, Ready) }
Γ' = (PC + 1, R, Running)
```

**Regla de AWAIT:**
Emite el evento y transiciona al estado `Waiting`. Solo se reactiva por el ACK causal en el Ledger.
```
Γ ⊢ AWAIT Symbol Label
-----------------------------
L' = L ∪ { (C.now(), Emitted(Symbol)) }
Γ' = (Label, R, Waiting(Symbol_ACK))
```

**Regla de AFTER:**
Suspende la corrutina explícitamente en el tiempo.
```
Γ ⊢ AFTER R_ticks Label
-----------------------------
Q' = Q ∪ { (Label, R, Waiting_Timer(C.now() + R_ticks)) }
Γ' = (-, R, Suspended)
```

## 4. Invariantes del Sistema (Proof Constraints)

Estas invariantes son formalmente comprobadas y cualquier violación dispara un aborto inmediato.

- **I1 (Unicidad Operacional):** Ninguna corrutina ejecuta más de una instrucción por `UNIT.TICK` escalar, o la misma corrutina no ejecuta dos veces concurrentemente.
- **I2 (Causalidad Única):** Cada evento del Ledger tiene un único productor (origen de firma criptográfica).
- **I3 (Inmutabilidad del Pasado):** El Ledger es estrictamente `append-only`. No existe el opcode de borrado.
- **I4 (Monotonía Temporal):** El reloj global `C` cumple: `C.now() <= C.next()`.
- **I5 (Ausencia de Anergía):** No existe estado mutable oculto (Hidden Mutable State). Toda mutación debe reflejarse en `R`, `H` o `L`.

## 5. Modelo de Fallo Formal

Cuando se detecta una condición de inestabilidad, fallo causal o violación de invariante (ej. Blowup en $F60$), la máquina NO intenta recuperarse o degradar precisión. Emplea la siguiente cadena de aserción estricta:

```
[ CRITICAL HALT ] -> [ CAUSAL SNAPSHOT ] -> [ ARTIFACT EXPORT ] -> [ ABORT PROCESS ]
```

1. **HALT:** Se suspende el despachador de la corrutina infractora. Ningún estado posterior es mutado.
2. **SNAPSHOT:** Se extrae un hash criptográfico inmutable de `R`, `H`, y `L` en el `UNIT.TICK` actual.
3. **EXPORT:** El Snapshot se transforma al esquema JSON/Lean4 formal dictado en `export_schema.json`.
4. **ABORT:** Terminación segura de la máquina virtual (M).
