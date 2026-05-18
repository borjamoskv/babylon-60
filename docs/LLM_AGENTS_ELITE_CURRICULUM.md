# 🤖 CORTEX Persist — Autodidact Agent Lab Guide
> **Path to Mastery:** Teoría, Construcción Real y Vigilancia del Ecosistema.
> **Subsistema:** `cortex-persist v0.3.0b3` | **Realidad:** `C5-REAL`
> **Diseño:** Industrial Noir 2026 (`#0A0A0A` / `#2B3BE5` / Humanist Sans)

---

## 🌌 Justificación Termodinámica (Ω₂)

```yaml
Claim: CORTEX-Persist Autodidact Laboratory Guide (docs/LLM_AGENTS_ELITE_CURRICULUM.md)
Proof:
  Base: 9 domains * 3 phases * S^d_i yield
  Variables:
    r: 10 # 10 dominios de conocimiento
    d: 3 # niveles de profundidad (Teoría, Construcción, Vigilancia)
    n: 27 # nodos integrados de CORTEX-Persist
    S: 100 # Constante de Singularidad
  Range: [270000, 27000000]
  Confidence: C5-REAL
```

---

## 1. 🧭 Mapa de Habilidades y Correspondencia Estructural

Para dominar los agentes LLM, no basta con consumir abstracciones de alto nivel. Debes ver cómo interactúan con el silicio y la persistencia local. A continuación se mapean tus metas de aprendizaje directamente con la arquitectura de **CORTEX-Persist**:

| Dominio Autodidacta | Concepto Clave | Path Crítico en CORTEX-Persist |
| :--- | :--- | :--- |
| **Fundamentos** | Prompting Estructurado, Compresión | [`cortex/composer/`](file:///Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex/composer), [`cortex/shannon/`](file:///Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex/shannon) |
| **Arquitectura** | ReAct Loops, MCTS, Planner | [`cortex/mcts/`](file:///Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex/mcts), [`cortex/engine/`](file:///Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex/engine) |
| **Memoria** | RAG, Vector Search local | [`cortex/memory/`](file:///Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex/memory), [`cortex/embeddings/`](file:///Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex/embeddings) |
| **Guardrails** | Contradicción y Exergía | [`cortex/guards/contradiction_guard.py`](file:///Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex/guards/contradiction_guard.py) |
| **Protocolo** | Model Context Protocol (MCP) | [`cortex/mcp/`](file:///Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex/mcp) |
| **Seguridad** | Ledger Criptográfico, Taint | [`cortex/ledger/ledger_core.py`](file:///Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex/ledger/ledger_core.py) |

---

## 2. 🛡️ Laboratorios Prácticos (Construcción Real)

### Lab 2.1: Contención Epistémica y la Frontera Determinista (Ω₁)
> **Objetivo:** Impedir que el output estocástico (alucinaciones) contamine el estado del sistema.

1. **Analiza el Guardrail de Exergía:**
   - Abre [`cortex/guards/exergy_guard.py`](file:///Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex/guards/exergy_guard.py).
   - Observa cómo se calcula la pérdida de señal y cómo se rechazan propuestas antes del commit físico.
2. **Prueba de Falsación:**
   - Diseña un test en `tests/` que inyecte un payload estocástico inválido.
   - Valida que el pipeline ejecute el rollback del patrón Saga (SAGA-1 a SAGA-6) de forma atómica.

### Lab 2.2: Memory & Local-First Vector Storage
> **Objetivo:** Escalar la ventana de contexto usando RAG local determinista sobre SQLite-vec.

1. **Inspecciona la Base Vectorial:**
   - Abre [`cortex/embeddings/`](file:///Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex/embeddings) y [`cortex/storage/`](file:///Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex/storage).
   - Examina la integración de ONNX Runtime para generación de embeddings locales sin depender de APIs de red inestables.
2. **Aislamiento Multitenant:**
   - Verifica cómo se restringen las lecturas vectoriales en base al `tenant_id` en la base de datos sqlite.

### Lab 2.3: La Cadena de Confianza (Cryptographic Audit Ledger)
> **Objetivo:** Asegurar la inmutabilidad de las decisiones tomadas por el agente.

1. **Causalidad Criptográfica:**
   - Abre [`cortex/ledger/ledger_core.py`](file:///Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex/ledger/ledger_core.py).
   - Rastrea cómo se calculan las cadenas de hashes SHA3-256 sobre cada operación y cómo se firman mediante criptografía asimétrica Ed25519.
2. **Simula un Ataque de Manipulación:**
   - Escribe una función temporal que intente alterar un registro histórico en `cortex.db` y observa la alerta inmediata generada por `cortex/ledger/verifier.py`.

---

## 3. 🎯 Los 6 Frameworks & Sandboxes como Referencia

En tu camino de Autodidacta, debes analizar cómo resuelven la computación estos ecosistemas, y compararlos con la filosofía local-first de CORTEX:

1. **OpenAI Agents SDK:** Enfoque cloud-centric.
   - *Contraste CORTEX:* Dependiente de red y API keys vivas. CORTEX-Persist funciona de forma aislada en local con fallback determinista.
2. **LangGraph:** Grafos cíclicos de estado.
   - *Contraste CORTEX:* LangGraph abstrae el estado en memoria volátil de Python. CORTEX-Persist forza transacciones ácidas y rollbacks de base de datos a nivel Saga.
3. **AutoGen:** Sistemas multi-agente conversacionales.
   - *Contraste CORTEX:* Propenso a la entropía de tokens. CORTEX aplica la Ley de la Exergía (Ω₂) para optimizar los ciclos de reloj.
4. **CrewAI:** Agentes basados en roles definidos.
   - *Contraste CORTEX:* Su runtime es laxo. CORTEX enforcea contratos rigurosos por rol (Validator, Executor, Auditor, Guardian) definidos en [`AGENTS.md`](file:///Users/borjafernandezangulo/10_PROJECTS/cortex-persist/AGENTS.md).
5. **Model Context Protocol (MCP):** El estándar de oro para interoperabilidad.
   - *Integración:* CORTEX implementa un host nativo MCP, permitiendo a cualquier LLM externo usar las herramientas de persistencia locales.

---

## 4. 📚 Papers Clave Mapeados al Silicio

1. **ReAct (Reasoning + Action):**
   - *Implementado en:* [`cortex/mcts/`](file:///Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex/mcts). Recompone la cadena de pensamiento antes de lanzar herramientas deterministas.
2. **Toolformer (Learning to Use Tools):**
   - *Implementado en:* El registro de herramientas de CORTEX. Los agentes invocan herramientas auto-documentadas bajo el control de [`cortex/guards/capability_guard.py`](file:///Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex/guards/capability_guard.py).
3. **Reflexion (Verbal Reinforcement Learning):**
   - *Implementado en:* [`cortex/guards/contradiction_guard.py`](file:///Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex/guards/contradiction_guard.py), que detecta contradicciones lógicas en las decisiones tomadas por el agente en tiempo de ejecución.

---

## ⚡ Rutina Diaria del Operador de Élite

```
07:00 ── 🔍 GIT RADAR: git log --oneline -n 10 (Reconstrucción del contexto causal)
08:00 ── 📰 ECOSYSTEM WATCH: Verificar lanzamientos de repositorios en el MCP y SWE-bench
12:00 ── 🧪 BUILD & BREAK: Crear una prueba de concepto mínima o romper un guardrail local
17:00 ── 📈 BENCHMARKING: Ejecutar pytest tests/ -v --cov=cortex para telemetría
21:00 ── 📇 EXERGY COMMIT: Consolidar estado limpio y firmar el ledger de la sesión
```

---
📝 *El ecosistema verifica, el silicio recuerda. Escribe código atómico, rechaza la entropía.*
