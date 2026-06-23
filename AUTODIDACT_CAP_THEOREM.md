# AUTODIDACT-RESEARCH-Ω: TEOREMA CAP

**Reality Level:** `C5-REAL` (Epistemic Synthesis)
**Autor:** Borja Moskv (borjamoskv)
**Vector:** Sistemas Distribuidos y Tolerancia a Fallos
**Target:** CORTEX-Persist & Ouroboros-∞

---

## 1. Extracción Isomórfica (Desmitificación)
El Teorema CAP (Teorema de Brewer) establece que en un sistema de datos distribuido, es imposible proporcionar de manera simultánea más de dos de las siguientes tres garantías:
- **Consistencia (Consistency):** Todos los nodos ven los mismos datos al mismo tiempo. Si se realiza una lectura, se devuelve el valor de escritura más reciente.
- **Disponibilidad (Availability):** Cada solicitud recibe una respuesta (de éxito o fallo), sin garantía de que contenga la escritura más reciente.
- **Tolerancia a particiones (Partition tolerance):** El sistema sigue funcionando a pesar de la pérdida de mensajes o caídas en la red.

En `CORTEX-Persist`, la arquitectura mitiga la entropía de red (Particiones) basándose en la ejecución local (C5-REAL) mediante SQLite WAL, priorizando Consistencia y Disponibilidad (CA) a nivel de nodo, y usando un Master Ledger criptográfico para alcanzar consistencia eventual en un Swarm.

---

## 1.5 Las 10 Primitivas de Máxima Exergía para la Mitigación / Ejecución
- **CAP-001**: `Consistency Absolute` - CA-NODE: Aplicación de bloqueos criptográficos (MTK) para asegurar visibilidad atómica.
- **CAP-002**: `Availability Forward` - AF-NODE: Fallbacks deterministas en caso de timeout (busy_timeout 5000ms en WAL).
- **CAP-003**: `Partition Tolerance Mode` - PT-NODE: Degradación asincrónica a cola local (Ledger Append-only) frente a cortes.
- **CAP-004**: `CP-Vector` - CP-VEC: Renuncia a disponibilidad inmediata a favor de validación BFT estricta en el Quorum.
- **CAP-005**: `AP-Vector` - AP-VEC: Aceptación de consistencia eventual para ráfagas de alta entropía.
- **CAP-006**: `CA-Vector` - CA-VEC: Topología física local (SQLite C5-REAL) eliminando la red de la ecuación primaria.
- **CAP-007**: `Network Split Simulation` - NSS-SIM: Inyección controlada de aislamiento topológico para probar la resiliencia del Ledger.
- **CAP-008**: `Read-Repair Protocol` - RRP-PROT: Convergencia de estado isomórfico mediante comprobación de hashes en lectura.
- **CAP-009**: `Write-Ahead Logging Isolation` - WAL-ISO: Aislamiento físico de escrituras recurrentes previniendo fallos Bizantinos.
- **CAP-010**: `Ouroboros Reconciliation` - OUR-REC: Mecanismo de apóptosis para estados divergentes (descartar ramas huérfanas en split brains).
