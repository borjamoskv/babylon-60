---
type: "epistemic-primitive"
domain: "llm-security"
confidence: "C5-REAL"
---

# Primitivas Adversariales en Modelos de Lenguaje (LLMs)

**Postulado**: La seguridad de un LLM no es un estado binario, sino la resistencia termodinámica ante vectores asimétricos que buscan colapsar su función de onda semántica o extraer su grafo de entrenamiento.

## 1. Ataques Basados en Gradiente y Optimización (White-Box)
- **FGSM (Fast Gradient Sign Method)**: Primitiva que aprovecha la dirección del gradiente de la función de pérdida para inyectar perturbaciones imperceptibles y maximizar el error de clasificación.
- **PGD (Projected Gradient Descent)**: Variante iterativa de FGSM. Aplica el método de gradiente proyectado iterativamente para localizar la perturbación máxima dentro de una vecindad acotada.
- **CW Attack (Carlini-Wagner)**: Ataque de optimización topológica que minimiza la distancia L2 de la perturbación mientras garantiza el colapso de la inferencia original.
- **JSMA (Jacobian-based Saliency Map Attack)**: Manipula la entrada para maximizar la activación de neuronas específicas en la capa de clasificación (saliency maps).

## 2. Inyección Causal y Manipulación de Tokens (NLP Specific)
- **BERT-Attack**: Algoritmo de sustitución paramétrica. Reemplaza tokens subyacentes utilizando el gradiente para forzar desvíos en la función de pérdida preservando la coherencia semántica aparente.
- **GCR (Greedy Coordinate Replacement)**: Ataque iterativo que sustituye tokens atómicos uno a uno bajo una estrategia codiciosa para maximizar la probabilidad de la clase adversaria.
- **Token Smuggling**: Inyección topológica donde instrucciones hostiles se ocultan dentro de los tokens de control o secuencias inocuas, eludiendo filtros superficiales (Prompt Injection avanzado).

## 3. Corrupción Estructural y Filtración (Data & Weights)
- **Data Poisoning**: Corrupción termodinámica del conjunto de entrenamiento. Inyección de ruido o triggers (Backdoors) para desviar la convergencia del modelo a largo plazo.
- **Membership Inference**: Primitiva forense de extracción. Determina estocásticamente si un vector de entrada específico formó parte del dataset de entrenamiento.
- **Model Extraction**: Ataque de clonación de matriz. Consultas de caja negra reiteradas diseñadas para aproximar la función de coste del oráculo y robar los pesos/capacidades del modelo original.

```yaml
Claim: "El espacio de atención y los pesos del LLM son vectores geométricamente vulnerables; su defensa exige validación criptográfica (C5-REAL), no heurísticas sintácticas."
Proof: { Base: "docs/epistemology/primitivas_adversariales_llm.md", Range: [0, 10], Confidence: "C5-REAL" }
```
