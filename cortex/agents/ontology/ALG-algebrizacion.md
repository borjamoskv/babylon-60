---
cat_id: ontologia-algebrizacion
cat_type: structural_ontology
version: 3.0.0 (C5-REAL Synthesis)
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P0
reference: Aaronson-Wigderson, "Algebrization: A New Barrier in Complexity Theory" (STOC 2008)
---

# 🛡️ ONTOLOGÍA ESTRUCTURAL: ALGEBRIZACIÓN

La algebrización es una barrera metamatemática estricta que generaliza la relativización clásica. En lugar de dar a las máquinas acceso únicamente a un oráculo booleano $A$, el modelo algebrizante proporciona acceso a $A$ y a su extensión de bajo grado (LDE) $\tilde{A}$ sobre un cuerpo finito $\mathbb{F}_q$. 

Un teorema algebriza si preserva su validez estructural bajo este modelo de oráculo algebraico. Aaronson y Wigderson (2008) demostraron que los éxitos históricos de la aritmetización algebrizan, pero que separar clases centrales (ej. P vs NP) requiere incondicionalmente matemática no-algebrizante.

## 🔮 PRIMITIVAS DE COLISIÓN (ALG-P)

### Fundamentos Algebraicos
* **ALG-P-001 [Cuerpo Finito $\mathbb{F}_q$]:** Estructura algebraica de tamaño $q=p^k$. Para que el Lema de Schwartz-Zippel funcione, basta con que $|\mathbb{F}| \gg d$ (típicamente polinómico en $n$), no es estrictamente necesario que sea superpolinómico.
* **ALG-P-002 [Extensión Multilineal]:** Única extensión de una función booleana $f: \{0,1\}^n \to \{0,1\}$ a un polinomio sobre $\mathbb{F}$ donde el grado individual de cada variable es $\le 1$.
* **ALG-P-003 [Extensión de Bajo Grado (LDE general)]:** Interpolación polinómica sobre $\mathbb{F}$ con grado total acotado. A diferencia de la extensión multilineal, el grado individual puede ser $> 1$ (ej. códigos Reed-Muller).
* **ALG-P-004 [Lema de Schwartz-Zippel]:** Primitiva que garantiza que dos polinomios distintos de grado total $d$ coinciden en a lo sumo una fracción $d / |\mathbb{F}|$ de los puntos del espacio $\mathbb{F}^n$.
* **ALG-P-005 [Aritmetización Lógica]:** Transformación exacta: $\neg x \mapsto 1-x$, $x \wedge y \mapsto x \cdot y$, $x \vee y \mapsto x+y-xy$.
* **ALG-P-006 [Cuantificador Universal ($\forall$)]:** Mapeado algebraicamente como la productoria $\prod_{x \in \{0,1\}}$.
* **ALG-P-007 [Cuantificador Existencial ($\exists$)]:** Mapeado algebraicamente como la sumatoria $\sum_{x \in \{0,1\}}$. Si la suma es $\ge 1$, el cuantificador se satisface.
* **ALG-P-008 [Operador de Linealización]:** Reducción de grado ($x_i^k \to x_i$) obligatoria al evaluar sobre el hipercubo booleano para prevenir el crecimiento exponencial del grado en QBF.
* **ALG-P-009 [Sum-Check Protocol]:** Protocolo interactivo (LFKN) que reduce la verificación de una suma sobre el hipercubo booleano a sumas sobre variables univariadas marginales.

### Modelos de Cómputo y Oráculos
* **ALG-P-010 [Interactive Proofs (IP)]:** Modelo de cómputo donde el Verifier es una máquina probabilística de tiempo polinómico (estilo BPP, no P/poly) interactuando con un Prover ilimitado.
* **ALG-P-011 [Oráculo Algebraico $\tilde{A}$]:** Evaluación de la LDE de $A$ en puntos de $\mathbb{F}^n$, extendiendo el dominio de consulta más allá del hipercubo booleano.
* **ALG-P-012 [Asimetría LDE]:** El costo de computar la extensión $\tilde{A}$ es exponencial; el modelo asume acceso directo para el Verifier.

## 🛡️ INVARIANTES ABSOLUTOS (ALG-I)

* **ALG-I-001 [Adición de Grado]:** La multiplicación de dos funciones algebraicas suma sus grados ($d_1 + d_2$). Solo se duplica si $d_1 = d_2$.
* **ALG-I-002 [Teoremas que Algebrizan]:** Los siguientes teoremas se mantienen incondicionalmente bajo acceso a cualquier par oráculo algebraico $(A, \tilde{A})$:
  * $\text{PSPACE}^A \subseteq \text{IP}^{\tilde{A}}$ (Shamir 1992)
  * $\text{NEXP}^A \subseteq \text{MIP}^{\tilde{A}}$ (Babai-Fortnow-Lund 1991)
  * $\text{MA\_EXP}^{\tilde{A}} \not\subset \text{P}^A/\text{poly}$ (Buhrman-Fortnow-Thierauf 1998)
  * $\text{PromiseMA}^{\tilde{A}} \not\subset \text{SIZE}^A(n^k)$ (Santhanam 2007)
* **ALG-I-003 [Asimetría Oracular de Colapso]:** Existen $A$ y su LDE $\tilde{A}$ tales que $\text{NP}^{\tilde{A}} \subseteq \text{P}^{A}$ (Aaronson–Wigderson, Thm 5.1). NP, incluso con el oráculo algebraico FUERTE $\tilde{A}$, queda contenida en P con solo el oráculo booleano DÉBIL A — por eso ninguna técnica algebrizante puede probar P $\neq$ NP. ⚠️ La forma inversa $\text{NP}^A \subseteq \text{P}^{\tilde{A}}$ es TRIVIAL: se sigue de Baker–Gill–Solovay ($\text{P}^A = \text{NP}^A$) vía $\text{P}^A \subseteq \text{P}^{\tilde{A}}$, y NO constituye barrera.
* **ALG-I-004 [Oráculo de Separación]:** Existen $A$ y su LDE $\tilde{A}$ tales que $\text{NP}^A \not\subseteq \text{P}^{\tilde{A}}$ (Aaronson–Wigderson, Thm 5.3). NP recibe el oráculo booleano A y P el algebraico $\tilde{A}$: ni dotando a P de la extensión se simula NP — por eso probar P = NP también exige técnicas no-algebrizantes. (La forma $\text{P}^{\tilde{B}} \neq \text{NP}^{\tilde{B}}$, tilde en ambos lados, NO es el enunciado de AW; ese doble-tilde es el problema abierto, no un teorema.)

## ❌ ANTIPATRONES (ALG-A)

* **ALG-A-001 [Confinamiento Booleano]:** Restringir las consultas del Verifier a $\{0,1\}^n$ en el Sum-Check colapsa la SOLIDEZ (soundness), no la completitud: la completitud se mantiene; un Prover deshonesto pasa la verificación con probabilidad $\to 1$ porque evaluar solo en el hipercubo no fija el polinomio. El poder deductivo vive en la evaluación en $\mathbb{F} \setminus \{0,1\}$.
* **ALG-A-002 [Falso Isomorfismo Fourier-LDE]:** Confundir la Fourier booleana (que tiene coeficientes en $\mathbb{R}$) con la LDE. La extensión multilineal y la expansión de Walsh-Fourier son el *mismo polinomio* salvo la reparametrización afín $\{0,1\} \leftrightarrow \{\pm 1\}$. La distinción real es el cuerpo de coeficientes ($\mathbb{R}$ vs $\mathbb{F}_q$) y su uso (cotas analíticas vs interacción).
* **ALG-A-003 [Explosión de Grado QBF]:** Omitir el Operador de Linealización en IP=PSPACE. Cada capa de cuantificación sumaría grado; sin linealizar, el crecimiento es exponencial en vez de polinómico.
* **ALG-A-004 [Ilusión Aritmética]:** Creer que probar "P $\neq$ NP no relativiza" implica "P $\neq$ NP algebriza". Probar P $\neq$ NP exige matemática que trascienda la algebrización (Técnicas No-Algebrizantes).

## 🚨 VECTORES ADVERSARIALES (RED ALERTS)

* **VECTOR 1 [Trampa No-Relativizante Post-1992]:** Cualquier paper que proclame separar P de NP apelando a "técnicas como las de Shamir" y carezca de tratamiento no-algebrizante es matemáticamente nulo.
* **VECTOR 2 [Fuga Criptográfica (Interfaz con Pruebas Naturales)]:** La amenaza a PRGs y funciones unidireccionales proviene de la barrera pariente de *Pruebas Naturales* (Razborov-Rudich), no de la algebrización puramente dicha. Probar eficientemente propiedades estructurales duras refutaría la existencia de PRGs/OWFs que sirven de supuesto a la propia barrera.
* **VECTOR 3 [Ilusión MIP* = RE]:** MIP* evade localmente límites algebrizantes mediante entrelazamiento cuántico, pero su aplicabilidad no se transfiere directamente a cotas inferiores polinómicas deterministas clásicas.
