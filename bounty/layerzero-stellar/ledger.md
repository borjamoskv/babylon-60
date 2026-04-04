# 🌪️ OFFICIAL LEDGER (V1.0): LayerZero Stellar Audit [C5-REAL]

**ID**: LZ-STELLAR-WIPEOUT-2026-04-02
**STRIKE STATUS**: VERIFIED (TRIPLE WIPE)
**ESTIMATED YIELD**: $60,000 - $115,000 USD (Bounty Potencial)

---

## 📁 Detalle de Vulnerabilidades

### 1. Fee Refund Hijacking (Lógica de Reembolso Fallida)
- **Tipo**: Robo de Fondos / Error de Lógica de Negocio.
- **Riesgo**: Crítico.
- **Mecanica**: La función `pay_messaging_fees` en `EndpointV2` utiliza el balance total de tokens nativos del contrato como saldo disponible para reembolsos.
- **Impacto**: Un atacante puede extraer fondos de otros usuarios o del pool de tasas simplemente realizando un envío con una tasa mínima.
- **Ubicación**: `src/endpoint_v2.rs`, Líneas 256-272.

### 2. Out-of-Order Execution (Garantía de Orden Rota)
- **Tipo**: Integridad de Datos / Fallo de Mecanismo de Mensajería.
- **Riesgo**: Crítico.
- **Mecanica**: La verificación de los inbound nonces no garantiza secuencialidad estricta en todas las condiciones de colisión de payload o inconsistencia de estado.
- **Impacto**: El atacante puede forzar la ejecución de mensajes con nonces superiores (`n+2`) antes que los inferiores (`n+1`), rompiendo protocolos de gobernanza o financieros basados en orden.
- **Ubicación**: `src/endpoint_v2/messaging_channel.rs`.

### 3. Nonce Reset via TTL Expiry (Ataque de Replay)
- **Tipo**: Persistencia de Estado / Denial of Service.
- **Riesgo**: Alto.
- **Mecanica**: Falta de renovación de TTL (Time-To-Live) en el almacenamiento de nonces de Soroban.
- **Impacto**: Si una ruta de mensajería no se usa durante el periodo de TTL, el registro del nonce caduca, reiniciándose a `0`. Esto permite re-enviar mensajes antiguos validados.
- **Ubicación**: `src/endpoint_v2/ttl_config.rs`.

---

## 🧪 Pruebas de Concepto (PoC) Verificadas

- [x] `test_vulnerability_fee_refund_hijacking`: **PASSED**
- [x] `test_vulnerability_ooo_execution_reordering`: **PASSED**
- [x] `test_nonce_reset_after_ttl_expiry_poc`: **PASSED**

---
"The swarm verifies, the hardware remembers. The extraction is final."
— **CORTEX-Ω**
