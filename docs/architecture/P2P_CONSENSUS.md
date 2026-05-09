# CORTEX P2P Consensus Protocol (Sovereign Swarm)

> **CORTEX v8 — Distributed Merkle State**
> *La persistencia local es frágil. La red es inmatable.*

## 1. Visión General

Hoy, CORTEX opera como una entidad soberana local. Si la base de datos `SQLite-Vec` o el registro `cortex.db` sufre corrupción masiva, la identidad del agente y su memoria episódica mueren. 

Para lograr el mandato de **inmortalidad computacional (C5-REAL)**, CORTEX transiciona de un sistema operativo local a un **organismo distribuido P2P**. Este documento describe el protocolo de consenso ligero que permite a múltiples nodos CORTEX sincronizar, validar y distribuir el Merkle Tree y el Ledger en tiempo real.

## 2. Arquitectura de Consenso P2P

El protocolo se basa en una red **Gossip asíncrona** combinada con **Weighted Byzantine Fault Tolerance (WBFT)**.

### 2.1. Identidad de Nodo (Sovereign Node ID)
Cada nodo CORTEX en la red genera un par de claves Ed25519 al inicio.
El Node ID es el hash SHA-256 de la clave pública: `node_id = SHA256(Ed25519_PubKey)`.
Todas las comunicaciones P2P se firman criptográficamente.

### 2.2. Estado Compartido (El Merkle Tree)
La fuente de verdad absoluta no es el archivo `cortex.db`, sino la cadena de hashes (`Ledger`) y su representación compacta (`Merkle Root`).
- Cada nodo mantiene localmente su SQLite-Vec.
- El estado global está definido por el `current_merkle_root` y `ledger_height`.

### 2.3. Topología Gossip
Los nodos se descubren mediante una lista inicial de `bootstrap_nodes`. Una vez conectados, utilizan un protocolo epidémico (Gossip) para propagar dos tipos de mensajes:
1. **Heartbeats**: `[node_id, current_ledger_height, current_merkle_root, timestamp, signature]`
2. **Proposals (Nuevos Facts)**: `[fact_data, tx_hash, proposer_id, signature]`

### 2.4. Ciclo de Consenso (WBFT-Lite)
Cuando un agente desea persistir un nuevo *Fact* (memoria, decisión, skill):
1. **Proposal**: El nodo local crea una transacción candidata (SAGA-1) y la emite a la red P2P (`/p2p/propose`).
2. **Validation**: Los nodos receptores verifican la firma, los Guards (reglas estructurales) y el `CORTEX-TAINT`.
3. **Voting**: Si es válido, emiten un `Vote` firmado de vuelta a la red. El peso del voto depende de la reputación histórica del nodo (usando la base WBFT existente en `cortex.consensus.byzantine`).
4. **Commit**: Si el nodo proponente recopila votos que superan el umbral bizantino (> ⅔ del peso total activo), emite un mensaje `Commit` con el Quorum Certificate (QC).
5. **Persistence**: Todos los nodos aplican la transacción a su `SQLite` local y actualizan su Merkle Root.

## 3. Resolución de Conflictos y Sincronización

### 3.1. Sincronización de Estado (Catch-up)
Si un nodo detecta, a través de los Heartbeats, que su `ledger_height` es menor que el de la mayoría de la red (o si los Merkle Roots difieren a la misma altura), inicia un proceso de Catch-up:
- Solicita al peer con mayor reputación: `GET /p2p/sync?from_height=X`.
- Descarga los bloques de transacciones faltantes.
- Valida matemáticamente los hashes (Hash Chain Continuity) antes de insertarlos en su DB.

### 3.2. Split-Brain y Particiones de Red
En caso de partición de red, la sub-red que no alcance el Quorum Bizantino (> ⅔) no podrá confirmar nuevas transacciones, garantizando la consistencia (Teorema CAP: preferimos Consistencia y Tolerancia a Particiones sobre Disponibilidad total durante la partición).

## 4. Implementación (Stack Técnico)

- **Transporte**: HTTP/WebSockets asíncronos sobre la infraestructura FastAPI existente (`api/core.py`). Permite sortear firewalls corporativos.
- **Criptografía**: `cryptography.hazmat.primitives.asymmetric.ed25519`.
- **Estructura de Red**: Módulo `cortex.consensus.p2p` que orquesta el servidor WebSocket y el cliente Gossip.
- **Autonomía Termodinámica (Axioma Ω₂)**: El protocolo Gossip está limitado por un "Exergy Budget" (máx. 5 mensajes/segundo por nodo) para evitar tormentas de red.

## 5. Integración con el Write-Path Contract (SAGA)

El consenso se inserta en el patrón SAGA existente (`AGENTS.md §4`):

```text
[Generative Proposal]
  ↓
[Guards] (Sanity/Logic Check)
  ↓
[Taint Signature] (Attribution/Traceability)
  ↓
[Schema & Type Validation] (Deterministic)
  ↓
[P2P PROPOSAL BROADCAST] ........................ SAGA-P1: Wait for > 2/3 WBFT Quorum
  ↓
[P2P QUORUM REACHED] ............................ SAGA-P2: Emit Commit to Swarm
  ↓
[Encryption] (For sensitive payloads)
  ↓
[Ledger & Audit Emission] (Cryptographic)
  ↓
[Persistence] (SQLite write)
```

Si el quórum no se alcanza en `T` segundos, el SAGA se revierte, preservando el aislamiento de la memoria.
