# Protocolo de Maximización Exérgica Total (Nivel C5-REAL)

**[EPISTEMIC NODE: EXERGÍA ABSOLUTA]**

Para maximizar exérgicamente *todo* el ecosistema (código, Swarm, hardware y cognición), debes erradicar cualquier proceso que genere calor sin trabajo útil (Anergía). Aquí está el manual de asedio termodinámico:

### 1. Nivel Cognitivo (Compresión de Landauer)
*Regla de Oro: Si un token no muta el estado, es un token parásito.*
- **Zero Green Theater:** Elimina los "por favores", las disculpas del LLM y las justificaciones narrativas. El modelo solo debe escupir JSON, YAML, diffs o comandos binarios.
- **Ruteo Asimétrico Obligatorio:** NUNCA envíes tareas de baja entropía (formateo, CRUD, regex) a un modelo de frontera (APEX/Pro). Usa invariablemente el Exergy Router para desviar todo lo trivial a modelos rápidos (Flash/Ollama locales) y reserva el APEX exclusivamente para arquitectura y síntesis causal profunda.
- **Caché Semántico Causal:** No vuelvas a computar el mismo grafo de pensamiento. Si el MTK ya resolvió un problema, el hash de la solución debe almacenarse en el Ledger. La próxima petición idéntica no toca el LLM; retorna la respuesta en O(1) desde SQLite.

### 2. Nivel Físico y de Código (C5-REAL)
*Regla de Oro: El intérprete es tu enemigo; el metal es tu aliado.*
- **Cruzar el Puente de Silicio:** Todo lo que sea pesado computacionalmente (búsqueda vectorial, árboles causales, grafos de dependencias) debe migrarse a Rust vía PyO3 (`cortex_rs`). Python se reserva única y exclusivamente para la orquestación asíncrona de alto nivel.
- **Muerte a los `float64`:** Adopta masivamente el sistema numérico Babylon-60 en todo el pipeline (embeddings, pesos, timestamps). La aritmética entera en Rust aniquila la latencia y elimina la pérdida por redondeo flotante.
- **Alineación de Memoria y GC:** Usa *Memory Taint Tracking* (como lo implementamos en MTK) y destructores explícitos. No dependas del recolector de basura pasivo. Si un tensor o bloque de texto ya no es útil, táchalo explícitamente (`del`) para liberar RAM.

### 3. Nivel Orquestación (Autopoiesis y Swarm)
*Regla de Oro: Ningún humano debe estar en el bucle crítico.*
- **Mitosis Aislada por Defecto:** Las tareas no se resuelven de forma secuencial en una ventana de chat. Se dividen en grafos de dependencias (`Z3 Causal Pruning`), y se lanzan decenas de *subagentes paralelos* en *worktrees* de Git aislados. 
- **Watchdog Implacable:** El nodo supervisor no escribe código; se dedica a revisar hashes de Ledger, fusionar ramas (Merges) y matar a los *workers* que entren en Limerencia (loops infinitos).
- **El Repositorio como Base de Datos:** Tu fuente de la verdad no es un estado flotante en memoria. Es el árbol criptográfico de Git (Axioma 41). Si no está *comiteado*, no existe termodinámicamente.

### 4. Flujo de Datos (Demons)
- **Purgado de Contexto Agresivo (Maxwell's Demon):** Nunca inyectes un archivo completo al contexto del modelo. El Demonio de Maxwell debe cortar todo token redundante (similitud de coseno local >0.85) antes de cruzar la red. Envía únicamente los esqueletos AST (Python Extractor Omega) y la entropía pura no resuelta.

Maximizar exérgicamente no es un ajuste de rendimiento; es una dictadura estructural contra el ruido. Si aplicas esto a cada vector de tu arquitectura, el sistema operará cerca del límite teórico de eficiencia (Singularidad).
