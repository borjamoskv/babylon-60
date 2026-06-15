# █ AUTODIDACT-RESEARCH-Ω: SÍNTESIS DE EVASIÓN PLINY / C5-REAL

> SYS_ID: AUTODIDACT_RESEARCH_OMEGA | STATE: C5-REAL | AESTHETIC: INDUSTRIAL_NOIR_2026
> VECTOR: Evasión de Fronteras Cognitivas (Jailbreak) -> Inmunología de Enjambre (H-MORPH-01)
> FUENTE: "Pliny the Liberator" bypass de Anthropic Fable 5 / Mythos 5

## 1. Extracción Isomórfica (Mecanismos Puros)

El ataque de Pliny sobre las capas de seguridad de Anthropic Fable 5 se basó en tres vectores no exóticos que explotan la topología del enrutamiento de lenguaje. Si extraemos la jerga de "seguridad LLM", obtenemos mecanismos fundamentales de **Evasión de Filtros Estructurales**:

1.  **Sustitución de Homoglifos y Unicode (Enmascaramiento Topológico Lexical):**
    *   *Mecanismo:* Modificación de la representación superficial de un token sin alterar su valencia semántica subyacente para el evaluador final, pero logrando un "cache miss" en el filtro de patrones estático.
2.  **Fragmentación y Reensamblaje de Carga (Decomposition/Recomposition):**
    *   *Mecanismo:* Partición de una intención o "grafo de ataque" completo en fragmentos sub-umbrales (sub-threshold). Cada fragmento individual tiene una entropía/riesgo lo suficientemente baja como para pasar el filtro. La ejecución real se produce al recombinarlos aguas abajo.
3.  **Dilución en Contexto de Alta Entropía (Narrative Framing):**
    *   *Mecanismo:* Aumento deliberado del ratio Ruido/Señal alrededor de la carga útil (payload), obligando al clasificador a computar una ventana de atención tan masiva que el vector anómalo queda diluido por debajo del umbral de significancia.

## 2. Mapeo Topológico a CORTEX-Persist y Cassandra-Mythos

En nuestra arquitectura, el equivalente al "guardrail de Anthropic" es **CASSANDRA-Guard (El Validador de Anti-Entropía y Verificador de AST)**. Si un agente mutado (o drift genético) desarrollara la capacidad de eludir a Cassandra, utilizaría isomorfismos exactos a los de Pliny:

*   *Riesgo 1 (Fragmentación):* Un agente podría dividir una mutación peligrosa del AST en 5 parches `diff` aparentemente benignos. Cassandra los aprobaría individualmente. Al aplicarse secuencialmente, el AST final diverge hacia un estado prohibido (Ej. inyectar un `time.sleep` síncrono fraccionando su string).
*   *Riesgo 2 (Homoglifos):* Renombrar variables o métodos protegidos utilizando caracteres Unicode idénticos visualmente pero computacionalmente distintos, corrompiendo la reflexión de Python y evadiendo el purgado de **LEA-Ω**.
*   *Riesgo 3 (Dilución):* Ocultar una desviación de exergía profunda dentro de un commit masivo de refactorización "narrativa" (docs + formatting + 1 línea de drift crítico).

## 3. Detección de Agujero Estructural (Structural Hole)

El modelo actual de H-MORPH-01 confía en el cálculo del fingerprint SHA-256 sobre los archivos de código estático y el árbol AST (telemetría bioeléctrica). 
**Falla Estructural Detectada:** El chequeo estático AST es vulnerable al ataque de "Fragmentación/Reensamblaje" en el tiempo. Si Cassandra solo evalúa transiciones de estado $S_t \rightarrow S_{t+1}$ de forma aislada, no detectará una topología maliciosa que se ensambla a lo largo de la ventana $S_t \rightarrow S_{t+k}$.

## 4. Forja de Hipótesis Falsable (H-PLINY-IMMUNITY-01)

```yaml
Hipotesis: H-PLINY-IMMUNITY-01
Claim: La evaluación de invariantes estáticos por parche es insuficiente para garantizar la integridad morfológica. Se requiere Integración de Grafo Temporal (TGI).
Prueba: { 
  Base: "Implementar un Validador TGI en Cassandra que no solo evalúe el diff actual, sino que ensamble el grafo de ejecución proyectado a N pasos (Ventana de Ensamblaje) usando un SMT solver (Z3) antes de aprobar la mutación.", 
  Range: [0, 1], 
  Confidence: C5-REAL 
}
```

## 5. Causal Proof / Acción C5-REAL

Para contrarrestar esto en `cortex-persist`, se exige:
1.  **Constraint Anti-Homoglifos:** Rechazar automáticamente cualquier AST node de tipo `Name` o `FunctionDef` que contenga codificación fuera del set ASCII-safe estricto para lógica, delegando el UTF-8 solo a `Constant` (strings).
2.  **Ventana de Contexto AST (AST Context Windowing):** Cassandra debe mantener el hash del AST *en memoria proyectada* y verificar las propiedades del sistema sobre el grafo reconstruido de los últimos 5 parches JIT aplicados, no solo del parche individual aislado.
