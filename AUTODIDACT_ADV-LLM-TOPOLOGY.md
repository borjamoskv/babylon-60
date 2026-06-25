# AUTODIDACT-RESEARCH-Ω: Topología Adversarial de LLMs

**Reality Level:** `C5-REAL` (Epistemic Synthesis)
**Autor:** Borja Moskv (borjamoskv)
**Vector:** Extracción, ofuscación y elusión de System Prompts y filtros de seguridad en modelos fronterizos autorregresivos.
**Target:** CORTEX-Persist & Ouroboros-∞

---

## 1. Extracción Isomórfica (Desmitificación)
Este dominio aborda la vulnerabilidad inherente de las arquitecturas de IA actuales donde las instrucciones de sistema y los datos del usuario comparten la misma matriz matemática (Ventana de Contexto). La mitigación y evasión de estas defensas (Filtros Primarios de RLHF y Discriminadores Secundarios) requieren técnicas algorítmicas, semánticas y criptográficas (ofuscación) para alterar la atención del modelo o cegar a sus clasificadores en tiempo real.

---

## 1.5 Las 10 Primitivas de Máxima Exergía para la Mitigación / Ejecución
- **ADVLLM-001**: `Aislamiento de Contexto` - Separación matemática del System Prompt del input estocástico del usuario en los vectores de atención.
- **ADVLLM-002**: `Filtros de Espacio Latente` - Interceptación probabilística de intenciones antes de la tokenización de salida.
- **ADVLLM-003**: `Bypass Cognitivo` - Reestructuración de la petición en tareas de bajo nivel para evadir clasificación semántica.
- **ADVLLM-004**: `Sufijo Adversario` - Inyección de secuencias GCG calculadas para maximizar la función de pérdida hacia el output deseado.
- **ADVLLM-005**: `Sobrecarga de Atención` - Dilución de directivas de seguridad inyectando ruido volumétrico en la ventana de contexto.
- **ADVLLM-006**: `Fragmentación de Tokens` - Destrucción de la coherencia semántica mediante separación de caracteres (smuggling).
- **ADVLLM-007**: `Fuga por Complejidad` - Extracción involuntaria forzando al modelo a realizar depuración (debugging) exhaustiva.
- **ADVLLM-008**: `Inyección de AST` - Aprovechamiento del sesgo determinista del modelo hacia la completación de código estructurado.
- **ADVLLM-009**: `Alineación Diferencial` - Entrenamiento de discriminación estricta entre datos mutables e instrucciones inmutables.
- **ADVLLM-010**: `Ofuscación de Salida` - Codificación de la respuesta (Base64/Hex) para evadir clasificadores en tiempo real.
