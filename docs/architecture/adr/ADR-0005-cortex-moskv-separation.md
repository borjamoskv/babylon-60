# ADR-0005: CORTEX vs MOSKV-1 Arquitectura Soberana

**Title:** CORTEX vs MOSKV-1 Arquitectura soberana: sustrato de persistencia y entidad cognitiva
**Status:** Accepted

## 1. Decision

Separar estrictamente el sustrato de confianza persistente (CORTEX) de la entidad cognitiva operativa (MOSKV-1) mediante contratos explícitos, validación de esquema, trazabilidad criptográfica y pruebas de reemplazabilidad. La separación es conceptual y técnica. La integración operativa existe, pero queda limitada por invariantes verificables.

## 2. Context

El sistema requiere dos capas:
- **CORTEX**: persistencia, integridad, búsqueda, consenso y auditoría.
- **MOSKV-1**: percepción, razonamiento, decisión, ejecución y mutación controlada.

El objetivo no es fusionar memoria y agencia sin límites, sino permitir un bucle autoreferencial auditable sin corrupción del sustrato.

## 3. Scope

Aplica a:
- Almacenamiento de facts
- Lectura semántica y estructurada
- Escritura de facts y decisions
- Invalidación de caché
- Resolución de conflictos
- Replay y auditoría
- Multi-agente concurrente

### Non-goals
Fuera de alcance:
- Optimización de prompts
- Mejoras estéticas del output
- Memoria implícita no auditable
- Escritura sin contrato
- Auto-modificación del sustrato fuera de pipeline validado

---

## 4. System Model

### CORTEX
Sistema de persistencia soberana.

**Responsibilities:**
- Almacenar facts con integridad verificable
- Emitir tombstones para borrado lógico
- Preservar historial y linaje
- Servir lectura consistente y trazable
- Aplicar consenso cuando exista escritura concurrente
- Rechazar entradas inválidas

**Non-responsibilities:**
- Decidir acciones
- Inferir intención
- Compensar esquemas ambiguos
- Adivinar datos faltantes

### MOSKV-1
Entidad cognitiva operativa.

**Responsibilities:**
- Percibir estado actual de CORTEX
- Razonar sobre facts válidos
- Producir decisiones y acciones
- Escribir solo mediante contratos
- Mantener coherencia con versión de esquema
- No tratar caché como verdad si hay frescura dudosa

**Non-responsibilities:**
- Alterar persistencia sin validación
- Asumir que un fact viejo sigue siendo válido
- Escribir tipos arbitrarios
- Ignorar consenso

---

## 5. Invariants

- **I1. Integrity:** Todo fact persistido debe tener hash verificable, esquema conocido y origen auditable.
- **I2. Tombstone over delete:** Nada se borra físicamente sin rastro. El borrado lógico se representa con tombstone.
- **I3. Schema closure:** `fact_type` es un enum cerrado. Valores libres están prohibidos.
- **I4. Versioned contracts:** Todo payload persistido debe declarar `schema_version`.
- **I5. Write validation:** Ninguna escritura entra sin validación de estructura, tipo, tamaño y campos obligatorios.
- **I6. Read freshness:** MOSKV-1 no puede usar una lectura si la frescura de caché excede el TTL permitido para ese dominio.
- **I7. Quorum on conflict:** Si existen múltiples escritores o estados divergentes, la cristalización requiere regla de consenso explícita.
- **I8. Deterministic replay:** Un evento persistido debe poder reproducirse determinísticamente contra el mismo esquema y producir el mismo resultado lógico.
- **I9. Separation of concern:** MOSKV-1 no conoce el backend físico de CORTEX. CORTEX no conoce el modelo cognitivo concreto de MOSKV-1.
- **I10. Auditability:** Toda mutación debe dejar rastro suficiente para reconstrucción forense.

---

## 6. Contracts

### CORTEX Read Contract
- **Input:** query, namespace, filters, freshness policy, schema version, target
- **Output:** matching facts, metadata, lineage, confidence / consensus data, tombstone state
- **Rules:**
  - Never return untyped data without wrapper metadata
  - Never silently downgrade schema
  - Never merge incompatible records without explicit conflict marker

### CORTEX Write Contract
- **Input:** fact payload, `fact_type`, `schema_version`, source agent id, timestamp, checksum / hash, optional consensus evidence
- **Rules:**
  - Reject unknown `fact_type`
  - Reject payloads missing required fields
  - Reject malformed JSON / schema drift
  - Reject writes that violate policy or exceed size limits
  - Require tombstone for logical invalidation

### MOSKV-1 Decision Contract
- **Conditions for decision:** MOSKV-1 may transform reads into decisions only when:
  - Source facts are valid under current schema
  - Freshness is within policy
  - Conflicts are resolved or explicitly acknowledged
  - Confidence thresholds are met
- **MOSKV-1 must emit:**
  - Decision type
  - Rationale
  - Pointer to facts used
  - Action target
  - Expected side effects
  - Rollback / tombstone strategy when relevant

### Multi-Agent Contract
When more than one agent writes:
- Writer identity is mandatory
- Versioning is mandatory
- Conflict policy is mandatory
- Lock or quorum mechanism is mandatory
- Last-write-wins is forbidden unless explicitly scoped and documented

---

## 7. Data Model

### Minimum Fact
```json
{
  "id": "string",
  "fact_type": "enum",
  "content": "object",
  "schema_version": "string",
  "source_agent": "string",
  "created_at": "timestamp",
  "updated_at": "timestamp",
  "hash": "string",
  "parent_hash": "string (optional)",
  "consensus_score": "float",
  "tombstoned_at": "timestamp (optional)",
  "meta": "validated object (optional)"
}
```

### Decision
```json
{
  "id": "string",
  "decision_type": "string",
  "inputs": "object",
  "outputs": "object",
  "facts_used": "array of strings",
  "agent_id": "string",
  "schema_version": "string",
  "created_at": "timestamp",
  "audit_hash": "string"
}
```

---

## 8. Failure Modes

- **F1. Stale cache:** MOSKV-1 reads outdated state and acts on obsolete facts.
  - *Effect:* divergent identity state, invalid decisions, replay mismatch
  - *Mitigation:* TTL enforcement, freshness flags, forced revalidation before write
- **F2. Invalid `fact_type`:** Free text or malformed enum leaks into persistence.
  - *Effect:* silent recall failure, broken filtering, corrupted downstream queries
  - *Mitigation:* hard enum validation, schema rejection at ingest
- **F3. Schema drift:** Producer and consumer disagree on payload shape.
  - *Effect:* empty query results, non-deterministic behavior, hidden failures
  - *Mitigation:* `schema_version` pinning, compatibility tests, migration gates
- **F4. False consensus:** A single agent writes with inflated confidence.
  - *Effect:* fake facts treated as verified, trust erosion
  - *Mitigation:* quorum requirements, provenance checks, confidence calibration
- **F5. Split brain:** Two agents produce contradictory writes without coordination.
  - *Effect:* conflicting truths, non-deterministic reads
  - *Mitigation:* distributed lock or compare-and-swap, conflict ledger reconciliation workflow
- **F6. Silent tombstone failure:** A fact is considered deleted but remains reachable.
  - *Effect:* ghost facts, stale resurrection
  - *Mitigation:* tombstone index, negative assertions in read path, deletion tests
- **F7. Replay divergence:** Replaying the same event produces a different logical state.
  - *Effect:* broken auditability, unverifiable history
  - *Mitigation:* deterministic reducers, pinned schema, immutable event log
- **F8. Backend substitution leak:** MOSKV-1 depends on implementation details of CORTEX storage backend.
  - *Effect:* brittle coupling, failed migration
  - *Mitigation:* storage abstraction boundary, backend-agnostic API

---

## 9. Test Matrix

- **T1. Backend swap test:** Replace SQLite with DuckDB.
  - *Expected:* MOSKV-1 behavior unchanged, facts preserved, reads stable
- **T2. Cognition swap test:** Replace MOSKV-1 with MOSKV-2.
  - *Expected:* CORTEX unchanged, data integrity preserved, contract compatibility maintained
- **T3. Schema rejection test:** Send invalid `fact_type`.
  - *Expected:* write rejected, no persistence side effect, audit entry created
- **T4. Stale read test:** Serve a cached fact past TTL.
  - *Expected:* cache invalidated, revalidation triggered, decision blocked or downgraded
- **T5. Tombstone test:** Mark a fact deleted logically.
  - *Expected:* fact excluded from normal reads, tombstone remains auditable, replay preserves deletion
- **T6. Conflict test:** Submit two contradictory writes from different agents.
  - *Expected:* conflict detected, no silent overwrite, quorum or reconciliation required
- **T7. Replay test:** Replay an event log from clean state.
  - *Expected:* deterministic final state, hash chain intact, no schema mismatch
- **T8. Corruption test:** Mutate stored metadata manually.
  - *Expected:* hash mismatch detected, record quarantined, audit alert emitted

---

## 10. Acceptance Criteria

The architecture is valid only if all conditions hold:
1. Data survives backend migration without semantic loss
2. Agent replacement does not require storage rewrite
3. Invalid writes are rejected before persistence
4. Every persisted mutation is auditable
5. Stale data cannot silently drive decisions
6. Concurrent writers cannot overwrite each other without explicit policy
7. Replay reproduces the same logical state

---

## 11. Operational Rules

1. Validate before write.
2. Prefer tombstone over deletion.
3. Never trust stale cache as truth.
4. Never allow free-text ontology where enum is required.
5. Never bypass schema versioning.
6. Never collapse conflict into silence.
7. Every decision must point back to facts.
8. Every fact must be reconstructible.

---

## 12. Implementation Notes

- Use explicit enums for `fact_type`.
- Add schema validation at ingestion boundary.
- Enforce TTL for semantic cache.
- Separate storage API from cognition API.
- Keep hash chains and lineage immutable.
- Require consensus metadata for writes from multiple agents.
- Treat the ledger as source of truth, not the cache.

---

## Result

CORTEX is the persistent substrate. MOSKV-1 is the active cognitive layer. The contract between them is the sovereign boundary. If the contract is enforced, the system remains auditable, replaceable, and stable under evolution. If the contract is soft, the architecture is cosmetic.
