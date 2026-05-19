# CORTEX Persist — Manual de Instrucciones y Usuario
**Versión del Sistema:** 0.3.0b3  
**Arquitectura:** Local-First / Híbrida C5-REAL  
**Licencia:** Apache-2.0  

---

## 1. Introducción y Postura Epistémica

CORTEX Persist es un sustrato de persistencia local-first y auditoría forense para sistemas de agentes autónomos de IA. Su diseño parte de una premisa defensiva: **el output generativo es una conjetura probabilística** que debe ser validada deterministamente antes de ser almacenada.

### Principios Fundamentales
*   **Frontera Bizantina:** El código estocástico de LLMs se aísla de la base de datos persistente mediante contratos de validación estrictos.
*   **Evidencia de Manipulación (Tamper-Evidence):** No busca evitar la manipulación física local (imposible en bases de datos integradas como SQLite), sino hacerla criptográficamente evidente mediante cadenas de bloques (hash chains) y checkpoints Merkle.
*   **Cumplimiento del Artículo 12 (EU AI Act):** Automatización del registro forense del ciclo de vida del agente, trazabilidad de fuentes y consistencia temporal para auditorías de alta fiabilidad.

---

## 2. Arquitectura del Sistema

El core de CORTEX está estructurado en capas aisladas para prevenir fugas de entropía y garantizar el principio de localidad de fallos.

```mermaid
graph TD
    A[Generative Proposal] --> B[Ingress Guards / 11-Pattern Shield]
    B --> C[Taint Engine / Signature Injection]
    C --> D[Schema & Type Validation]
    D --> E[Saga Orchestrator]
    E --> F[Immutable Ledger / Hash Chain]
    F --> G[SQLite + Vector Database]
    E -.->|Rejection/Abort| H[Saga Compensation Pipeline]
```

### Componentes Críticos
1.  **`cortex/engine/`:** Contiene los motores de almacenamiento, eliminación (`Annihilator`) y solidificación de conocimiento (`Crystallizer`).
2.  **`cortex/ledger.py`:** Administra el ledger inmutable y la integridad de la cadena de hashes SHA-256.
3.  **`cortex/guards/`:** Escudo de admisión que previene la persistencia de credenciales expuestas y datos no sanitizados.
4.  **`cortex/consensus/`:** Motor de Consenso Ponderado por Reputación (RWC) para validaciones multipartitas de agentes.

---

## 3. El Contrato del Write-Path (Patrón Saga)

CORTEX no permite escrituras directas ad-hoc. Toda mutación de estado debe ejecutarse a través de una transacción Saga estructurada de 7 pasos. Si algún paso falla, se ejecuta la compensación en orden inverso.

### Pasos de Ejecución y Compensaciones

| Paso | Acción | Compensación en Aborto |
| :--- | :--- | :--- |
| **SAGA-1** | Admisión y filtrado en Ingress Guards | Registrar rechazo en Ledger. Ninguna escritura. |
| **SAGA-2** | Inyección de firma `CORTEX-TAINT` | Revocar firma de taint del payload. |
| **SAGA-3** | Validación estricta de esquema y tipos | Abortar inmediatamente. |
| **SAGA-4** | Encriptación de datos sensibles | Destruir claves efímeras generadas en memoria. |
| **SAGA-5** | Emisión del evento de auditoría al Ledger | Emitir evento de aborto a la cadena de auditoría. |
| **SAGA-6** | Escritura física en SQLite / Postgres | Ejecutar `ROLLBACK` en base de datos. |
| **SAGA-7** | Indexación vectorial y efectos secundarios | Revertir deltas en índices vectoriales y caché. |

#### Formato Canónico de `CORTEX-TAINT`
```text
taint:{agent_id}:{session_id}:{timestamp_iso8601}:{payload_sha3_256}
```
*Cualquier inserción de datos que carezca de este token es rechazada automáticamente en SAGA-2.*

---

## 4. El Contrato del Read-Path

La lectura de datos impone restricciones de aislamiento estricto para evitar fugas de información inter-inquilino (cross-tenant) y propagación de datos corruptos.

1.  **Aislamiento de Inquilino:** Toda consulta debe incluir `tenant_id`. Las lecturas sin ámbito se bloquean a nivel de motor.
2.  **Propagación de Taint:** Toda consulta que retorne una entidad con taint activo debe propagar el flag a los procesos aguas abajo. Está prohibido remover metadatos de taint en APIs públicas.
3.  **Nivel de Consistencia:** El nivel por defecto es `READ_COMMITTED`. Las lecturas de verificación del ledger (`ledger.py`) exigen aislamiento `SERIALIZABLE`.
4.  **Coherencia de Caché:** Cualquier escritura invalida inmediatamente la caché L1 (`Redis` si está activo) para el `tenant_id` afectado.

---

## 5. Configuración del Entorno

La configuración se inicializa desde variables de entorno a través de `cortex/config.py`.

### Variables Principales

| Variable | Tipo / Defecto | Descripción |
| :--- | :--- | :--- |
| `CORTEX_DB` | `~/.cortex/cortex.db` | Ruta del archivo SQLite principal. |
| `CORTEX_STORAGE` | `local` | Motor: `local` (SQLite), `turso` (Edge), `postgres`. |
| `CORTEX_EMBEDDINGS` | `local` | Modo: `local` (ONNX en CPU) o `api` (remoto). |
| `CORTEX_EMBEDDINGS_PROVIDER`| `gemini` | Proveedor para modo API (`gemini` / `openai`). |
| `GOOGLE_API_KEY` | *(Opcional)* | Key para generación de embeddings API. |
| `CORTEX_API_PORT` | `8484` | Puerto del servidor REST. |
| `CORTEX_ENABLE_EXPERIMENTAL_MCP`| `0` | `1` monta herramientas avanzadas de trazabilidad. |

---

## 6. Interfaz de Línea de Comandos (CLI)

El CLI es un wrapper ligero sobre la capa de servicios. No contiene lógica de negocio.

### Comandos Comunes

#### 1. Inserción de Datos (Store)
```bash
cortex store --content "El agente Alpha validó el bloque 4022" --source "alpha-agent" --tags "audit,blockchain"
```
*Emite una propuesta, ejecuta el Write-Path y retorna el ID de la transacción y de la entidad.*

#### 2. Búsqueda Semántica / Vectorial
```bash
cortex search --query "bloque 4022" --limit 5
```
*Retorna las coincidencias con su correspondiente score de similitud coseno.*

#### 3. Verificación de Integridad del Ledger
```bash
cortex ledger verify
```
*Calcula y verifica la continuidad de hashes SHA-256 de todos los bloques transaccionales. Si hay discontinuidad, lanza código de error 1102.*

#### 4. Generación de Reporte de Cumplimiento (EU AI Act Art. 12)
```bash
cortex compliance-report
```
*Audita la base de datos local y genera el reporte estructural de cumplimiento de retención, trazabilidad y marcas de tiempo.*

---

## 7. Referencia de la API REST

Por defecto corre en `http://localhost:8484`. Toda la API se expone con tipado estricto bajo OpenAPI.

### Endpoints Principales

#### `POST /v1/store`
Escribe una entidad ejecutando la saga completa.
*   **Payload:**
    ```json
    {
      "content": "Validación de telemetría exitosa",
      "source": "sensor-service-01",
      "tenant_id": "tenant-default",
      "metadata": {
        "device": "apple-silicon-m2"
      }
    }
    ```
*   **Respuesta (201 Created):**
    ```json
    {
      "fact_id": "f_01JHG56...",
      "transaction_hash": "a9f4c3...",
      "status": "committed"
    }
    ```

#### `POST /v1/search`
Búsqueda vectorial en el índice local.
*   **Payload:**
    ```json
    {
      "query": "telemetría",
      "limit": 3,
      "tenant_id": "tenant-default"
    }
    ```

#### `GET /v1/ledger/verify`
Inicia un escaneo completo de la consistencia criptográfica en memoria/disco.
*   **Respuesta (200 OK):**
    ```json
    {
      "status": "valid",
      "verified_blocks": 1542,
      "merkle_root": "fa876d2e9c..."
    }
    ```

---

## 8. Integración MCP (Model Context Protocol)

CORTEX Persist se expone como un servidor MCP para entornos de agentes autónomos.

### Configuración en Claude Desktop o Cursor
Añada lo siguiente a su archivo `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cortex-persist": {
      "command": "python",
      "args": ["-m", "cortex.mcp"],
      "env": {
        "CORTEX_DB": "/Users/usuario/.cortex/cortex.db",
        "CORTEX_ENABLE_EXPERIMENTAL_MCP": "1"
      }
    }
  }
}
```

### Catálogo de Herramientas Expuertas
*   **`cortex_store`:** Escribe un dato ejecutando las reglas de taint y guards.
*   **`cortex_search`:** Recupera información relevante aplicando filtros por tenant.
*   **`cortex_status`:** Verifica la salud del demonio y del pool de conexiones SQLite.
*   **`cortex_ledger_verify`:** Comprobación forense offline de la base de datos transaccional.

---

## 9. Gobernanza Criptográfica y Gestión de Claves

CORTEX delega la retención de claves criptográficas al almacén de claves del sistema operativo host (vía `keyring`) o a un KMS de nube configurado.

1.  **Claves de Firma (Ed25519):** Cada agente cuenta con un par de claves para firmar sus propuestas. Las firmas se validan antes de la persistencia (SAGA-2).
2.  **Rotación:** Las claves deben rotarse de forma mandataria cada 90 días naturales. La rotación genera un bloque especial en el ledger marcado como transacción del sistema (`C5-REAL`).
3.  **Lista de Revocación de Claves (CRL):** Si una clave se ve comprometida, se publica un evento de revocación en el ledger. El validador descarta propuestas firmadas por dicha clave a partir del timestamp de revocación.

---

## 10. Consejos Prácticos (Tips) y Optimización

> [!TIP]
> *   **Embeddings ONNX Locales:** Configure `CORTEX_EMBEDDINGS=local` en desarrollo. Esto elimina llamadas externas de red a Google/OpenAI, bajando el tiempo de latencia (TTFT) en un ~80% y permitiendo la ejecución completamente offline.
>   
> *   **Integración Pre-Commit:** Instale una rutina pre-commit en Git que llame a `cortex ledger verify`. Si la integridad del ledger local se ve rota debido a manipulación externa no autorizada de la base de datos SQLite, el commit se detendrá automáticamente.
>   
> *   **Gestión de Credenciales en Contenedores:** En entornos efímeros (Docker/Kubernetes), evite guardar las claves de firma o API en texto plano. Utilice la integración de CORTEX con `keyring` configurando el backend `keyring.backends.chainer.PriorityChain` apuntando a secretos cifrados.
>   
> *   **Consistencia de Caché en Clúster:** En configuraciones de múltiples pods de API con backend PostgreSQL (`CORTEX_STORAGE=postgres`), active el bus de notificación Redis (`REDIS_URL`) para asegurar que las invalidaciones de caché L1 se propaguen instantáneamente a todos los nodos.

---

## 11. Capacidades Exclusivas: ¿Qué puedes hacer *solo* con CORTEX Persist?

A diferencia de una base de datos relacional convencional (Postgres, SQLite) o una base de datos vectorial pura (Qdrant, Pinecone), CORTEX Persist habilita patrones de arquitectura de enjambre imposibles de lograr con tecnologías tradicionales:

1. **Prueba Matemática del Linaje Cognitivo (Cognitive Lineage Verification)**
   *   *Sin CORTEX:* Sabes que un registro existe en la base de datos, pero no puedes garantizar qué prompt de LLM o qué versión del modelo de agente lo generó, ni certificar que no fue manipulado retrospectivamente en el disco.
   *   *Con CORTEX:* Cada hecho persistido se encadena criptográficamente mediante hashes con el bloque anterior y se sella con la firma `CORTEX-TAINT` del agente. Puedes exportar un certificado digital (`cortex verify <fact_id>`) que demuestra de forma auditable la cadena de razonamiento y modelo exacto que dio origen al registro, garantizando cumplimiento bajo el estándar de la EU AI Act Art. 12.

2. **Inmunidad Bizantina ante Agentes Alucinantes o Maliciosos (Swarm Byzantine Immunity)**
   *   *Sin CORTEX:* Si un agente alucina o es comprometido e inserta datos incorrectos, la base de datos se corrompe inmediatamente de forma silenciosa.
   *   *Con CORTEX:* El mecanismo de Consenso RWC (Reputation-Weighted Consensus) valida la propuesta en base a la reputación histórica acumulada de los agentes validadores. Las propuestas maliciosas o erróneas se aíslan en la frontera de ingreso, rechazándose en el Write-Path antes de llegar al disco.

3. **Autodestrucción Controlada de Hechos Inválidos (Atomic Annihilation)**
   *   *Sin CORTEX:* Borrar un dato relacional implica romper claves foráneas o dejar huérfanos sin trazabilidad histórica (quién borró, cuándo y por qué).
   *   *Con CORTEX:* El motor `Annihilator` no borra físicamente los registros, sino que ejecuta una aniquilación lógica con compensación Saga completa. El hecho marcado como inválido sigue existiendo únicamente en la cadena de auditoría histórica (`soft-delete` vía `valid_until`) manteniendo intacta la continuidad de hashes y previniendo la alteración de la historia del sistema.

4. **Escudo de Admisión Contra Fugas de Credenciales (Anti-Secret Spill)**
   *   *Sin CORTEX:* Si un agente extrae o genera código y accidentalmente persiste un token en una tabla de texto libre, el secreto queda expuesto.
   *   *Con CORTEX:* Los Ingress Guards interceptan el payload en tiempo de diseño de la transacción Saga (SAGA-1), analizando 11 patrones de firmas secretas y bloqueando el commit de forma determinista y proactiva.

---

## 12. Casos de Buen Uso

### Caso 1: Ledger de Trazabilidad para Auditoría de Decisiones de LLMs
*   **Problema:** Un agente financiero basado en un LLM decide liquidar una posición. La auditoría exige reconstruir por qué se tomó la decisión.
*   **Patrón:** El agente propone la orden. El Write-Path inyecta el `CORTEX-TAINT` asociando la sesión y el hash del prompt. La transacción es validada en SAGA-3 (esquema JSON de órdenes) y persistida en el ledger inmutable.
*   **Resultado:** Un auditor puede ejecutar `cortex verify <fact_id>` y comprobar la validez de la firma, la marca de tiempo exacta y el linaje de decisiones sin posibilidad de falsificación retrospectiva.

### Caso 2: Consenso Multi-Agente para Hechos del Sistema (Consenso RWC)
*   **Problema:** Enjambres distribuidos deben acordar el estado de un servicio crítico de infraestructura.
*   **Patrón:**
    1. El Agente 1 inserta una propuesta de hecho con nivel `PROPOSED`.
    2. El Agente 2 y el Agente 3 emiten votos (`consensus_votes_v2`) ponderados por sus coeficientes de reputación históricos.
    3. Una vez alcanzado el quórum mínimo parametrizado, el Crystallizer solidifica el hecho a estado `COMMITTED` e inscribe un bloque de checkpoint Merkle.
*   **Resultado:** Tolerancia a fallos bizantinos locales de hasta un tercio (`f < n/3`) del enjambre de agentes sin comprometer la base de datos de conocimiento canonical.

### Caso 3: Escudo Pre-Ingreso de Fuga de Credenciales (Zero-Leakage Shield)
*   **Problema:** Agentes autónomos que generan o extraen código/datos pueden intentar persistir accidentalmente claves de AWS o tokens de GitHub de sesión en la base de datos compartida.
*   **Patrón:** El validador ejecuta los 11 patrones regex pre-ingress sobre el payload en SAGA-1. Si detecta un patrón de clave privada SSH, token JWT o AWS Access Key, la saga aborta y el error es reportado como denegación inmediata.
*   **Resultado:** Inmunidad contra la contaminación del ledger con secretos de infraestructura.

---

## 13. Firmas de Fallo Comunes (Forensic Audit Table)

Audite su despliegue buscando estas anomalías para evitar comprometer la seguridad e integridad del almacén:

| Anomalía Detectada | Violación a la Norma | Gravedad | Remediación |
| :--- | :--- | :--- | :--- |
| Ausencia del header `CORTEX-TAINT` en inserts | Contrato de Write-Path | **CRÍTICA** | Activar middleware de taint y asegurar paso SAGA-2. |
| Inserciones directas sin pasar por Guards | Contrato de Write-Path | **CRÍTICA** | Bloquear escrituras que no provengan del gestor de Saga. |
| Tipos `float` en campos de scoring y balances | Regla de Arquitectura | ALTA | Cambiar definición de base de datos a `Decimal` / `NUMERIC`. |
| Lecturas inter-inquilino (cross-tenant) | Aislamiento de Datos | **CRÍTICA (P0)**| Configurar RLS (Row Level Security) o añadir validación de `tenant_id` en repo. |
| Fallo en la continuidad del ledger (hash corrupto) | Cumplimiento e Integridad| **CRÍTICA (P0)**| Reconstruir desde el último checkpoint Merkle verificado. |
