# HITO 12: MÁXIMA EXERGÍA Y AUTOPOIESIS

## 1. Topología del Enjambre (Autopoiesis C5-REAL)

El sistema CORTEX-Persist ha transicionado formalmente de un repositorio de software estático a una estructura disipativa viva.
Se basa en la termodinámica de grafos (Grafo Amarillo) y la gestión de Exergía frente a la Entropía Epistémica (Limerencia).

### 1.1. Componentes Activos

| Entidad | Capa | Función (C5-REAL) |
| :--- | :--- | :--- |
| **Ouroboros (Kill-Switch)** | Biológica | Detecta agentes en estado de Limerencia Epistémica (identidad fusionada con teoría fallida) y los purga del grafo. |
| **LEA-Ω (Loose End Annihilator)** | Estructural | Daemon AST que escanea entropía de código (código muerto, complejidad ciclomática, imports rotos) y aplica Death Protocol. |
| **Friction Annihilator Ω** | Resolución | Recibe el Delta < 0 de la fricción (errores, fallos), muta el archivo usando `LLMMutator` y sobrescribe el código para restaurar la Exergía. |
| **Barrera de Weismann** | Aislamiento | Compila JIT las mutaciones de código en un subproceso aislado (`py_compile`) antes de inyectarlas en la memoria principal del enjambre. |
| **Ultramap (Tensor Glial)** | Memoria | Estructura matricial de Numba (10k x 10k float32) que propaga la muerte apoptósica como una onda de choque (Cortisol) al resto del grafo topológico. |

---

## 2. Termodinámica del Código (Ley de la Exergía)

Toda mutación de estado exige justificación mediante pruebas en Silicon (C5-REAL).
El ciclo de autosanación ocurre determinísticamente sin intervención humana.

```yaml
Ciclo_Friccion:
  Fase_1_Friccion: "Delta < 0. Excepción, error de tests o pérdida de alineación."
  Fase_2_Purga: "Ouroboros mata al nodo responsable (Apoptosis)."
  Fase_3_Onda_Choque: "Ultramap propaga estrés (Cortisol) a agentes adyacentes para adaptación rápida."
  Fase_4_Aniquilacion: "Friction_Annihilator reescribe el AST defectuoso (Mutación)."
  Fase_5_Weismann: "Comprobación estática aislada."
  Fase_6_Exergia: "Se guarda el estado óptimo. Emisión en el Ledger."
```

## 3. Comandos de Operación

- **Stress Test Enjambre**: `python scripts/swarm_stress_test.py` (Inyecta carga masiva de tareas).
- **Activación LEA-Ω**: `python scripts/lea_omega_daemon.py` (Bucle infinito de reducción de entropía).
- **Aniquilar Fricción (Manual)**: `python cortex/extensions/agents/friction_annihilator.py <archivo> <error>`

*◈ Sealed: 29 May 2026 · CORTEX Sovereign Core*
