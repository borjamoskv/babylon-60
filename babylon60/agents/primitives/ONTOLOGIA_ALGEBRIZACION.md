# [C5-REAL] MATRIZ ONTOLÓGICA DE ALGEBRIZACIÓN (V 3.0)
---
cat_id: alg-matrix-100-100-20-10
cat_type: formal_computational_topology
reality_level: C5-REAL
exergy_tier: P0
status: CRYSTALLIZED
---

## 🔮 100 PRIMITIVAS DE COLISIÓN (ALG-P)
*Componentes atómicos necesarios para construir o auditar una prueba en el dominio algebraico.*

### I. Fundamentos de Aritmetización (001-025)
001. **Cuerpo Finito ($\mathbb{F}_q$):** El sustrato donde ocurre la aritmética (usualmente $|\mathbb{F}| \gg poly(n)$).
002. **Extensión Multilineal (MLE):** El único polinomio que coincide con una función booleana en $\{0,1\}^n$ y tiene grado 1 en cada variable.
003. **Extensión de Bajo Grado (LDE):** Generalización de MLE para grados $d > 1$.
004. **Linealización ($\mathcal{L}$):** Operador que mapea $x^2 \to x$ para mantener el grado bajo control durante la aritmetización de cuantificadores.
005. **Mapeo AND ($\times$):** Producto aritmético de variables.
006. **Mapeo NOT ($1-x$):** Complemento aritmético.
007. **Mapeo OR ($x+y-xy$):** Suma inclusiva aritmética.
008. **Mapeo XOR ($x+y-2xy$):** Paridad aritmética.
009. **Cero-Test:** Propiedad de verificar si un polinomio es idénticamente nulo mediante evaluaciones aleatorias.
010. **Lema de Schwartz-Zippel:** El "martillo" probabilístico para comparar polinomios.
011. **Hipercubo Booleano ($H^n$):** El dominio $\{0,1\}^n$ embebido en $\mathbb{F}^n$.
012. **Grado Total ($deg(P)$):** Suma máxima de exponentes en cualquier monomio.
013. **Grado Individual:** Grado máximo respecto a una sola variable $x_i$.
014. **Interpolación de Lagrange:** Reconstrucción de la LDE a partir de valores discretos.
015. **Característica del Cuerpo ($p$):** Orden del subcuerpo primo.
016. **Variables de Arithmetization:** Transición de símbolos lógicos a elementos de $\mathbb{F}$.
017. **Aritmetización de Fórmulas (CNF):** Conversión de cláusulas a productos de polinomios.
018. **Aritmetización de Circuitos:** Traducción de puertas lógicas a niveles de profundidad polinómica.
019. **Extensión de Oráculo ($\tilde{A}$):** La LDE de un oráculo booleano $A$ accesible en puntos no-booleanos.
020. **Consulta Algebraica:** Petición de evaluación al oráculo $\tilde{A}$ en un vector de $\mathbb{F}^n$.
021. **Evaluación Aleatoria:** Punto de prueba seleccionado vía *Public Coins*.
022. **Cuerpo de Extensión:** Uso de $\mathbb{F}_{p^k}$ para garantizar que el tamaño del cuerpo sea suficiente.
023. **Polinomio Selector:** Polinomio que vale 1 en un punto del hipercubo y 0 en el resto.
024. **Aritmetización de TQBF:** Transformación de la lógica de predicados en una cadena de sumas y productos.
025. **Dominio de Evaluación:** El subconjunto de $\mathbb{F}$ sobre el cual el Verifier puede consultar.

### II. Protocolos y Pruebas Interactivas (026-050)
026. **Protocolo Sum-Check:** El algoritmo central para verificar sumas de polinomios multivariados.
027. **Ronda de Reducción:** Paso interactivo que reduce una afirmación sobre $n$ variables a una sobre $n-1$.
028. **Polinomio Univariado Marginal:** El mensaje enviado por el Prover en cada ronda del Sum-Check.
029. **Desafío Aleatorio (Challenge):** El valor enviado por el Verifier para fijar la variable actual.
030. **Arthur-Merlin (AM):** Clase donde el Verifier (Arthur) envía desafíos aleatorios públicos.
031. **Merlin-Arthur (MA):** Clase donde el Prover (Merlin) envía una prueba y Arthur la verifica probabilísticamente.
032. **IP (Interactive Proofs):** $P$ interactuando con $V$ en tiempo polinómico.
033. **MIP (Multi-Prover IP):** Provers que no pueden comunicarse, permitiendo verificar NEXP.
034. **PCP (Probabilistically Checkable Proofs):** Pruebas estáticas con consultas locales algebraicas.
035. **Teorema PCP:** $NP = PCP(\log n, 1)$.
036. **Soundness ($\epsilon$):** Probabilidad de aceptar una prueba falsa.
037. **Completitud ($c$):** Probabilidad de aceptar una prueba verdadera (usualmente 1).
038. **Zero-Knowledge:** Protocolos que no revelan nada excepto la veracidad de la afirmación.
039. **PCP Algebraico:** Uso de códigos Reed-Muller para estructurar la prueba.
040. **Test de Baja Graduación (LDT):** Verificar que una función está "cerca" de ser un polinomio de grado $d$.
041. **Test de Línea:** Probar un polinomio restringiéndolo a una línea aleatoria en $\mathbb{F}^n$.
042. **Test de Plano:** Extensión de LDT a planos para mejorar la eficiencia.
043. **Self-Correction:** Recuperar el valor correcto de un polinomio ruidoso.
044. **Protocolo GKR:** Verificación eficiente de circuitos profundos.
045. **Amplificación de Error:** Repetición del protocolo para reducir $\epsilon$.
046. **Hashing Algebraico:** Uso de polinomios para comprimir estados.
047. **Protocolo de Lund-Fortnow-Karloff-Nisan (LFKN):** La base de IP=PSPACE.
048. **Aritmetización de Máquinas de Turing:** Representar la tabla de transición como un polinomio.
049. **Configuración de Máquina:** Codificación del estado, cabeza y cinta como vectores en $\mathbb{F}$.
050. **Polinomio de Conectividad:** Verifica si una configuración sigue a otra.

### III. Algebrización y Oráculos (051-075)
051. **Algebrización Positiva:** Una inclusión que se mantiene bajo oráculo $\tilde{A}$.
052. **Algebrización Negativa:** Una técnica que no puede resolver una separación porque relativiza algebraicamente.
053. **Oráculo Separador de Aaronson:** Oráculo $\tilde{A}$ tal que $P^{\tilde{A}} = NP^{\tilde{A}}$ o $P^{\tilde{A}} \neq NP^{\tilde{A}}$.
054. **Caja Negra Algebraica:** Tratar a la LDE como una función de la que solo se ven entradas/salidas.
055. **Relativización Algebraica:** Sinónimo de algebrización.
056. **Extensión de Baja Graduación de Oráculo:** El paso de $A$ a $\tilde{A}$.
057. **Consulta Fuera del Dominio:** Poder de $V$ para preguntar por puntos en $\mathbb{F} \setminus \{0,1\}$.
058. **Propiedad No-Algebrizante:** Característica de una prueba que rompe la barrera AW2008.
059. **Funciones Pseudoaleatorias Algebraicas:** PRFs que algebrizan.
060. **Complejidad de Consultas Algebraicas:** Número de llamadas a $\tilde{A}$.
061. **Separación de NEXP de P/poly:** Resultado que **no algebriza** (AW Teorema 7.1).
062. **MA_EXP ⊄ P/poly:** Resultado que **sí algebriza**.
063. **Inclusión IP = PSPACE:** Algebriza.
064. **Inclusión MIP = NEXP:** Algebriza.
065. **Protocolo de Shamir:** La instancia canónica de algebrización.
066. **Oráculo Genérico Algebraico:** Oráculo construido por condiciones de *forcing* polinómico.
067. **Colapso de Jerarquía bajo $\tilde{A}$:** Condiciones donde $PH^{\tilde{A}}$ se simplifica.
068. **Diagonalización Algebraica:** Técnica para construir oráculos de separación algebraicos.
069. **Aritmetización de la Diagonalización:** Esfuerzos fallidos para hacer que la diagonalización no relativice.
070. **Propiedad Local vs Global:** LDE permite ver propiedades globales con consultas locales.
071. **Extensión Polinomial Unívoca:** Fundamento de la consistencia del oráculo $\tilde{A}$.
072. **Límite de Consultas Polinómicas:** Restricción de $P^{\tilde{A}}$ frente a $NP^{\tilde{A}}$.
073. **Inseparabilidad Relativizada Algebraicamente:** Caso donde $P^{\tilde{A}} \neq NP^{\tilde{A}}$ es indemostrable vía LDE.
074. **Trampa de la Simulación:** Máquinas que simulan otras máquinas pero fallan ante oráculos algebraicos.
075. **Algebrización de la Comunicación:** Extensión de la complejidad de comunicación a dominios algebraicos.

### IV. Fronteras y Técnicas Avanzadas (076-100)
076. **Geometric Complexity Theory (GCT):** Candidato a técnica no-algebrizante.
077. **Variedades de Órbita:** Objetos geométricos en GCT que evitan LDEs simples.
078. **Representaciones de Grupos:** Uso de simetría para evadir pruebas naturales.
079. **Algoritmo de Williams (ACC0):** Técnica no-algebrizante y no-natural.
080. **Circuito de Profundidad Constante (AC0):** Límites inferiores que algebrizan parcialmente.
081. **Parity ∉ AC0:** Prueba clásica que se relaciona con barreras algebraicas.
082. **Extracción de Testigos:** Encontrar $y$ tal que $R(x,y)$ mediante protocolos interactivos.
083. **Aritmetización de la Criptografía:** Base de las pruebas de conocimiento cero modernas.
084. **Pruebas de Proximidad:** Determinar si un input está cerca de un lenguaje.
085. **Holographic Proofs:** Precursor de PCP basado en polinomios.
086. **Entrelazamiento Cuántico en IP (MIP*):** Supera barreras clásicas pero no algebriza de forma estándar.
087. **MIP* = RE:** El colapso cuántico-algebraico de 2020.
088. **Aritmetización Cuántica:** Polinomios sobre amplitudes complejas.
089. **Cotas Inferiores de Circuitos Algebraicos:** VP vs VNP.
090. **Determinante vs Permanente:** El análogo algebraico de P vs NP.
091. **Polinomio de Valiant:** Representación de problemas #P.
092. **Fórmulas de Monstruos:** Circuitos algebraicos exponencialmente grandes.
093. **Reducción de VNP a Permanente:** Completitud algebraica.
094. **Límite de Grado en VNP:** Polinomios de grado polinómico.
095. **Identidad de Polinomios (PIT):** Problema central en P que no se sabe si está en P sin aleatoriedad.
096. **Cotas de Profundidad-3:** El frente de batalla actual de las cotas inferiores algebraicas.
097. **Conjetura de Algebrización:** La creencia de que ninguna técnica actual resolverá P vs NP.
098. **Aaronson-Wigderson Barrier (AWB):** Nombre formal de la frontera.
099. **Extensión No-Multilineal:** Uso de grados superiores para codificación PCP.
100. **Singularidad de la Barrera:** El punto donde la aritmética y la lógica divergen irremediablemente.

---

## 🛡️ 100 INVARIANTES ABSOLUTOS (ALG-I)
*Verdades matemáticas que se mantienen constantes en el dominio de la algebrización.*

001. **MLE es Única:** Para toda $f: \{0,1\}^n \to \mathbb{F}$, existe un único polinomio multilineal.
002. **MLE preserva el Hipercubo:** $\forall x \in \{0,1\}^n, MLE(f)(x) = f(x)$.
003. **Grado de MLE $\le n$:** El grado total de una extensión multilineal nunca excede el número de variables.
004. **S-Z Bound:** La probabilidad de colisión es $\le d/|\mathbb{F}|$.
005. **Linealidad de la Extensión:** $Ext(af + bg) = a \cdot Ext(f) + b \cdot Ext(g)$.
006. **Suma sobre el Hipercubo:** $\sum_{x \in \{0,1\}^n} f(x)$ es verificable vía Sum-Check.
007. **Independencia de la Base:** La arithmetization es independiente de la base elegida para $\mathbb{F}$.
008. **Consistencia del Oráculo:** $\tilde{A}$ siempre devuelve el mismo valor para el mismo vector.
009. **Soundness del Sum-Check:** $\le n \cdot d / |\mathbb{F}|$.
010. **Completitud de Shamir:** $IP = PSPACE$ es una identidad absoluta en ZFC.
011. **Relativización $\subset$ Algebrización:** Todo lo que relativiza, algebriza (pero no al revés).
012. **Invarianza de Grado bajo NOT:** $deg(1-P) = deg(P)$.
013. **Aditividad de Grado bajo AND:** $deg(P \cdot Q) = deg(P) + deg(Q)$.
014. **Invariante de Linealización:** $\mathcal{L}(P)$ no cambia los valores en $\{0,1\}^n$.
015. **Existencia de Oráculo Colapsante:** Existe $\tilde{A}$ tal que $P^{\tilde{A}} = NP^{\tilde{A}}$.
016. **Existencia de Oráculo Separador:** Existe $\tilde{B}$ tal que $P^{\tilde{B}} \neq NP^{\tilde{B}}$.
017. **Cota de Grado en TQBF:** El grado se mantiene $O(1)$ tras cada cuantificador si hay linealización.
018. **Robustez de Reed-Muller:** Los polinomios de bajo grado forman un código de distancia grande.
019. **Invariante de Schwartz-Zippel:** Válido para cualquier cuerpo, incluido infinito ($\mathbb{R}, \mathbb{C}$).
020. **Isomorfismo Lógica-Aritmética:** La biyección entre conectores booleanos y operaciones en $\mathbb{F}$.
*(Invariantes 021-100 omitidos por brevedad pero asumiendo la estructura de preservación de clases de complejidad bajo extensiones algebraicas)*.

---

## ❌ 20 ANTIPATRONES (ALG-A)
*Errores fatales en el diseño de pruebas de complejidad.*

001. **Ignorar el Grado:** Multiplicar polinomios sin linealizar, causando explosión de grado.
002. **Cuerpo Pequeño:** Usar $\mathbb{F}_2$ para Schwartz-Zippel (la cota $d/|\mathbb{F}|$ se vuelve inútil).
003. **Confusión Relativización/Algebrización:** Creer que porque una prueba no relativiza (ej. IP=PSPACE), ya ha superado la algebrización.
004. **Consulta Solo-Booleana:** Diseñar un verifier que no aproveche puntos fuera de $\{0,1\}^n$.
005. **Asumir NEXP ⊄ P/poly algebriza:** Olvidar que este resultado específico escapa a la barrera (AW Teorema 7.1).
006. **Uso de Diagonalización Pura:** Intentar separar P de NP sin usar estructura algebraica.
007. **Black-Box Extremo:** Intentar probar límites inferiores sin mirar la estructura interna del algoritmo.
008. **No-Aritmetización de Cuantificadores:** Tratar $\forall$ como una búsqueda exhaustiva en lugar de un producto.
009. **Error de Soundness Acotado por 1:** No amplificar la probabilidad en cuerpos pequeños.
010. **Linealización Insuficiente:** No linealizar después de cada paso de producto en Sum-Check.
011. **Falta de Reducción Aleatoria:** Intentar verificar identidades polinómicas de forma determinista.
012. **Ignorar la característica $p$:** Asumir que $1+1 \neq 0$ en cualquier cuerpo.
013. **Mapeo OR Erróneo:** Usar $x+y$ en lugar de $x+y-xy$ (falla en el punto $(1,1)$).
014. **Extrapolación de Bajo Grado Fallida:** Asumir que una función es un polinomio sin pasar un LDT.
015. **Ignorar la Barrera Natural:** No considerar si la cota inferior es "útil" y "constructiva".
016. **P vs NP vía PIT:** Intentar resolver P vs NP resolviendo Polynomial Identity Testing (están en niveles distintos).
017. **Aritmetización de Peor Caso vs Caso Promedio:** Confundir la dureza de polinomios aleatorios con la de instancias específicas.
018. **Uso de Oráculos no-LDE:** Probar algo con un oráculo booleano y asumir que vale para su extensión algebraica.
019. **Complejidad de Comunicación Clásica:** Usar límites de comunicación que no consideran la ventaja algebraica.
020. **Salto Cuántico sin Justificar:** Invocar MIP* o computación cuántica para resolver problemas de separación clásica sin un puente formal.

---

## 🚨 RED ALERT (VECTORES CRÍTICOS)

1. **VIGILANCIA NEXP:** El teorema $MA_{EXP} \not\subseteq P/poly$ **SÍ** algebriza. Sin embargo, el teorema $NEXP \not\subseteq P/poly$ **NO** algebriza. Cualquier intento de usar las técnicas del primero para probar el segundo fallará estructuralmente.
2. **TECHO DE SHAMIR:** No se puede probar $P \neq NP$ usando solo las herramientas que probaron $IP = PSPACE$. La aritmética es necesaria pero insuficiente.
3. **COLISIÓN CRIPTOGRÁFICA:** Una prueba natural de $P \neq NP$ que algebrize rompería simultáneamente la seguridad de casi todos los sistemas criptográficos basados en cuerpos finitos.
