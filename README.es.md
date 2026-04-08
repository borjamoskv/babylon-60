🌐 [English](README.md) | **Español** | [中文](README.zh.md)

# CORTEX Persist

**Integridad criptográfica de memoria, pistas de auditoría y linaje verificable para agentes de IA.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/borjamoskv/Cortex-Persist/actions/workflows/ci.yml/badge.svg)](https://github.com/borjamoskv/Cortex-Persist/actions)
[![Codecov](https://codecov.io/gh/borjamoskv/Cortex-Persist/branch/main/graph/badge.svg)](https://codecov.io/gh/borjamoskv/Cortex-Persist)

CORTEX es una **capa de confianza (drop-in trust layer)** para la memoria de IA. Aplica integridad criptográfica sobre cualquier almacenamiento (Mem0, Zep, o personalizado), haciendo el estado y las decisiones de los agentes verificables y detectables ante manipulación.

---

### Cómo encaja CORTEX

*   **Builders** → Añade una capa de evidencia sobre agentes existentes con una integración corta.
*   **Compliance** → Genera evidencia técnica útil para revisiones regulatorias y auditorías.
*   **Infraestructura** → Envuelve tu almacén vectorial actual sin reemplazar tus embeddings ni tu lógica.

---

### Readiness Empresarial

Si estás evaluando CORTEX para compra, procurement o adopción interna, empieza por:

- [Enterprise Readiness](ENTERPRISE_READINESS.md)
- [Due Diligence Checklist](DUE_DILIGENCE_CHECKLIST.md)
- [Deployment Hardening](DEPLOYMENT_HARDENING.md)
- [Support](SUPPORT.md)
- [Repo Governance](REPO_GOVERNANCE.md)
- [Maintainers](MAINTAINERS.md)
- [Version Support](VERSION_SUPPORT.md)
- [Release Process](RELEASE_PROCESS.md)

---

### Inicio Rápido

```bash
# 1. Instalar e Inicializar
pip install cortex-persist
cortex init

# 2. Almacenar una memoria (con hash SHA-256 y encadenada)
cortex store risk-bot "Transacción marcada: Discordancia de IP" --type decision --source risk-bot

# 3. Verificar integridad con el ID devuelto por el comando anterior
cortex verify <FACT_ID>
```

**¿Qué acaba de pasar?**
-   **Libro de Contabilidad Inmutable**: El hecho se almacenó en un registro criptográfico de solo adición.
-   **Encadenamiento de Hash**: El registro fue encadenado mediante SHA-256 al bloque anterior.
-   **Sello Merkle**: Todo el estado fue sellado con una prueba de linaje verificable.

---

### Integración

```python
import asyncio
from cortex import CortexEngine

async def main():
    engine = CortexEngine()
    
    # Almacenar con recibo criptográfico
    receipt = await engine.store_fact(
        content="Usuario aprobó transacción de $5,000",
        fact_type="decision"
    )
    
    # Verificar prueba de integridad
    assert await engine.verify(receipt.hash) == True

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
| **Audit Export** | ~400 ms | ~800 ms | Traversal de linaje y exportación de evidencia |

---

### Documentación

- [**Arquitectura**](docs/architecture.md) — Sellos Merkle y encadenamiento de hash.
- [**Seguridad y Confianza**](docs/SECURITY_TRUST_MODEL.md) — Invariantes criptográficas.
- [**Tecnologías Nativas de CORTEX**](https://cortexpersist.com/docs/cortex-native-technologies) — Definición canónica de las cinco tecnologías exclusivas del sistema.
- [**Referencia de API**](docs/api.md) — Documentación completa de SDK y CLI.
- [**Enterprise Readiness**](ENTERPRISE_READINESS.md) — Estado actual, límites y plan de evaluación.
- [**Due Diligence Checklist**](DUE_DILIGENCE_CHECKLIST.md) — Checklist reproducible para compradores y equipos técnicos.

---

### Cinco Tecnologías Nativas de CORTEX

CORTEX no solo tiene módulos; también compone cinco tecnologías propias sobre su frontera de confianza:

1. **Criptoepistemología Persistente**: decide si una salida generada merece convertirse en estado durable.
2. **Forénsica de Continuidad Hash**: demuestra que la cadena de custodia no fue alterada.
3. **Memoria Conjetural Encapsulada**: mantiene hipótesis, contradicciones y taint sin disfrazarlas de verdad.
4. **Sagas de Integridad Autónoma**: hace que cada mutación no trivial sea abortable, compensable y reversible.
5. **Autopoiesis Verificada de Agentes**: permite que los agentes sinteticen lógica nueva bajo aislamiento y validación.

La definición técnica y el mapeo a módulos reales viven en [Tecnologías Nativas de CORTEX](https://cortexpersist.com/docs/cortex-native-technologies).

---

### Licencia

Apache License 2.0. Consulta [LICENSE](LICENSE).

*Creado por [borjamoskv.com](https://borjamoskv.com) · [cortexpersist.com](https://cortexpersist.com)*
