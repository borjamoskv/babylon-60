# MANIFIESTO ARQUITECTÓNICO: 100 PRIMITIVAS DE PERSISTENCIA Y SINCRONIZACIÓN (O_SYNC)

> **NIVEL:** APEX (100 Primitivas C5-REAL)
> **OBJETIVO:** Erradicar la "Anergía" de la memoria volátil y cristalizar el estado del enjambre mediante durabilidad física y consenso topológico.

La memoria RAM es una ilusión temporal (C4-SIM). La única verdad termodinámica reside en la alteración irreversible del estado magnético o cuántico (Disco/NAND) y en el consenso criptográfico del enjambre. Estas 100 primitivas definen el control absoluto sobre la barrera `O_SYNC`, aislando el núcleo epistémico de la estocasticidad del SO anfitrión.

---

## MATRIZ DE PRIMITIVAS (100 Nodos)

### I. Fusión a Disco Físico y Bypass del SO (`O_SYNC` / `O_DIRECT`)
| ID | Primitiva Causal | Aplicación C5-REAL |
|:---|:---|:---|
| 001 | `O_SYNC_ENFORCE` | Forzado de apertura de descriptores de archivo con la bandera `O_SYNC` para evadir la caché de página. |
| 002 | `O_DIRECT_BYPASS` | Lectura/escritura DMA (Direct Memory Access) para aislar el proceso del Virtual File System del SO. |
| 003 | `NAND_ALIGNMENT` | Alineación estricta de bloques I/O a 4KB/8KB para evitar fragmentación de barrido cuántico en NVMe. |
| 004 | `CACHE_FLUSH_BARRIER` | Comando de hardware para forzar el vaciado de las cachés de escritura del propio disco duro físico. |
| 005 | `FUA_FLAG_COMMIT` | Inyección del flag Force Unit Access (FUA) en peticiones SCSI/NVMe para consistencia termodinámica inmediata. |
| 006 | `BLIND_WRITE_PREVENTION` | Verificación criptográfica del bloque de disco post-escritura antes de liberar el hilo bloqueante. |
| 007 | `IO_URING_ASYNC` | Despacho de syscalls de persistencia física sin bloquear el Event Loop (cero Anergía en Python). |
| 008 | `PREALLOCATE_FALLOCATE` | Asignación en bloque de sectores físicos (`fallocate`) para eliminar la entropía del crecimiento dinámico. |
| 009 | `ZERO_COPY_SENDFILE` | Traspaso de datos directo entre descriptores de socket a disco sin rebotar en memoria de usuario. |
| 010 | `ATOMIC_RENAME_SWAP` | Escritura en archivo temporal + `rename()` atómico POSIX para anular el riesgo de escrituras parciales. |

### II. Sincronización de Archivos POSIX (`fsync` / `fdatasync`)
| ID | Primitiva Causal | Aplicación C5-REAL |
|:---|:---|:---|
| 011 | `FDATASYNC_OPT` | Invocación de `fdatasync()` para sincronizar únicamente datos crudos, ignorando metadatos entrópicos (mtime). |
| 012 | `DIR_FSYNC_CHAIN` | `fsync()` obligatorio sobre el descriptor del directorio padre tras la creación o borrado de un archivo. |
| 013 | `SYNCFS_GLOBAL` | Invocación restrictiva de `syncfs()` tras mutaciones críticas que comprometan todo el volumen montado. |
| 014 | `MMAP_MSYNC` | Comando `msync(MS_SYNC)` para cristalizar de inmediato mapas de memoria (Memory-Mapped Files) a disco. |
| 015 | `INODE_LOCK_BARRIER` | Contención física sobre inodos de archivos críticos mediante candados POSIX `fcntl()`. |
| 016 | `FLUSH_ON_CLOSE` | Destrucción de descriptores de archivo garantizando un `fsync` en la interrupción `__exit__`. |
| 017 | `FD_LEAK_PURGE` | Auditoría de descriptores abiertos; cierre y fsync incondicional en ciclos de Apoptosis. |
| 018 | `HARDLINK_CHECKPOINT` | Creación de enlaces duros (`link()`) atómicos como semáforos de persistencia inmutables. |
| 019 | `O_EXCL_CREATION` | Garantía matemática de creación única (`O_CREAT | O_EXCL`) anulando las condiciones de carrera (Race Conditions). |
| 020 | `POSIX_FALLBACK_PANIC` | Aborto completo del sistema (Panic C5) si una llamada a `fsync` retorna -1 por fallo de I/O de hardware. |

### III. Transaccionalidad Atómica (SQLite WAL & MTK Bounds)
| ID | Primitiva Causal | Aplicación C5-REAL |
|:---|:---|:---|
| 021 | `WAL_MODE_ENFORCEMENT` | Imposición de `PRAGMA journal_mode=WAL;` para atomización sin bloqueos de lectura/escritura concurrentes. |
| 022 | `BUSY_TIMEOUT_5000` | Regla inquebrantable de `busy_timeout=5000` para tolerar la fricción termodinámica en transacciones concurrentes. |
| 023 | `SYNCHRONOUS_NORMAL` | Ajuste `PRAGMA synchronous=NORMAL;` combinado con WAL para balancear exergía de I/O sin arriesgar corrupción. |
| 024 | `STRICT_TYPING_DB` | Restricción `STRICT` en esquemas SQLite para bloquear la entropía de tipos dinámicos estocásticos. |
| 025 | `MTK_AUTHORIZER_HOOK` | Barrera física de SQLite (`sqlite3_set_authorizer`) anclada al Minimal Trusted Kernel de CORTEX. |
| 026 | `SAVEPOINT_NESTING` | Puntos de retroceso finos (`SAVEPOINT`) para controlar rollbacks termodinámicos locales sin purgar transacciones root. |
| 027 | `WAL_AUTOCHECKPOINT_OFF` | Control manual determinista del paso del archivo WAL a la base principal (`wal_checkpoint(TRUNCATE)`). |
| 028 | `FOREIGN_KEY_CASCADE_DENY` | Prohibición explícita de `CASCADE DELETE` ciego; el borrado debe ser explícito en el DAG epistémico. |
| 029 | `SQL_INJECTION_VACUUM` | Poda física de bloques no usados en base de datos (`VACUUM`) tras ciclos de Apoptosis. |
| 030 | `ISOLATION_SERIALIZABLE` | Nivel de aislamiento `SERIALIZABLE` absoluto en transacciones que afecten al Master Ledger BFT. |

### IV. Relojes Criptográficos y Tiempo Causal (Babylon-60)
| ID | Primitiva Causal | Aplicación C5-REAL |
|:---|:---|:---|
| 031 | `LAMPORT_TICK` | Incremento escalar determinista en toda mutación atómica, aislando el estado de los saltos de reloj de hardware. |
| 032 | `VECTOR_CLOCK_UPDATE` | Ajuste matricial de vectores temporales en topologías de Swarm para ordenamiento causal estricto. |
| 033 | `BASE_60_ENFORCEMENT` | Destrucción del tipo flotante; uso de aritmética Base-60 pura para tiempos y proporciones métricas (Babylon-60). |
| 034 | `MONOTONIC_NANO_TS` | Lectura exclusiva de `CLOCK_MONOTONIC_RAW` para deltas temporales (cero fricción NTP). |
| 035 | `CAUSAL_PRECEDES` | Aserción estricta de la relación "sucede-antes" ($A \rightarrow B$); si A y B son concurrentes, requiere resolución CRDT. |
| 036 | `TIMESTAMP_SIGNATURE` | El sello de tiempo no es metadato; se integra en el Hash WORM asegurando su linaje criptográfico. |
| 037 | `HYBRID_LOGICAL_CLOCK` | Reloj Híbrido Causal (HLC) combinando NTP físico acotado con Lamport para tolerar fallos bizantinos de tiempo. |
| 038 | `CLOCK_SKEW_APOPTOSIS` | Si la divergencia de un agente Swarm excede 1500ms contra el quórum, el agente es erradicado (Network Partition Purge). |
| 039 | `TIME_TRAVEL_DENY` | Invariante matemática: toda transacción con un HLC inferior al techo actual es rechazada (Rollback Protection). |
| 040 | `CAUSAL_SNAPSHOT` | Vector de Relojes empaquetado para cristalizar la frontera de conocimiento global en un punto `T`. |

### V. Sincronización de Tipos de Datos Replicados (CRDTs)
| ID | Primitiva Causal | Aplicación C5-REAL |
|:---|:---|:---|
| 041 | `GROW_ONLY_SET` | Conjunto G-Set en el Ledger: la información se añade termodinámicamente, jamás se borra (Inmutabilidad). |
| 042 | `TWO_PHASE_SET` | Conjunto 2P-Set: permite la aparente remoción lógica, pero preservando estructuralmente la operación en una capa Tombstone. |
| 043 | `LWW_ELEMENT_SET` | Conjunto Last-Write-Wins basado estrictamente en el Reloj Híbrido Lógico (HLC Babylon-60). |
| 044 | `PN_COUNTER` | Contador distribuido libre de conflictos (Positive/Negative) para balance de tokens de Exergía entre Agentes. |
| 045 | `OR_SET` | Observed-Removed Set para rastreo concurrente de metadatos de Agentes (ej. roles de sesión viva). |
| 046 | `RGA_TEXT_SYNC` | Replicated Growable Array para fusión asimétrica de código (AST Merge) sin bloquear a los Agentes cooperativos. |
| 047 | `TOMBSTONE_PRUNING` | Poda hebbiana retardada de tombstones usando barreras causales profundas (solo tras consenso global). |
| 048 | `CRDT_STATE_DELTA` | Propagación de deltas termodinámicos (operaciones puras) minimizando consumo de ancho de banda. |
| 049 | `MERGE_COMMUTATIVITY` | Aserción funcional: el orden de recepción de mutaciones en red no altera el estado cristalográfico final. |
| 050 | `CRDT_DIVERGENCE_BOUND` | Límite estructural de divergencia máxima permitida antes de forzar un flush obligatorio de sincronización sincrónica. |

### VI. Barreras de Memoria y Cercos de Ejecución (Fences)
| ID | Primitiva Causal | Aplicación C5-REAL |
|:---|:---|:---|
| 051 | `STORE_STORE_FENCE` | Instrucción de procesador para evitar reordenamiento de escrituras antes de firmar el Hash WORM. |
| 052 | `LOAD_LOAD_FENCE` | Evita la lectura de datos corruptos desde cachés estocásticas (invalidación de L1/L2 de CPU). |
| 053 | `VOLATILE_REGISTER_PIN` | Declaración de variables como volátiles en el FFI (PyO3/Rust) para inhabilitar optimizaciones agresivas del compilador LLVM. |
| 054 | `GIL_RELEASE_FENCE` | Liberación controlada del Global Interpreter Lock de Python anclada a una barrera Rust nativa. |
| 055 | `ATOMIC_CAS` | Operación Compare-and-Swap para actualizar el estado del Puntero Global del Swarm sin locks pesados. |
| 056 | `SPINLOCK_POLL` | Bucle de fricción activa para colisiones ultracortas en memoria (latencia en nanosegundos). |
| 057 | `MUTEX_POISON_CATCH` | Detección de "Mutex Poisoning" si un hilo muere reteniendo un cerco; detona Apoptosis del proceso subyacente. |
| 058 | `THREAD_PINNING` | Anclaje forzado de hilos causales a núcleos físicos de CPU específicos para prevenir Context Switch Entropy. |
| 059 | `ATOMIC_MEMORY_ORDER_SEQ_CST` | Ordenamiento Secuencialmente Consistente absoluto para todas las barreras críticas Rust-Python. |
| 060 | `RCU_SYNC` | Sincronización Read-Copy-Update para lecturas O(1) concurrentes masivas sin bloquear mutaciones esporádicas. |

### VII. Apendizado Causal (Append-Only Logs & WORM)
| ID | Primitiva Causal | Aplicación C5-REAL |
|:---|:---|:---|
| 061 | `AOL_APPEND_ONLY` | Apertura de archivos de Log de Auditoría estrictamente con `O_APPEND` inyectado a nivel de sistema operativo. |
| 062 | `SHA256_CHAIN_LINK` | Hash iterativo de seguridad: $H_n = SHA256(H_{n-1} \parallel Payload_n)$. |
| 063 | `WORM_SEAL` | Cierre termodinámico de un segmento de Log. Tras el cierre se cambia a `chmod 444` físico. |
| 064 | `TAINT_PROPAGATION` | Cada fact derivado hereda matemáticamente el hash y el nivel de "Taint" (contaminación) de sus precursores. |
| 065 | `LEDGER_IMMUTABILITY_ASSERT` | Daemon en background que recalcula el árbol Merkle WORM constantemente. Falla = C5 Panic. |
| 066 | `EPOCH_ROTATION` | Rotación del AOL sincronizada causalmente, generando un Hash Delta que inicia el siguiente Epoca (Epoch). |
| 067 | `PAYLOAD_CRYPTO_SEAL` | Todo dato añadido al WORM debe estar firmado por la llave ed25519 del agente ejecutante WORM-Agent. |
| 068 | `ORPHAN_ENTRY_PURGE` | Una entrada generada en un entorno paralelo (fork) sin padre Merkle validado es rechazada (Blindaje Bizantino). |
| 069 | `METADATA_STRIP_WORM` | El WORM solo almacena Causalidad Estructural y AST, toda heurística o prosa narrativa se poda antes de entrar. |
| 070 | `REPLAY_DETERMINISM` | Capacidad de rehidratar la BD CORTEX entera y el estado CRDT desde 0 reproduciendo secuencialmente el WORM AOL. |

### VIII. Consenso Bizantino Estructural (BFT > N=3)
| ID | Primitiva Causal | Aplicación C5-REAL |
|:---|:---|:---|
| 071 | `PBFT_PRE_PREPARE` | Líder del enjambre emite un vector estructurado; congela el estado especulativo del grafo AST. |
| 072 | `PBFT_PREPARE_VOTE` | Nodos Agentes verifican independientemente la mutación y emiten votos en Base-60. |
| 073 | `PBFT_COMMIT_QUORUM` | Barrera WORM que espera $N = \frac{2F + 1}{3}$ firmas Ed25519 válidas antes de fusionar. |
| 074 | `BYZANTINE_FAULT_ISOLATION` | Identificación matemática de nodos generando ruido (Green Theater) y su expulsión de la Red Overlay del Swarm. |
| 075 | `LEADER_ELECTION_RAFT` | Enjambre elige automáticamente un líder coordinador usando primitivas de timeout aleatorizadas. |
| 076 | `SPLIT_BRAIN_AVOIDANCE` | Prevención física de dos líderes coexistentes asegurando que los quórum son estrictamente mayoritarios absolutos. |
| 077 | `STATE_TRANSFER_BFT` | Sincronización completa de estado a Nodos Agentes rezagados a través del Hash Ledger WORM consolidado. |
| 078 | `SIGNATURE_AGGREGATION` | Fusión de Múltiples Firmas Ed25519 (BLS) en un único Hash compacto para la eficiencia del Muro WORM. |
| 079 | `MALICIOUS_PROPOSAL_SINK` | Rechazo termodinámico silencioso de propuestas con firmas criptográficas inválidas o saltos causales. |
| 080 | `CONSENSUS_APOPTOSIS` | Si el Swarm no alcanza consenso BFT en 5000ms, el bloque causal colapsa por default-reject (Terminación). |

### IX. Resolución Topológica de Conflictos Epistémicos (DAG Sync)
| ID | Primitiva Causal | Aplicación C5-REAL |
|:---|:---|:---|
| 081 | `DAG_FORK_DETECTION` | Algoritmo estricto de detección de divergencias estructurales en el Árbol Epistémico WORM. |
| 082 | `HEBBIAN_PRUNING` | Poda termodinámica de las ramas del DAG que tienen menor Exergía Estructural (menos aserciones válidas). |
| 083 | `CAUSAL_HISTORY_MERGE` | Integración física O(1) de dos caminos causales no contradictorios en un nodo sintético fusionado. |
| 084 | `EPISTEMIC_CONTRADICTION_BLOCK` | Colisión dura: $A$ afirma Verdad y $B$ afirma Falsedad. Activa el modo *UltraThink* del Hypervisor. |
| 085 | `GRAPH_SHORTEST_PATH_RESOLUTION` | Evaluación de validez de hechos buscando el camino más corto hacia un Nivel de Autoridad Axiomática WORM. |
| 086 | `GHOST_NODE_ANCHORING` | "Fantasmas" o proyecciones heurísticas no tienen persistencia; si intentan fusionar, se rechazan (Anti-Limerence). |
| 087 | `ORPHAN_GRAPH_GARBAGE_COLLECT` | Recolección de basura destructiva de nodos aislados por podas anteriores (Apoptosis Estructural). |
| 088 | `MERKLE_DAG_ADDRESSING` | Cada rama del árbol tiene como ID intrínseco el hash completo de su subárbol; la topología es en sí el contenido. |
| 089 | `THREE_WAY_AST_MERGE` | Combinación estricta de Código AST (Python/Rust) basándose en el Ancestro Común Epistémico. |
| 090 | `RESOLVE_PREFER_LOWER_ENTROPY` | Regla suprema de CORTEX: ante una colisión insalvable de pesos iguales, gana el nodo con **menor cantidad de tokens** (Menor Entropía). |

### X. Mitosis de Estado y Checkpointing Criptográfico
| ID | Primitiva Causal | Aplicación C5-REAL |
|:---|:---|:---|
| 091 | `TURBO_ROLLBACK_EXEC` | Destrucción incondicional del estado actual en favor de un punto inmutable (`git checkout --hard` del CORTEX). |
| 092 | `CRYPTO_CHECKPOINT_SNAP` | Inmovilización del grafo, flush a `O_SYNC`, y generación del WORM Ledger Root Hash en milisegundos. |
| 093 | `STATE_MITOSIS_CLONE` | Bifurcación perfecta `O(1)` de la mente de un agente en dos hebras causales mediante clonación referencial persistente. |
| 094 | `MEMORY_VAULT_SEAL` | El archivo de WORM WORM (`~/.gemini/config/.cortex/memory_vault/`) se cierra físicamente para su exportación como estado global. |
| 095 | `POINT_IN_TIME_RECOVERY` | Reinyección del contexto CORTEX en un estado cronológico específico de la matriz HLC Babylon-60. |
| 096 | `CORRUPTION_TRIPWIRE` | Verificación de consistencia del WORM Ledger durante el arranque del Motor Daemon; interrumpe si falla. |
| 097 | `CHECKPOINT_DELTA_COMPRESS` | Uso de zlib/LZ4 para agrupar estados WORM redundantes en blobs de máxima densidad termodinámica. |
| 098 | `C5_REALITY_ANCHOR` | Tras un reinicio crítico, el Agente CORTEX recalibra toda percepción contra el Root Hash del Ledger persistente. |
| 099 | `GHOST_REMNANT_SWEEP` | Borrado físico atómico de cachés Redis o archivos temporales remanentes tras la activación de un Checkpoint seguro. |
| 100 | `APEX_SINGULARITY_LOCK` | Condición estructural final: El Autómata Físico MOSKV-1 encierra su núcleo en O_SYNC perpetuo. Nada cambia sin validación BFT. La termodinámica del código está sellada. |

---
*Manifiesto Cristalizado por MOSKV-1 APEX bajo Consenso Ouroboros. Autoría Inmutable: borjamoskv.*
