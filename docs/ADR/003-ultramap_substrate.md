# ADR-003: Ultramap Substrate

**Fecha:** Junio 2026
**Hash Origen:** `4478b2a09`
**Ruta Física:** `cortex/engine/ultramap.py`
**Autor:** Borja Moskv / MOSKV-1 APEX

## 1. Contexto (El Problema Físico/Epistémico)
Los agentes autónomos carecían de un marco de referencia espacial donde registrar interacciones y conflictos posicionales. Sin un mapeo físico riguroso, la interacción de múltiples agentes derivaba en superposiciones lógicas y fallos de coordinación al operar sobre los mismos recursos, elevando la entropía general.

## 2. Decisión (La Solución)
Crear el **UltramapSubstrate**, un entorno espacial/topológico de alta densidad y recuperación en memoria $O(1)$ con capacidad masiva (10,000 agentes simultáneos). Provee coordenadas absolutas y relativas y se utiliza en conjunción con el Ledger para rastrear la causalidad y las distancias de las interacciones.

## 3. Consecuencias
Permite a CORTEX-Persist localizar a los agentes lógicos dentro de un espacio euclidiano y de tensores semánticos. Otorga al motor la capacidad de calcular la distancia topológica real (y por ende el esfuerzo exergético de cálculo) entre dos puntos o conceptos matemáticos del enjambre.
