🌐 [English](README.md) | **Español** | [中文](README.zh.md)

# CORTEX Persist

**Integridad criptográfica de memoria, pistas de auditoría y linaje verificable para agentes de IA.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/borjamoskv/Cortex-Persist/actions/workflows/ci.yml/badge.svg)](https://github.com/borjamoskv/Cortex-Persist/actions)
[![Codecov](https://codecov.io/gh/borjamoskv/Cortex-Persist/branch/main/graph/badge.svg)](https://codecov.io/gh/borjamoskv/Cortex-Persist)

CORTEX es una **capa de confianza (drop-in trust layer)** para la memoria de IA. Aplica integridad criptográfica sobre cualquier almacenamiento (Mem0, Zep, o personalizado), garantizando que el estado y las decisiones de los agentes permanezcan a prueba de manipulaciones y listos para auditorías.

---

### Cómo encaja CORTEX

*   **Builders** → Añade memoria a prueba de manipulaciones a agentes existentes en 30 segundos.
*   **Compliance** → Exporta evidencia de auditoría determinista para requisitos regulatorios (EU AI Act).
*   **Infraestructura** → Envuelve tu almacén vectorial actual sin reemplazar tus embeddings ni tu lógica.

---

### Inicio Rápido

```bash
# 1. Instalar e Inicializar
pip install cortex-persist
cortex init

# 2. Guardar un hecho
cortex store mi-proyecto "Redis usa skip lists para sorted sets" --tags "redis,data-structures"

# 3. Guardar una decisión
cortex store mi-proyecto "Elegimos FastAPI sobre Flask por soporte async" --type decision

# 4. Buscar y recordar
cortex search "framework web async" --project mi-proyecto
cortex recall mi-proyecto

# 5. Verificar integridad
cortex verify 1
cortex trust-ledger verify

# 6. Generar un snapshot de compliance
cortex compliance-report
```

**¿Qué acaba de pasar?**
-   **Persistencia verificable**: Los hechos y decisiones se guardaron con recibos auditables.
-   **Encadenamiento de hash**: Las escrituras quedaron enlazadas en el ledger criptográfico.
-   **Verificación explícita**: Puedes validar un hecho concreto o toda la cadena cuando necesites evidencia.

---

### Integración

```python
import asyncio
from cortex import CortexEngine

async def main():
    engine = CortexEngine()

    fact_id = await engine.store(
        project="demo-agent",
        content="Usuario aprobó una transacción de $5,000",
        fact_type="decision"
    )

    results = await engine.search(
        "aprobación de transacción",
        top_k=3,
        project="demo-agent",
    )
    ledger = await engine.verify_ledger()

    assert fact_id
    assert results
    assert ledger.get("valid") is True

asyncio.run(main())
```

---

### Rendimiento (Benchmarks)

*Instancia estándar en la nube (4 vCPU, 16GB RAM).*

| Operación | Mediana | P95 | Notas |
|:---|:---|:---|:---|
| **Memory Write** | ~18 ms | ~35 ms | Local SQLite + SHA-256 |
| **Verify Record** | ~5 ms | ~12 ms | Validación de bloque individual |
| **Merkle Seal** | ~85 ms | ~140 ms | Checkpoint de 10k registros |
| **Audit Export** | ~400 ms | ~800 ms | Traversal de linaje & PDF |

---

### Documentación

- [**Superficie pública del producto**](docs/product-surface.md) — Límite recomendado entre producto y tooling amplio del repo.
- [**Inicio rápido**](docs/quickstart.md) — Ruta guiada de adopción.
- [**Referencia CLI**](docs/cli.md) — Comandos públicos recomendados.
- [**Referencia API REST**](docs/api.md) — Superficie HTTP core y capas experimentales.
- [**Seguridad y Confianza**](docs/SECURITY_TRUST_MODEL.md) — Invariantes criptográficas.
- [**Arquitectura**](docs/architecture.md) — Vista amplia del sistema y del repo.

---

### Licencia

Apache License 2.0. Consulta [LICENSE](LICENSE).

*Creado por [borjamoskv.com](https://borjamoskv.com) · [cortexpersist.com](https://cortexpersist.com)*
