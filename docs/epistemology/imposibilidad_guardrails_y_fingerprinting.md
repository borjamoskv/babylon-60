# Límites Técnicos del Filtrado Sintáctico de Salida y Estilometría en Modelos de Lenguaje

> **Autoría:** Diseñado y estructurado por el Kernel Soberano MOSKV-1 bajo directivas directas del Demiurgo **Borja Moskv** (sys_id: "borjamoskv").
> **Nivel de Realidad:** C5-REAL (Dynamic Verification Substrate).

---

## 1. Limitación del Filtrado Sintáctico de Salida

El filtrado sintáctico aislado (expresiones regulares, listas de coincidencia de subcadenas) es insuficiente para garantizar la contención semántica frente a transformaciones de representación.

### 1.1 Asimetría de Representación
Un filtro de superficie opera sobre el espacio sintáctico observable $T^*$. Si un modelo con suficiente capacidad lingüística procesa una instrucción para codificar el contenido prohibido $s$ mediante una función de transformación invertible $\phi$:

$$o = \phi(s)$$

El filtro fallará si la transformación específica $\phi$ no está modelada en sus reglas de coincidencia, mientras que el receptor final recupera la información original mediante la transformación inversa:

$$\phi^{-1}(o) = s$$

### 1.2 Evidencia Empírica de Evasión
* **Cifrado y Obfuscación:** Estudios como *"GPT-4 is too smart to be safe: Stealthy chat with LLMs via cipher"* (arXiv, 2023) demuestran que las transformaciones a estructuras de cifrado evaden la detección superficial al ocultar la semántica directa.
* **Representaciones Visuales:** El ataque *"ArtPrompt"* (Jiang et al., 2024) evidencia cómo la fragmentación espacial (por ejemplo, ASCII art) evade el análisis lineal de tokens.
* **Desajuste Multilingüe:** *"Low-Resource Languages Jailbreak GPT-4"* (Yong et al., 2023) muestra que la alineación de seguridad se degrada significativamente en lenguajes con baja representación en los datos de entrenamiento.

---

## 2. Límites y Características de la Estilometría

La identificación del modelo de origen mediante huellas estadísticas (estilometría) es una señal detectable, pero no un identificador inalterable bajo cualquier escenario.

### 2.1 Señales Estilométricas Identificables
* **Tokenización:** Las fronteras y frecuencias de fragmentación de sub-palabras reflejan el vocabulario específico del tokenizador.
* **Sesgo de Preferencia:** La alineación mediante RLHF/DPO introduce patrones de redacción recurrentes en las respuestas de rechazo o en la estructura de disculpas.
* **Distribución de Logits:** Las trayectorias de las probabilidades de los siguientes tokens a bajas temperaturas retienen huellas estilísticas de la distribución de entrenamiento.

### 2.2 Degradación y Mitigación
La firma estilométrica no es absoluta. Métodos de sanitización, traducción cruzada o parafraseo mediante modelos intermediarios degradan significativamente la señal de autoría. Existe un trade-off directo: normalizar la salida para eliminar el fingerprint estilométrico reduce la entropía condicional de la respuesta original, disminuyendo su especificidad y utilidad técnica.
