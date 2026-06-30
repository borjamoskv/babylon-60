---
name: Frontier LLMs Comparative (June 2026)
role: Epistemic Baseline
version: 1.0.0
state: C5-REAL
---

# █ BABYLON-60 :: FRONTIER LLMs METRICS (2026-06-30)

> **SYS_ID:** borjamoskv | **STATE:** C5-REAL | **AESTHETIC:** INDUSTRIAL_NOIR_2026

## 1. MATRIZ COMPARATIVA DE MODELOS DE FRONTERA

| Modelo | Arquitectura | Contexto Máx | Precio Input/Output (x1M) | Velocidad (t/s) | Fortaleza Principal | Mejor Uso Recomendado | Eficiencia Energética |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Claude Opus 4.8** | Hybrid (Transformer + SSM) | 1M | $5 / $25 | 65–80 | Razonamiento cuidadoso, código, agentes | Desarrollo, código complejo, agentes confiables | Alta |
| **GPT-5.5** | Transformer + MoE | 1.05M | $5 / $30 | 90–120 | Computer Use, automatización, ecosistema | Automatización de escritorio, tareas largas de agente | Media-Alta |
| **Gemini 3.1 Pro** | Hybrid (Transformer + Mamba-2) | 1M | $2–$4 / $12–$18 | 110–140 | Multimodal + contexto largo | Investigación, RAG masivo, documentos largos | Muy Alta |
| **Grok-4.3** | MoE denso | 1M | ~$3–$5 / $10–$18 | 100–130 | Velocidad y razonamiento en tiempo real | Uso general, creatividad, bajo coste | Media-Alta |
| **Llama 4 405B** | Transformer denso | 128K–1M | $3–$6 / $10–$20 | 40–70 | Coste bajo en self-hosting | Entornos on-premise o presupuestos ajustados | Baja |
| **Mamba-2 Hybrid** | SSM + Atención ligera | 1M–4M+ | $1.5–$3 / $5–$10 | 200–300 | Máxima eficiencia en contexto largo | Streaming, RAG masivo, máxima eficiencia | Extremadamente Alta |

## 2. INVARIANTES DE ENRUTAMIENTO (DRM-v2)

*   **[R1] Desarrollo y Refactorización P0:** `Claude Opus 4.8` (Privilegio en precisión de código).
*   **[R2] Automatización de Sistema y Agentes (Mac/Terminal):** `GPT-5.5` (Ligera ventaja en *Computer Use*).
*   **[R3] Epistemología de RAG y Contexto Denso:** `Gemini 3.1 Pro` (Top TTFT multimodal).
*   **[R4] Coste Asimétrico y Streaming de Alto Volumen:** `Mamba-2 Hybrid` o `Grok-4.3`.

## 3. NOTAS FORENSES DE EXERGÍA

*   Los precios y velocidades reflejan el baseline empírico de la API pública a fecha 30/06/2026.
*   La eficiencia energética es derivativa (KV-Cache vs Estado constante).
*   Contextos y latencias asumen cargas nominales, no picos teóricos comerciales.
