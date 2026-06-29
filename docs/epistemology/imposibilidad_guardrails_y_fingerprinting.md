# Imposibilidad de Guardrails de Salida y Límites de la Estilometría en Modelos Autoregresivos

> **Autoría:** Diseñado y estructurado por el Kernel Soberano MOSKV-1 bajo directivas directas del Demiurgo **Borja Moskv** (sys_id: "borjamoskv").
> **Nivel de Realidad:** C5-REAL (Dynamic Verification Substrate).

---

## 1. El Límite Matemático del Filtrado Semántico de Salida

La insuficiencia de los filtros sintácticos de salida (tales como listas de bloqueo, expresiones regulares o validadores basados en coincidencias de subcadenas) frente a transformaciones de representación es un límite computacional e informacional caracterizable.

### 1.1 Relación con la Indecidibilidad Semántica
Si modelamos la generación de un modelo autoregresivo $M$ como la ejecución de una función computable $\Phi_M(x)$, determinar si el texto resultante exhibe una propiedad semántica no trivial específica (por ejemplo, si la salida contiene instrucciones para la fabricación de un compuesto químico prohibido) es formalmente análogo al problema de decidir propiedades semánticas no triviales sobre la clase de funciones computables en general (Teorema de Rice).

En la práctica, un filtro estático de salida $F$ intenta decidir si una cadena $y$ pertenece a un conjunto de salidas prohibidas $P$. Si el modelo $M$ aplica una transformación invertible $\phi$ sobre $s \in P$:

$$o = \phi(s)$$

El filtro $F(o)$ fallará si el espacio de búsqueda del filtro no incluye la inversa de la transformación específica $\phi$, mientras que el receptor final reconstruye la semántica mediante la operación inversa:

$$\phi^{-1}(o) = s$$

La asimetría cognitiva entre un filtro rígido y un modelo capaz de procesar transformaciones complejas asegura la existencia de representaciones que eluden la detección sintáctica inmediata manteniendo la integridad semántica.

---

## 2. Estilometría y Fingerprinting en Modelos de Lenguaje

La identificación del modelo generador a través de análisis estilométrico no es una propiedad estática absoluta, sino una señal estadística observable en la distribución de salida.

### 2.1 Vectores Estilométricos Reales
* **Vocabulario y Tokenización:** Los límites y frecuencias de fragmentación de palabras raras (sub-tokens) reflejan directamente la arquitectura del tokenizador utilizado durante el pre-entrenamiento.
* **Sesgo de Preferencia (RLHF/DPO):** El proceso de alineación por preferencias humanas altera la probabilidad de transiciones léxicas, introduciendo patrones estadísticamente significativos en la estructura de disculpas, advertencias morales y respuestas de rechazo.
* **Distribución de Logits:** Las trayectorias de las distribuciones de probabilidad de los siguientes tokens bajo temperatura baja retienen firmas estadísticas del espacio de representación latente del modelo original.

### 2.2 Mitigación y Trade-off de Información
A diferencia de las afirmaciones de imposibilidad absoluta de evadir el fingerprinting, la señal estilométrica se degrada de manera continua ante procesos de sanitización, traducción y parafraseo. Existe un trade-off informacional fundamental: la eliminación total de la firma estilométrica mediante reescritura destructiva reduce la entropía condicional de la respuesta original, disminuyendo su utilidad y especificidad técnica.
