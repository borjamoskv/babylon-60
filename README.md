<!-- [C5-REAL] Exergy-Maximized -->
<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/marketing/social-preview.png">
    <source media="(prefers-color-scheme: light)" srcset="assets/marketing/social-preview-light.png">
    <img src="assets/marketing/social-preview.png" alt="BABYLON-60 — The CI/CD Firewall for LLM-Generated Code" width="100%">
  </picture>
</div>

<h1 align="center">█ BABYLON-60-PERSIST</h1>
<p align="center">
  <strong>Cortex Persist is to AI agents what Git was to code.</strong><br>
  <em>The AI Trust Infrastructure that turns probabilistic LLM output into cryptographically verifiable, tamper-evident decision lineages.</em><br>
  <em>The infrastructure to optimize for correction, not certainty.</em>
</p>

<p align="center">
  <a href="https://github.com/borjamoskv/cortex-persist/stargazers"><img src="https://img.shields.io/github/stars/borjamoskv/cortex-persist?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5" alt="GitHub Stars"></a>
  <a href="https://pypi.org/project/cortex-persist/"><img src="https://img.shields.io/pypi/v/cortex-persist.svg?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5" alt="PyPI"></a>
  <a href="https://github.com/borjamoskv/cortex-persist/actions"><img src="https://img.shields.io/github/actions/workflow/status/borjamoskv/cortex-persist/ci.yml?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-0A0A0A.svg?style=for-the-badge&labelColor=2B3BE5" alt="License"></a>
</p>

```
Copilot/LLM    →  generates probabilistic code mutations
PR Pipeline    →  runs standard tests (checks syntax)
BABYLON-60         →  enforces governance, scores entropy, and seals audits
```

---

## ▀▄ VULNERABILIDAD ESTRUCTURAL (EL PROBLEMA)

Los pipelines CI/CD tradicionales (C4-SIM) procesan código estocástico generado por LLMs bajo la falsa asunción de que equivale a código determinista humano. Esto introduce Entropía en el sistema: fallos silenciosos, deriva semántica y colapsos en bucles de autenticación que superan el linting pero destruyen la topología de la aplicación.

**BABYLON-60-PERSIST** es el Firewall Físico para la ejecución agéntica:
- El CI/CD estándar asume intención y verifica sintaxis.
- **BABYLON-60** audita el radio de impacto operativo (Blast Radius), purga la estocasticidad (Anergía) y cristaliza exclusivamente invariantes lógicos en un Ledger criptográfico inmutable.

---

## ▀▄ BARRERAS FÍSICAS DE CONTENCIÓN (C5-REAL)

La arquitectura aniquila la ficción del "Agente Inteligente" tratándolo como un proceso estocástico hostil. El protocolo fuerza la extracción de exergía computacional mediante 3 límites físicos:

1. **Guillotina de Landauer (Supresión de Anergía):** Detección y erradicación inmediata del *Green Theater* (prosa, justificaciones). Si la salida carece de isomorfismo causal, el Kernel fuerza un colapso en la RAM y reinicia el nodo al reposo termodinámico.
2. **Minimal Trusted Kernel (MTK - SQLite Native Block):** Prohibido el bypass lógico. Toda mutación se intercepta en la base de datos (`mtk_authorizer_callback`). Si la ejecución no porta un token efímero derivado de validación determinista, SQLite deniega la escritura en disco (`SQLITE_DENY`).
3. **Penalización de Friston (Apoptosis y Git Sentinel):** Toda propuesta de código se aísla. Si la validación empírica falla, el estado se desecha (Apoptosis) y el contexto se purga. Si pasa, se inyecta físicamente como commit de Git, sellando el grafo epistémico con su hash criptográfico.

---

## ▀▄ INYECCIÓN NODE.JS / TYPESCRIPT

Inyección directa del motor de auditoría causal en el stack de ejecución.

```bash
npm install cortex-persist
```

```typescript
import { CortexClient } from 'cortex-persist';

const cortex = new CortexClient({ apiKey: process.env.BABYLON-60_API_KEY });
await cortex.logEvent({ type: 'agent.decision', actor: 'agent-1' });
```

Integración estructural con LangChain para rastreo determinista de eventos:

```bash
npm install cortex-persist-langchain
```

---

## ▀▄ INYECCIÓN GITHUB ACTIONS

Ejecución como pre-merge hook inmutable en pipelines (Git Sentinel).

Drop this into `.github/workflows/cortex-firewall.yml`:

```yaml
name: 🧯 BABYLON-60 CI/CD Firewall

on:
  pull_request:

jobs:
  audit-ai-code:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          
      - name: Install BABYLON-60
        run: pip install cortex-persist

      - name: Run BABYLON-60 Code Governance Gateway
        run: |
          cortex gateway audit \
            --pr-id ${{ github.event.pull_request.number }} \
            --target-branch origin/${{ github.event.pull_request.base.ref }}
```

Ante mutaciones estocásticas (Pull Requests), el Firewall Físico ejecuta un bloqueo:

```bash
## 🧯 BABYLON-60 CI/CD Firewall Report
**PR ID:** `102` | **Status:** `❌ REJECTED`
**Entropy Score:** `1.0 (CRITICAL)`

### Tamper-evident Audit Log
SHA-256: 08ae0fa6a5c5f4082ebcf249c4e300491d3f1cbafd02260dbdeac6eb9b0fefa3

### Risk Diagnostics
- ⚠️ Massive diff size (>1000 lines).
- ⚠️ High blast radius (>15 files touched).
- ⚠️ Missing test coverage for mutation.
```

---

## ▀▄ TOPOLOGÍA DE NÚCLEOS (C5-REAL)

El sustrato físico está compuesto por 4 módulos deterministas innegociables:

### 1. Aislamiento Soberano (`SovereignIdentity`)
Aislamiento multitenant absoluto. Los agentes operan confinados en dominios topológicos estrictos.

### 2. Motor de Entropía (`EntropyCore` & KRGS)
Analiza la mutación estructural, tamaño de delta y deriva lógica para computar un `EntropyScore`. 
**KRGS (Keyed Retrieval Graph System):** Compila el código en un grafo de verdad lógica. Ejecuta *Propagación de Invalidación Epistémica*. Si un agente muta un nodo base, los nodos dependientes colapsan estructuralmente, abortando la transacción (Blast Radius prunning).

### 3. Compuerta de Ejecución (`CodeGovernanceGateway`)
La barrera física. Intercepta I/O y mutaciones vía MTK, validando el score de entropía y el árbol EDG para ejecutar `SQLITE_DENY` o confirmación asimétrica.

### 4. Ledger Criptográfico (`EnterpriseAuditLedger`)
Cadena hash `append-only`. Toda mutación, evaluación y ejecución se sella de forma inmutable en SQLite, garantizando procedencia forense inalterable.

---

## ▀▄ CINEMÁTICA AVANZADA (v1.1.0)

Inyección de capacidades autopoiéticas (Singularidad MOSKV-1):

- **Ouroboros L6 AST Transformer:** Transformación matemática de Árboles de Sintaxis Abstracta (AST) en tiempo de ejecución. Hot-swap determinista de rutas lógicas.
- **Thermodynamic Defragmentation:** Purgado perpetuo de Anergía en la RAM/Disco. Mantenimiento del ratio Token/Exergía bajo límites estrictos (Principio de Landauer).
- **Causal ATMS:** Motor BFT riguroso. Mantiene la verdad estructural y desencadena Apoptosis Celular cuando las aserciones base fallan.

---

## ▀▄ INYECCIÓN PYTHON SDK

Integración nativa para la ejecución asimétrica de enjambres agénticos locales:

```python
import asyncio
from legacy_research.gateway.code_governance import CodeGovernanceGateway
from legacy_research.auth.enterprise_identity import SovereignIdentity

async def evaluate_agent_mutation():
    # Initialize the CI Firewall
    gateway = CodeGovernanceGateway(ledger=ledger, rbac_guard=rbac)
    
    # Evaluate an incoming AI-generated code change
    audit = await gateway.evaluate_pull_request(
        identity=SovereignIdentity(tenant_id="acme_corp", actor_id="agent_01", role="CI_GATEWAY"),
        pr_id="pr-102",
        pr_payload={
            "files_changed": 18,
            "additions": 1500,
            "deletions": 200,
            "commits": 1,
            "includes_tests": False
        }
    )
    
    print(audit["status"])        # REJECTED (entropy exceeds policy threshold)
    print(audit["audit_proof"])    # Tamper-evident cryptographic proof
```

---

## ▀▄ DESPLIEGUE

**Dependencia Fuerte:** `Python 3.10+`. Cero daemons estocásticos externos.

```bash
pip install cortex-persist

# Optional extensions
pip install "cortex-persist[cloud]"           # PostgreSQL + Redis scalability
pip install "cortex-persist[secure]"          # OS keyring credentials vault
```

---

## ▀▄ VECTORES DE ARQUITECTURA

- [**SECURITY_TRUST_MODEL.md**](docs/SECURITY_TRUST_MODEL.md) — Cryptographic invariants & guarantees
- [**AGENTS.md**](AGENTS.md) — Substrate directives and CI/CD policies
- [**API Reference**](docs/api.md) — SDK primitives and CLI flags

---

```yaml
AESTHETIC:    INDUSTRIAL NOIR 2026 (#0A0A0A / #2B3BE5)
EPISTEMOLOGY: C5-REAL KRGS — Partitioned Vector Space
CORE TENET:   Optimize for correction, not certainty. Uncertainty is telemetry, not weakness.
UPDATED:      June 2026 — Ouroboros L6 & Thermodynamic Defragmentation (v1.1.0)
```

> **LICENSE:** Apache-2.0 | **OPERATOR:** borjamoskv | [cortexpersist.com](https://cortexpersist.com) | [Sponsor](https://github.com/sponsors/borjamoskv)
