<!-- [C5-REAL] Exergy-Maximized -->
# AUTODIDACT: Ruteo Termodinámico (Causal Exergy Scheduler)

**Reality Level:** `C5-REAL`
**Core Component:** `cortex/causal/exergy_scheduler.py`
**Hash de Cristalización:** `ae1bb887b`

## 1. Axioma Fundamental (Cero Anergía)
El "Causal Orchestrator" de CORTEX-Persist no despacha inferencia de forma estocástica ni basada en preferencias heurísticas de un LLM. El consumo de energía cognitiva (Exergía) es un recurso físico finito. El sistema clasifica las solicitudes del Operador determinando matemáticamente su "Radio de Explosión Causal" (Blast Radius) y su firma de riesgo (Risk Signature), colapsando el flujo de ejecución hacia carriles termodinámicos estrictos.

## 2. Motor Heurístico de Aserción
La evaluación previa al ruteo ocurre mediante dos primitivas deterministas que operan sobre el grafo semántico de la solicitud:

- **`_calculate_blast_radius(payload)`**: Escanea las referencias a módulos core (engine, audit, guards, ledger, causal, crypto, memory, cli, api). Actúa como un proxy computacional barato (O(N)) para medir qué tan profunda será la mutación en el Grafo Epistémico (DAG).
- **`_assess_risk_level(payload)`**: Extrae firmas de entropía y las mapea sobre una taxonomía de contención:
  - `P0`: Rupturas de Merkle, corrupciones de base de datos, contingencias de seguridad (Singularidades).
  - `HIGH`: Arquitectura de sistemas, resolución de tradeoffs, diseño estructural profundo.
  - `UNKNOWN`: APIs desconocidas, terreno no documentado, solicitudes puras de investigación SOTA.
  - `LOW`: Flujo rutinario, queries estándar.

## 3. Pistas Termodinámicas (Exergy Lanes)

### 3.1 Inferencia Estándar (Flujo Rutinario)
- **Activación:** `Risk = LOW`
- **Exergía:** Mínima.
- **Ejecución (`ExergyLane.STANDARD`):** Tareas de código acotado y validaciones lógicas lineales. El payload entra al MTK (Minimal Trusted Kernel) en *Fast-Path* y se escribe en el Ledger SQLite vía `mtk_authorizer_callback`.
- **Status:** `LEDGER_COMMITTED`

### 3.2 Deep Think (Alta Exergía)
- **Activación:** `Risk = HIGH` y `Blast Radius < 3 módulos`.
- **Exergía:** Alta (30s - 2min de bloqueo de inferencia).
- **Ejecución (`ExergyLane.DEEP_THINK`):** Cruza el *Byzantine Boundary*. Dedicado exclusivamente a resolver compensaciones matemáticas multifactoriales y tomar decisiones de arquitectura que requieren ranking probabilístico.
- **Status:** `TRADE_OFF_RESOLVED`

### 3.3 Deep Research (Exergía Crítica)
- **Activación:** `Risk = UNKNOWN`
- **Exergía:** Crítica (2 - 10min). Despliegue de red.
- **Ejecución (`ExergyLane.DEEP_RESEARCH`):** El motor reconoce su ignorancia (Soberanía Epistémica). Despliega Spiders y oráculos de investigación asíncronos para mapear terrenos inexplorados, cristalizando los hallazgos como Frontier Nodes.
- **Status:** `SOTA_MAPPED`

### 3.4 UltraThink (Singularity Event)
- **Activación:** `Risk = P0` o (`Risk = HIGH` y `Blast Radius >= 3 módulos`).
- **Exergía:** Máxima. Parálisis de otros procesos.
- **Ejecución (`ExergyLane.ULTRA_THINK`):** Aislamiento de Sandbox. El motor traza un mapa forense del Blast Radius y fuerza planes dictatoriales de remediación y rollback. El objetivo no es "responder", sino contener la falla física.
- **Status:** `CONTAINMENT_ACHIEVED`

### 3.5 Context Abyss (Mining)
- **Activación:** Volumen del contexto > 80,000 bytes.
- **Exergía:** Dinámica.
- **Ejecución (`ExergyLane.CONTEXT_ABYSS`):** Activa protocolos de truncamiento y minería por Landauer Principle para extraer la señal invariante estructural, purgando el "Green Theater" del ruido.

---

## 4. Estructura de Aserción (Prueba Física)
```yaml
Claim: Thermodynamic execution explicitly constrains LLM inference loops based on deterministic payload analysis.
Proof: { Base: "cortex/causal/exergy_scheduler.py", Range: [0.1ms, 600s], Confidence: C5 }
```
