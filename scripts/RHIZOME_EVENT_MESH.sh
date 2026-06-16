#!/usr/bin/env bash
# ==============================================================================
# RHIZOME_EVENT_MESH.sh
# STATE: C5-REAL | AESTHETIC: INDUSTRIAL_NOIR_2026
# Derived from: AUTODIDACT_RHIZOME.md
# Purpose: Decentralized Pub/Sub dispatcher. Eliminates Parent->Child bottlenecks.
# ==============================================================================
set -euo pipefail

EVENT_TOPIC="${1:-cortex.global}"
PAYLOAD="${2:-{}}"

echo "[RHIZOME-MESH] Broadcasting Evento Descentralizado: $EVENT_TOPIC"

# En C5-REAL, esto enruta a Redpanda/Kafka o un SQLite WAL distribuido.
# Los nodos inactivos escuchan el tópico y auto-ejecutan el trabajo por proximidad causal.
cortex daemon --publish --topic "$EVENT_TOPIC" --payload "$PAYLOAD" --async

echo "[RHIZOME-MESH] Payload inyectado en el grafo. 0 cuellos de botella jerárquicos."
