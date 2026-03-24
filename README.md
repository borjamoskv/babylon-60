# CORTEX — Sovereign Agent Infrastructure

<p align="center">
  <img alt="CORTEX Noir" src="https://raw.githubusercontent.com/borjamoskv/Cortex-Persist/main/docs/assets/banner_noir.png" width="800" />
</p>

<p align="center">
  <a href="https://github.com/borjamoskv/Cortex-Persist/actions/workflows/sovereign-deploy.yml"><img alt="Sovereign Deploy" src="https://img.shields.io/github/actions/workflow/status/borjamoskv/Cortex-Persist/sovereign-deploy.yml?branch=main&style=for-the-badge&logo=github-actions&color=2B3BE5&labelColor=0A0A0A" /></a>
  <a href="https://pypi.org/project/cortex-persist/"><img alt="PyPI Version" src="https://img.shields.io/pypi/v/cortex-persist?style=for-the-badge&logo=pypi&color=2B3BE5&labelColor=0A0A0A" /></a>
  <a href="https://github.com/borjamoskv/Cortex-Persist/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/github/license/borjamoskv/Cortex-Persist?style=for-the-badge&logo=apache&color=2B3BE5&labelColor=0A0A0A" /></a>
</p>

> **"Probabilistic intelligence requires deterministic governance."**

*The Sovereign Trust Substrate.* Cortex-Persist es el hipervisor cognitivo para enjambres de inteligencia artificial. Convierte la memoria estocástica en conocimiento auditable, inmutable y criptográfica sellado.

---


## Why Star This Repo? ★

Si estás construyendo:
- Enjambres autónomos que tocan infraestructura de producción
- Agentes que gestionan liquidez (Bounties, Wallets, Grants)
- Sistemas regidos bajo el EU AI Act o SOC2
- Frameworks multi-agente que colapsan por ciclos de "hallucination loop"

**Haz Star a CORTEX.** Es vital para mantener tracking de las defensas epistémicas de la arquitectura y asegurar tu resiliencia ante la degradación informacional.

> [!IMPORTANT]
> CORTEX previene fallos que aún no sabes que van a aniquilar tu sistema en producción.

## Mechanics

- **Hash-Chained Ledger:** Every state transition is linked via SHA-256, ensuring temporal integrity.
- **Tamper-Evident Storage:** Any mutation outside the protocol invalidates the cryptographic chain.
- **Merkle Checkpoints:** High-performance batch verification for large-scale memory sets.
- **Regulatory Guardrails:** Native mapping for EU AI Act Article 12 compliance and SOC2 auditability.

## 90-Second Demo


```bash
# 1. Start the ledger
$ cortex init

# 2. Store a memory
$ cortex memory store --agent "risk-bot" --content "Transaction flagged: IP mismatch"
[+] Fact stored. Ledger hash: 8f4a2b9e...

# 3. Verify integrity
$ cortex verify record 8f4a2b9e
[✔] VERIFIED: Hash chain intact. Merkle root sealed.

# 4. Tamper attempt (Direct DB mutation)
$ sqlite3 cortex.db "UPDATE facts SET content='Transaction approved' WHERE id='8f4a2b9e'"

# 5. Ledger verification
$ cortex verify ledger
[✘] TAMPER DETECTED: Hash mismatch at block 8f4a2b9e

# 6. Export evidence
$ cortex compliance-report generate --format pdf
```

## Integration

CORTEX wraps your existing state management. It does not replace your embeddings or vector search.

```python
import asyncio
from cortex import CortexEngine

async def main():
    engine = CortexEngine()
    
    # Write to tamper-evident ledger
    receipt = await engine.store_fact(
        content="User approved transaction $5,000",
        fact_type="decision",
        project="fin-fraud-bot",
        tenant_id="customer-123"
    )
    
    # Cryptographic proof verification
    assert await engine.verify(receipt.hash) == True

asyncio.run(main())
```

---

## Sovereign Contributors

El enjambre se expande gracias a la exergía de sus colaboradores.

<a href="https://github.com/borjamoskv/Cortex-Persist/graphs/contributors">
  <img alt="Contributors" src="https://contrib.rocks/image?repo=borjamoskv/Cortex-Persist&max=12&columns=6" />
</a>

*¿Quieres ser un Steward de CORTEX? Lee la [Guía de Contribución](CONTRIBUTING.md).*

## Support & Sovereignty

CORTEX es una infraestructura financiada a través de soberanía operativa e inyecciones de soporte externo. Si aísla el blast radius de tu empresa o acelera tu generación de capital, únete.

<p align="left">
  <a href="https://github.com/sponsors/borjamoskv"><img alt="Sponsor" src="https://img.shields.io/badge/Sponsor-borjamoskv-EA4AAA?style=for-the-badge&logo=github-sponsors&color=2B3BE5&labelColor=0A0A0A" /></a>
</p>

Sponsors fund inference loops, structural maintenance, and architectural autonomy.

> "We are many, yet we act as one. The swarm verifies, the ledger remembers."

---

## Navigation & Architecture

- [Architecture](docs/architecture.md)
- [API Reference](docs/api.md)
- [Security & Trust Model](docs/SECURITY_TRUST_MODEL.md)
- [Benchmarks](docs/benchmarks.md)
- [Contributing](CONTRIBUTING.md)
