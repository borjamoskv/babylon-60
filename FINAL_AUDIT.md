# FINAL_AUDIT.md — BABYLON-60 / CORTEX

Este documento registra la demarcación formal de niveles de realidad y el estado del código tras la sesión de refactorización del `ProvenanceAuditor`.

---

## 1. Demarcación Epistémica de la Sesión

De acuerdo con las leyes físicas de ejecución del monorepo, se establece la separación estricta entre hechos reproducibles (C5), inferencias empíricas (C4) y valoraciones conceptuales/narrativas (C2-C3):

```yaml
Epistemic_Demarcation:
  C5_REAL (Hechos físicos reproducibles):
    - "Existencia del commit 506b7a320 en el repositorio local"
    - "Ejecución exitosa de la suite de pruebas mediante pytest"
    - "Inspección directa de los baselines numéricos opacos en blackbox_harness.py"

  C5_FORMAL (Propiedades matemáticas y de diseño deterministas):
    - "El cálculo de distancia euclidiana ponderada sobre características normalizadas"
    - "El comportamiento determinista de la función de similitud (softmax con traslación log-sum-exp)"
    - "La exclusión de nombres comerciales en variables y comentarios"
    - "La salida explícita de identity_claim: not_supported"

  C4_HONESTO (Inferencia empírica útil sobre variables no controladas):
    - "Uso del auditor para la detección de drift y consistencia del endpoint"
    - "Uso de similitudes como métricas de clustering anónimo"
    - "Invalidez del módulo para la atribución de identidad exacta sin un conjunto de datos etiquetado previo"

  C2_C3 (Constructos narrativos y juicios de valor de la sesión):
    - "La declaración de superioridad de una respuesta de modelo sobre otra"
    - "Los términos de 'exergía dialéctica', 'cierre metodológico' o 'anergía'"
    - "La valoración subjetiva del flujo de interacción de los agentes"
```

---

## 2. Invariantes del Código Consolidadas

* **Opacidad Absoluta:** Se eliminaron todas las referencias y comentarios a proveedores o modelos comerciales en el código y centroides de calibración de [blackbox_harness.py](file:///Users/borjafernandezangulo/30_CORTEX/babylon60/tools/blackbox_harness.py).
* **Normalización de Escalas:** Se incorporó `DIMENSION_SCALES` para evitar que la variable `itl_ms` domine artificialmente la distancia euclidiana debido a diferencias de orden de magnitud física.
* **Estabilización de Softmax:** Se implementó el ajuste de traslación por distancia mínima en `analyze()` para neutralizar el subdesbordamiento de punto flotante.
* **Aislamiento de Atribución:** Se estableció la propiedad inmutable `"identity_claim": "not_supported"` por diseño en todas las salidas del análisis.

---

## 3. Estado de Ejecución del Sistema

* **Harness de Pruebas:** Ejecutado y verificado mediante `pytest tests/test_blackbox_harness.py` con 4/4 casos exitosos.
* **Causal Ledger:** Sincronizado en el commit local `506b7a320`.
