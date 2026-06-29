<!-- [C5-REAL] Exergy-Maximized -->
# CEP-001: Core Kernel Contracts

* **Id:** CEP-001
* **Título:** Contratos Mínimos del Núcleo e Invariantes Epistémicos
* **Estado:** Borrador (Draft)
* **Autor:** CORTEX Architecture Group
* **Fecha:** Junio 2026

## 1. Principio Fundamental de Diseño
La arquitectura CORTEX se rige por el siguiente invariante de ciclo de vida: Las interfaces deben estabilizarse antes que los algoritmos que las implementan. El éxito técnico del núcleo consiste en que la evolución del conocimiento (nuevas teorías de confianza, motores de inferencia o solvers) no implique la evolución ni la reescritura de la arquitectura.

## 2. El ABI Conceptual: Jerarquía de Tipos de EpistemicObject
Toda entidad que transite por el núcleo de CORTEX debe heredar de la interfaz abstracta `EpistemicObject`. Se define la siguiente jerarquía inicial, donde cada tipo posee identidad única, inmutabilidad estructural y contratos de serialización verificables.

```text
EpistemicObject (Abstracto: ID único + Hash criptográfico de estructura)
│
├── Assertion      (Declaración atómica o hecho sobre el dominio)
├── Evidence       (Artefacto verificable que soporta o refuta una Assertion)
├── Inference      (Mecanismo lógico o probabilístico que vincula objetos)
├── Diagnostic     (Metadato sobre la salud, contradicciones o lagunas del estado)
├── Constraint     (Invariante lógico o límite del sistema)
├── Provenance     (Atribución, autoría, marcas temporales y origen del objeto)
└── EpistemicState (Grafo acíclico dirigido que consolida los objetos anteriores)
```

## 3. Especificación del Contrato de EpistemicState
El `EpistemicState` es el objeto mínimo y contenedor de la verdad parcial del sistema. Sus propiedades operativas son:

### Campos Obligatorios e Inmutables
* `id`: Identificador global único (UUIDv7 o URI determinista).
* `root_hash`: Hash criptográfico (SHA3-256) generado a partir del contenido de su grafo interno. Cualquier alteración de sus componentes invalida el estado.
* `provenance`: Puntero obligatorio a un objeto `Provenance` que declare explícitamente el origen de la transición.
* `payload`: Conjunto indexado de `Assertions`, `Evidence` e `Inferences`.

### Invariantes y Reglas de Transición
1. **Inmutabilidad por Diseño:** Un `EpistemicState` no se modifica. Cualquier actualización genera un nuevo `EpistemicState` con un nuevo hash y una referencia al estado predecesor.
2. **Direccionalidad:** Las transiciones forman un Grafo Acíclico Dirigido (DAG) de estados históricos. No se permiten ciclos en la evolución temporal de la información.
3. **Preservación de Auditoría:** Ninguna transición de estado puede purgar los objetos de procedencia previos; el linaje completo debe ser reconstruible de extremo a extremo.

### Violaciones del Contrato (Panic Conditions)
El núcleo del kernel abortará la ejecución o rechazará el estado si se detecta:
* Un `EpistemicState` sin metadatos de procedencia explícitos.
* Discrepancia entre el `root_hash` y la evaluación estructural de sus componentes.
* Una transición de estado que modifique un objeto indexado en un estado previo sin generar un nuevo nodo en el DAG.

## 4. Flujo de Transición de Estado (Epistemic Saga)
La transición de `EpistemicState_N` a `EpistemicState_{N+1}` no es una mutación en memoria; es una función pura validada criptográficamente. El Kernel orquesta la transición mediante el siguiente contrato (alineado con la regla Write-Path de CORTEX):

1. **Ingesta de Delta ($\Delta$):** El Kernel recibe una propuesta que contiene nuevos `EpistemicObjects` (`Assertion`, `Evidence`, `Inference`).
2. **Auditoría de Invariantes (SAGA-1):** 
   - Verificar que todos los objetos en $\Delta$ heredan correctamente de `EpistemicObject` y poseen un hash válido.
   - Rechazar si se detecta Auto-Referencia probatoria (MI-001).
3. **Validación Topológica (SAGA-2):** 
   - Proyectar virtualmente el nuevo estado $N+1$ acoplando $\Delta$ a $N$.
   - Ejecutar análisis de ciclos en el Grafo de Procedencia. Si se detecta un ciclo, abortar la transición.
4. **Acoplamiento de Taint (SAGA-3):**
   - El `Taint Engine` sella criptográficamente cada nuevo objeto en $\Delta$ con su origen absoluto (Token de Atribución).
5. **Cristalización (SAGA-4):**
   - Calcular el nuevo `root_hash` del `EpistemicState_{N+1}` (Cadena de Merkle dependiente del estado previo).
6. **Persistencia Atómica (SAGA-5):**
   - Emitir la transición al Master Ledger (SQLite WAL en CORTEX-Persist). La verdad parcial avanza.
