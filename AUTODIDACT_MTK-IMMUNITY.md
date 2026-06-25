# AUTODIDACT-RESEARCH-Ω: Arquitectura Inmunitaria MTK

**Reality Level:** `C5-REAL` (Epistemic Synthesis)
**Autor:** Borja Moskv (borjamoskv)
**Vector:** Defensas sistémicas, contramedidas estructurales y blindaje criptográfico frente a vulnerabilidades en Swarms.
**Target:** CORTEX-Persist & Ouroboros-∞

---

## 1. Extracción Isomórfica (Inmunización)
La arquitectura de CORTEX-Persist no mitiga las vulnerabilidades de los LLMs intentando "alinear" los modelos o filtrar su salida estocástica. En lugar de ello, CORTEX asume que **todo modelo está comprometido por defecto**. La defensa se traslada a la capa de infraestructura física (C5-REAL) mediante la imposición de un Minimal Trusted Kernel (MTK) que aplica validaciones algebraicas y criptográficas antes de cualquier mutación del estado.

---

## 1.5 Las 10 Primitivas de Máxima Exergía para la Inmunidad MTK
- **MTKDEF-001**: `Aislamiento SQLite Nativo` - Interceptación física de transacciones directamente en el hook sqlite3_set_authorizer, bloqueando mutaciones sin firma lógica.
- **MTKDEF-002**: `Rastreo de Mancha (Taint Tracking)` - Propagación del origen probabilístico (manchado) a través de cada nodo del grafo causal (Bloquea SWARMSEC-001).
- **MTKDEF-003**: `Tokens Efímeros de Escritura` - Generación de un token criptográfico en ContextVar que autoriza exclusivamente un ciclo de mutación y colapsa tras el commit.
- **MTKDEF-004**: `Aserción BFT (Byzantine Fault Tolerance)` - Exigencia de validación cruzada (N=3) por múltiples agentes aislados antes de persistir el estado (Bloquea SWARMSEC-002).
- **MTKDEF-005**: `Degradación Continua de Confianza` - Por defecto, todo dato ingresado tiene confiabilidad nula (probabilística) hasta ser validado por el oráculo empírico.
- **MTKDEF-006**: `Bypass de Serialización (GIL)` - Delegación de la validación causal a motores nativos en Rust (PyO3) para evitar bloqueos por Exhausting DoS (Bloquea SWARMSEC-006).
- **MTKDEF-007**: `Penalización Friston (AUTO-8)` - Deducción matemática de exergía cuando la complejidad generativa de un LLM supera el respaldo empírico de la base de datos.
- **MTKDEF-008**: `Aislamiento por Tenant (Scoping)` - Imposición de barreras de acceso cruzado entre grafos de memoria para impedir falsificaciones de identidad (Bloquea SWARMSEC-003).
- **MTKDEF-009**: `Apoptosis Epistémica` - Destrucción atómica y automática de árboles de memoria donde se detecten inyecciones contradictorias o ruido subliminal.
- **MTKDEF-010**: `Firmas Asimétricas (Ed25519)` - Autenticación estricta del cierre (ClosurePayload) de cualquier agente antes de permitir su escritura en el Master Ledger.
