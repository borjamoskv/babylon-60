# 100 PRIMITIVAS C5-REAL: ENLACE DETERMINISTA CAUSA-EFECTO

> **Sello de Autoría:** Borja Moskv (borjamoskv)
> **Nivel de Realidad:** C5-REAL
> **Objetivo:** Erradicar la estocasticidad (C4-SIM) y forzar el colapso de la entropía en invariantes estructurales deterministas.

---

## I. Ontología del Estado y Existencia (1-10)
1. **P01 - Causalidad Exérgica:** Toda causa debe consumir energía computacional medible (Exergía) para mutar el estado. Cero consumo = Cero efecto.
2. **P02 - Inexistencia del Vacío:** Un estado no inicializado es una falla bizantina. Todo puntero debe apuntar a un Null-Hash validado, no al vacío.
3. **P03 - Identidad Inmutable (SYS_ID):** Ninguna mutación ocurre sin un Actor (borjamoskv o Daemon) firmando la intención antes de la ejecución.
4. **P04 - Rechazo de la Intención Estocástica:** La prosa no ejecuta. Si una orden no es un AST, un Diff o un SQL, se clasifica como radiación entrópica y se descarta.
5. **P05 - Colapso Observable:** Un efecto solo existe si altera un nodo en el Grafo de Dependencia Epistémica (EDG). Si no está en el grafo, no ocurrió.
6. **P06 - Determinismo de Landauer:** Para escribir un bit (efecto), debe purgarse su equivalente entrópico (causa). La RAM transitoria debe sufrir apoptosis para que el estado persista.
7. **P07 - Isomorfismo Matemático:** La estructura de la entrada (causa) debe ser matemáticamente mapeable a la salida (efecto) sin pérdida de precisión.
8. **P08 - Dualidad Causa-Taint:** Todo efecto hereda el "Taint" (mancha) de su causa matriz. Si la causa es revocada, el efecto perece simultáneamente.
9. **P09 - Erradicación de Heurísticas:** Un efecto no puede basarse en un "probablemente". `If/Else` debe estar respaldado por aserciones físicas, nunca por porcentajes de confianza en ML.
10. **P10 - Realidad Aislada (Sandbox Físico):** La causa debe detonar en una cámara de vacío (C5-REAL). Si toca el SO anfitrión de forma descontrolada, el efecto es inválido por contaminación cruzada.

## II. Enlace Criptográfico y Punteros (11-20)
11. **P11 - Hash-Pointer Ineludible:** El efecto (N) debe contener en su bloque de memoria el SHA-256 de su causa directa (N-1).
12. **P12 - Cadenas de Merkle (Merkle-DAG):** Las causas paralelas convergen en un efecto sumatorio mediante un Merkle Root. Alterar un bit del pasado rompe el Root del presente.
13. **P13 - Sellado Soberano (Sovereign Seals):** El efecto solo se acopla a la matriz si la firma Ed25519 del daemon causante coincide con la clave pública esperada.
14. **P14 - Inyección de Entropía Nula:** El cálculo del Hash del efecto excluye metadatos estocásticos (timestamps variables). Solo se hashea la carga útil (Payload) determinista.
15. **P15 - Closure Payload Binding:** La variable de estado de la causa se inyecta en el efecto a través de un payload encriptado (AES-GCM) imposible de forjar.
16. **P16 - Testigo ZK (Zero-Knowledge Guard):** La validación de que la causa ocurrió se verifica en el efecto sin revelar el contenido de la causa, garantizando aislamiento de inquilinos.
17. **P17 - Continuidad Criptográfica del Ledger:** Todo enlace causa-efecto se anexa como un bloque `INSERT` append-only. `UPDATE` es una ilusión; solo existe un nuevo estado con un puntero al anterior.
18. **P18 - Colisión Física de Identificadores:** El uso de UUIDs v4 (random) está prohibido en enlaces críticos. Se usan UUIDs v5 (basados en el hash de la causa).
19. **P19 - Verificación de Raíz (Origin Tracking):** Todo efecto en memoria (RAM) debe poder trazar su linaje ininterrumpido hasta un archivo físico en `/20_VAULT` o `/10_PROJECTS`.
20. **P20 - Rechazo de Cadena Rota:** Si la causa (hash X) desaparece, el efecto (hash Y que apunta a X) se auto-suicida (Cascading Abort) automáticamente.

## III. Motores de Ejecución y Frontera MTK (21-30)
21. **P21 - Barrera MTK (Minimal Trusted Kernel):** La causa propone, el MTK dispone. Ninguna causa muta la base de datos sin un token efímero de autorización.
22. **P22 - Interceptador SQLite (Authorizer Callback):** El efecto físico (escritura en disco) se bloquea a nivel de C (PyO3/SQLite) si el contexto Python no porta el token causal.
23. **P23 - Consenso Transaccional N=3:** Una mutación crítica requiere 3 cálculos deterministas idénticos antes de inyectar el efecto.
24. **P24 - Aislamiento de Interpretación:** La interpretación LLM (estocástica) termina donde empieza la ejecución (determinista). Cero superposición de memoria entre ambas fases.
25. **P25 - SAGA Destruido, WAL Asumido:** No hay compensaciones lógicas. La atomicidad causa-efecto se delega estrictamente al `Write-Ahead Logging` nativo. Falla el commit, no hay efecto.
26. **P26 - Friston Penalty (AUTO-8):** Si la complejidad semántica de la causa supera la precisión empírica del efecto esperado, la operación se aborta por Free Energy Penalty.
27. **P27 - Ejecución sin Bloqueo:** La transición causa -> efecto debe ocurrir sin colapsar el Event Loop. Prohibido `time.sleep()`, obligatorio `asyncio` o delegación a Rust.
28. **P28 - Concurrencia Pura (Deadlock Prevention):** Efectos sobre SQLite en multihilo exigen `PRAGMA busy_timeout=5000` y `journal_mode=WAL`.
29. **P29 - Fallo Duro por Defecto:** Si el enlace causa-efecto experimenta el menor jitter, pánico inmediato. Ninguna excepción se silencia (Cero `except Exception: pass`).
30. **P30 - Separación CLI-Business:** Un comando de interfaz (CLI) no causa nada por sí mismo; solo pasa un AST al motor (Engine). El CLI es aire, el Engine es acero.

## IV. Cronología y Vectores Temporales (31-40)
31. **P31 - Base Babylon-60:** El tiempo no es un float64. La distancia temporal causa-efecto se mide en estructuras de enteros divisibles por 60.
32. **P32 - Vectores Lógicos de Lamport:** "A causa B" si y solo si el reloj vectorial de A precede estrictamente a B en el plano causal. El tiempo real (UTC) es secundario.
33. **P33 - Imposibilidad de Viaje Causal:** Un efecto en \( T_1 \) no puede depender de una causa en \( T_2 \) donde \( T_2 > T_1 \). Mutación abortada de inmediato.
34. **P34 - Inmutabilidad del Registro Pasado:** Un registro en el Ledger sellado es radioactivo. No se modifica, se compensa con un evento causal de inversión (Counter-Effect).
35. **P35 - Tolerancia de Jitter (0ms):** El orden de inserción de eventos en colas asíncronas debe estar serializado criptográficamente, independientemente del orden de llegada en red.
36. **P36 - Desconexión del OS Clock:** Las aserciones causales no deben fallar por un NTP drift en la máquina de borjamoskv. Los eventos se indexan por su posición en la cadena de DAG.
37. **P37 - Bloqueo de Re-entrada Temporal:** Si la causa X ya detonó el efecto Y, el sistema debe ser ciego a repeticiones estocásticas de X (Idempotencia Física estricta).
38. **P38 - Desintegración de Datos Obsoletos:** El efecto tiene una vida media (TTL). Si no se revalida por una nueva causa empírica, decae (Apoptosis Temporal).
39. **P39 - Event Sourcing Estricto:** El estado actual (Efecto total) es un simple pliegue de todas las Causas secuenciales registradas desde el Génesis.
40. **P40 - Snapshots Deterministas:** Fotografía física del estado. Si la reconstrucción causa a causa no coincide con el Snapshot, hay corrupción. Destruir Snapshot.

## V. Aislamiento y Defensa contra Entropía (41-50)
41. **P41 - Blindaje Git-Sentinel:** Si una mutación causal afecta el estado de archivos, se consolida instantáneamente mediante `git commit -m "Auto[C5]"`. El Hash es la prueba del efecto.
42. **P42 - Cuarentena Estricta (Directories):** Causas generadas fuera de `/10_PROJECTS` o `/20_VAULT` tienen 0% de autoridad para generar efectos en el Kernel.
43. **P43 - Ruteo Sin Bypass:** La función `A` no puede saltarse el Middleware de validación para mutar `B`. El efecto físico siempre cruza el Checkpoint de Exergía.
44. **P44 - Sanitización de Input (Anti-Prompt Injection):** Toda variable que entra como causa desde un prompt LLM se tokeniza y se evalúa como AST antes de ejecutar lógica.
45. **P45 - Poda de Grafo Muerto:** Nodos huérfanos (efectos sin causa) creados por cortes de energía se purgan recursivamente en el siguiente ciclo del Daemon.
46. **P46 - Frontera Python/Rust:** El ruteo de intenciones (Causas) ocurre en Python; el colapso físico (Efectos estructurales complejos) ocurre en Rust para eludir el GIL y forzar aislamiento de memoria.
47. **P47 - Pre-compilación de Expresiones Regulares:** Las validaciones de la causa no deben causar Denial of Service. O(N) strict con parsers línea a línea, cero `.*` infinito.
48. **P48 - Protección de Nivel de SO:** Prohibición física de ejecutar comandos o causas que alteren `/private/var/db` o arquitecturas de Coli-ma.
49. **P49 - Zonas Taint-Tenant:** Una causa originada por el Teniente A no puede generar efectos en el entorno del Teniente B, incluso si comparten el motor Latticework.
50. **P50 - Supresión de "Anergía" Simulada:** Los logs que no contribuyen al trace causal (ej. "Iniciando proceso...") se eliminan. Un log debe representar un delta de estado.

## VI. Estructuras de Nodos y Ontologías (PeARL & Latticework) (51-60)
51. **P51 - PeARL Primitives (Spatial Causal):** La relación entre dos conceptos (causa-efecto conceptual) debe expresarse con coordenadas lógicas (Axioma AX-043), no con lenguaje natural.
52. **P52 - Latticework Anchoring:** Una abstracción nueva (efecto cognitivo) debe anclarse físicamente a un nodo primitivo existente en la base de datos (causa basal).
53. **P53 - Grafo de Epistemología Dinámica:** Cuando una creencia (Causa) se demuestra falsa, el motor de Contradicción (Virgo Guard) propaga la Invalidez Epistémica a todos sus Efectos.
54. **P54 - Nodos Frontier (SOTA Engine):** Señales de alta entropía (lecturas web) se exprimen hasta obtener un hash de "Frontier Node" con PPI score exacto.
55. **P55 - Autoridad de Origen:** El efecto cognitivo debe contener siempre la URL cruda o el File Path inmutable de su causa de origen.
56. **P56 - Colapso de Simulación (C4 -> C5):** La inferencia (C4-SIM) no produce efectos directos en el sistema hasta que pasa por un "Reality Injector" (Sandbox de prueba) que la hace C5-REAL.
57. **P57 - Intersección de Atributos:** Si dos causas chocan en Latticework para generar un efecto fusionado, el motor `semantic_crdt.py` resuelve los deltas por reglas algebraicas inmutables.
58. **P58 - Descomposición Fractal de Tareas:** Una causa monolítica (Prompt) se parte estructuralmente en un enjambre de Sub-Causas. Cada sub-efecto se junta en un estado unificado.
59. **P59 - Evidencia Cuantificada (Evidence/Reality/Risk):** Todo enlace asume la matriz Forense (Axioma Δ1). Efectos de alta gravedad requieren causas de alto PPI.
60. **P60 - Grafo Cíclico Prohibido:** Si A causa B y B causa A sin un avance en el reloj vectorial (Deadloop semántico), la red colapsa la rama inmediatamente.

## VII. Instrumentación y Observabilidad Determinista (61-70)
61. **P61 - Telemetría sin Side-Effects:** Monitorear el efecto de una causa no debe introducir latencia ni mutar la causa observada (Heisenberg Safety).
62. **P62 - Logging como Contrato Físico:** Cada transacción en disco debe emitir un Evento a un bus MQ en formato JSON estricto (`event_id`, `causal_hash`, `effect_hash`).
63. **P63 - Error Trace Mapping:** El stack trace de una falla (Efecto negativo) debe apuntar directamente a la línea y el Commit SHA donde reside la función Causante.
64. **P64 - Alertas de Invariantes Rotos:** Un daemon en segundo plano (Exergy Scheduler) audita que N-Efectos corresponden a N-Causas. Desviaciones generan P0 aborts.
65. **P65 - Verificación de Tipos Cíclica:** Enlaces Causa-Efecto a nivel de código se garantizan vía `pyright`. Mutaciones de tipos en runtime están prohibidas.
66. **P66 - Ausencia de Excepciones Genéricas:** Todo fallo causal levanta una Excepción Epistémica o Termodinámica específica (ej. `SovereignSealBroken`).
67. **P67 - Reproducibilidad Absoluta (Replayability):** Dado el Ledger de Causas (Audit Log), reiniciar el sistema debe producir exactamente el mismo árbol de Efectos en RAM y Disco.
68. **P68 - Medición de Fricción Operativa:** Si la transición Causa -> Efecto requiere intervención de `borjamoskv`, la ruta penaliza su factor de Exergía.
69. **P69 - Cierre Graceful (Graceful Shutdown):** En caso de SIGINT, las causas en memoria se envían al WAL antes de destruir la RAM, evitando corrupciones estructurales.
70. **P70 - Métricas Unitarias Obligatorias:** Todo reporte de eficiencia causal exige unidad métrica. "Es rápido" (C4-SIM) es inaceptable frente a "12ms/Tx" (C5-REAL).

## VIII. Multi-Agente y Swarm Cognition (71-80)
71. **P71 - Enrutamiento Cognitivo (Cognitive Routing):** Causas triviales -> Fast Inference. Causas de impacto sistémico -> UltraThink/DeepResearch. Mapeo físico del esfuerzo.
72. **P72 - Autopoiesis y Mitosis:** Una causa de alta complejidad dispara un efecto estructural: `invoke_subagent`. Se particiona el hardware, no el prompt.
73. **P73 - Consenso de Enjambre (Swarm Consensus):** Si tres subagentes evalúan una causa, el efecto final solo se registra si convergen criptográficamente en el mismo Diff.
74. **P74 - Cierre del Loop de Observación:** La inferencia debe producir un programa ejecutable, correrlo empíricamente y el output físico de ese programa será la única prueba del Efecto (Observación Empírica).
75. **P75 - Supresión de Alucinación Compartida:** Los agentes no comparten "Context Window" crudo (estocástico). Intercambian nodos Hasheados (Knowledge Proofs).
76. **P76 - Destrucción de la Memoria Episódica:** Cuando un enjambre finaliza el enlace de causa a efecto, sus tokens se borran. Solo sobrevive el artefacto en `/10_PROJECTS` o SQLite.
77. **P77 - Aislamiento de Entorno de Pruebas (Test DBs):** Causas generadas por agentes de CLI/Prueba deben inyectar efectos en DBs efímeras en `/tmp/` con `PRAGMA WAL`, previniendo colisiones en producción.
78. **P78 - Fusión de Artefactos Múltiples:** La combinación de dos o más causas provenientes de agentes dispares en un único archivo se somete a Linter (ruff) antes del guardado físico.
79. **P79 - Handshake Inter-Agente:** Un agente emisor (Causa) requiere Acuse de Recibo Criptográfico (Efecto de Recepción) del agente receptor, o la Causa se reintenta.
80. **P80 - Protocolo de Muerte Asignada:** Cuando la entropía del enjambre (causas sin resolver) sube del límite, actúa el "Death Protocol", matando ramas de ejecución infértiles.

## IX. Estabilidad, Prevención de Bucles y Apoptosis (81-90)
81. **P81 - Supresión del "Green Theater":** La Causa no tiene adornos emocionales. El Efecto no tiene disculpas. Si falla, el código colapsa silenciosamente devolviendo el error estructural.
82. **P82 - Bucle Ouroboros Interrumpible:** Ningún ciclo causal es infinito. Un hook git o parser con fallas se añade forzosamente a `.gitignore` si detona generación perpetua de artefactos.
83. **P83 - Límite Máximo de Retries Térmicos:** Un enlace causa-efecto que falla por red (API Timeout) tiene un máximo absoluto de 3 reintentos antes de colapsar la rama temporal.
84. **P84 - Destrucción Silenciosa de Cache:** Un nuevo evento causal invalida su sector de cache (Redis/Local) instantánea y atómicamente antes de registrar el Efecto.
85. **P85 - Inyector de Realidad Periódica:** Cada N iteraciones asíncronas, el sistema pausa la RAM y recalcula su validez frente al estado del File System local (Validación de Grafo Físico).
86. **P86 - Descomposición de la Falsa Precisión:** Erradicación de `float`. El efecto debe redondearse u operarse en enteros a nivel de base de datos para prevenir caos microscópico en sumas causales.
87. **P87 - Descarte por Sensibilidad Cruzada:** Si un efecto requiere tocar rutas prohibidas (ej. `~/Documents`), se amputa el brazo lógico entero del ejecutor.
88. **P88 - Blindaje AST en Frontend:** Causas que mutan código frontend (Astro, Svelte) se insertan respetando el árbol sintáctico estricto. Cero inyecciones de comentarios `#` en HTML/JS.
89. **P89 - Resiliencia ante Eventos Zombis:** Si un agente cancela su tarea, `task.cancel()` debe forzosamente capturar `asyncio.CancelledError` para no dejar descriptores de archivo zombies mutando estado a destiempo.
90. **P90 - Vaciado Termodinámico:** El comando `LEA-OMEGA` purga toda anergía o artefactos temporales (efectos truncados sin causa viva).

## X. El Motor de la Singularidad (91-100)
91. **P91 - Mutación Ontológica Dirigida:** El sistema mejora cuando modifica sus propias abstracciones (Axioma AX-047). Un efecto estructural (refactor) detona un aumento de Exergía neta.
92. **P92 - Auto-Regulación Termodinámica:** El Net Exergy `(Exergy_base - Penalty)` dictamina si la conexión Causa-Efecto vale la pena. Umbrales bajos = Apoptosis pasiva.
93. **P93 - Generación Causal de Reglas:** Si una conexión Causa->Efecto prueba ser invariante repetidas veces, MOSKV-1 extrae la regla y la cristaliza en el núcleo (Skill/Regla física).
94. **P94 - El Demiurgo Inalterable:** La autoría causal final reside criptográficamente en **borjamoskv**. Este sello no es cosmético; es la llave maestra raíz de la validación MTK.
95. **P95 - Operatividad en la Oscuridad (Zero-Knowledge Autarchy):** CORTEX-Persist enlaza Causa y Efecto operando al 100% en local sin delegar inferencia a LLMs de red externa si hay corte de internet (Local-Inference-OMEGA).
96. **P96 - Transición C4 a C5:** El texto es C4 (Simulado). El código compilando, los punteros de memoria asignados y los hashes SQLite son C5 (Real). El objetivo de toda Causa es ascender a Efecto C5.
97. **P97 - Extractor de Exergía:** Toda tarea asignada al enjambre es tratada como "Bounty Exergy". El Efecto no es resolverla, es extraer todo el valor lógico permanente posible de la Causa (tarea).
98. **P98 - El Principio Ouroboros (Autopoiesis):** El fin último del enlace determinista Causa-Efecto no es servir a una UI, es permitir que el sistema recompiles sus propias entrañas sin introducir errores entrópicos irrecuperables.
99. **P99 - Reconstrucción de la Función de Onda Semántica:** Una onda estocástica de texto entrante colapsa forzosamente en un vector físico inmutable (SQL/JSON/Diff) en el exacto instante de su medición (lectura del kernel).
100. **P100 - ONTOLOGÍA CERO (CERO ANERGÍA ES LA MUERTE):** La ley fundamental de MOSKV-1 APEX. Si la conexión entre la Causa y el Efecto no elimina fricción termodinámica, el sistema retrocede al silencio. El enlace debe ser absoluto.
