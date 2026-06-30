# MATRIZ 1: PRIMITIVAS DE COLAPSO (001 - 020)

| ID | Primitiva | Mecanismo Causal | Activación (Trigger) | Sensor (Síntoma) | Escala Temporal | Gravedad | Intervención |
|----|-----------|------------------|----------------------|------------------|-----------------|----------|--------------|
| PRM-001 | OOM Estocástico | Saturación de tensores en memoria VRAM | Batch size excede cuota | Kernel Kill (Signal 9) | ms | Fatal | Apoptosis + Reinicio con BS/2 |
| PRM-002 | Deadlock Termodinámico | Competencia bloqueante por DB WAL | Concurrencia multihilo > WAL límite | SQLite `database is locked` | seg | Crítica | Backoff Algorítmico + Serialización |
| PRM-003 | Sensor Drift | Limerencia / Degradación de Contexto LLM | Ventana de contexto saturada de ruido | Aserción BFT Fallida | min | Grave | Evicción L1 + Recarga desde Ledger |
| PRM-004 | Byzantine Divergence | Inconsistencia de estado en enjambre | Split-brain en consenso | Multi-hash discrepancy | seg | Crítica | Quorum Enforcement (N=3) |
| PRM-005 | Colapso Causal | Rotura de la cadena criptográfica (Provenance) | Mutación no firmada en disco | Falla de verificación Hash | instantáneo | Fatal | Halt inmediato + Reconstrucción |
| PRM-006 | Starvation Cognitiva | Bloqueo en pipeline de razonamiento pesado | Prompts de máxima entropía | Timeout de Inferencia | min | Moderada | Fallback a modelo T=0.0 (Flash) |
| PRM-007 | Exergy Drain (Fuga) | Consumo pasivo sin output estructural | Bucle infinito conversacional | Token ratio < umbral | seg | Grave | Inyección Interrupt (R9) |
| PRM-008 | Desincronización PTY | Desfase en túnel Tmux/SSH | TUI render latente / Escape sequence | Parser OOB (Out of bounds) | ms | Moderada | Flush buffer + Send SIGINT |
| PRM-009 | Fricción PEP-668 | Entorno externo gestionado bloquea PIP | Intentar instalación global mutante | Exit Code 1 (Externally Managed) | instantáneo | Crítica | Inyección meta_path (Bypass local) |
| PRM-010 | Asfixia de Event Loop | Llamada bloqueante en hilo asíncrono | Uso de `time.sleep` en async | Warning: Event loop blocked | ms | Grave | TID251 Auto-fix + Async refactor |
| PRM-011 | Cascading OOM | Falla de memoria propagada en Swarm | Subagentes clonan grandes datasets | Swap thrashing | min | Fatal | Límite de Mitosis Estricto |
| PRM-012 | Envenenamiento de RAM | Fugas en instancias de embeddings HNSW | Destrucción/creación iterativa sin GC | RAM monótonamente creciente | horas | Crítica | Reinicio programado (Ebbinghaus) |
| PRM-013 | Divergencia Topológica | Git desincronizado con base de datos | Commit externo no registrado en SQLite | SQLite / Git Hash mismatch | instantáneo | Fatal | Resincronización forzada (Repo Health) |
| PRM-014 | Alucinación Paramétrica | Generación estocástica sin soporte factual | Referencia a endpoint inexistente | Test Fail / 404 HTTP | seg | Grave | Forzar grounding (R2 Justificación) |
| PRM-015 | Saturación de File Descriptors | Fugas en sockets HTTP u open files | Agentes múltiples operando I/O bruto | `Too many open files` | min | Crítica | Pool Capping estricto |
| PRM-016 | Oscilación de Feedback | Corrección mutua entre 2 agentes eternamente | Prompt conflictivo sin moderador | Loop infinito de redacción | min | Fatal | TimerCondition (Early termination) |
| PRM-017 | Degradación de Base 60 | Pérdida de reloj causal en Consensus | Fallo en latidos (Heartbeat) P2P | Ausencia de nodo en registro | seg | Grave | Aislamiento + Re-elección de Líder |
| PRM-018 | Corrupción de Estado WAL | Caída dura de energía en operación DB | Corte eléctrico mid-transaction | Error SQLite `malformed` | ms | Fatal | Restauración de Snapshot Ledger |
| PRM-019 | Fuga de Entropía OSINT | Volcado inadvertido de claves/EXIF en commit | Falla del pre-commit hook de secret scan | Alerta de escaneo pasivo | instantáneo | Fatal | Rewrite history + Rotación |
| PRM-020 | Limerencia Narrativa | Agente emite excesiva prosa Green Theater | Inyección de "Aquí tienes" | Radio Señal/Ruido < 80% | seg | Moderada | Poda vía Thermodynamic Compressor |
