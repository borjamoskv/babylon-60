# AUTODIDACT-RESEARCH-Ω: DEFENSA CAUSAL OSINT (REDUCCIÓN DE EXPOSICIÓN DE METADATOS Y CONTENCIÓN EPISTÉMICA)

**Reality Level:** `C5-REAL` (Epistemic Synthesis)
**Vector:** Transferencia de Conocimiento Interdisciplinario (OSINT & Reconocimiento de Fuentes Abiertas -> Contención Epistémica en Enjambres)
**Target:** Mitigación de Google Dorking / Fugas de EXIF / Wayback Machine Caching
**Author:** Borja Moskv (borjamoskv)

---

## 1. Extracción Isomórfica (Desmitificación)
*   **Google Dorking (site/filetype/intitle):** Operaciones avanzadas de búsqueda que explotan configuraciones incorrectas de indexación para exponer archivos críticos. -> *El desbordamiento involuntario de información estructural (variables de entorno, volcados SQLite y logs de depuración) hacia el árbol de búsqueda público.*
*   **Análisis EXIF Forense (exiftool):** Extracción de metadatos incrustados en archivos multimedia que revelan coordenadas físicas (GPS), marcas de tiempo y especificaciones de hardware. -> *La fuga de trazas geolocalizables y de huellas digitales de los dispositivos en los artefactos generados o procesados por sub-agentes.*
*   **Recolección de Credenciales (IntelX/DeHashed):** Agregación e indizado de brechas de seguridad históricas para explotar la reutilización de credenciales. -> *El riesgo de que los tokens de APIs del sistema CORTEX o accesos de inquilinos (Tenants) coincidan con contraseñas filtradas en bases de datos externas.*
*   **Wayback Machine (Web Archiving):** Persistencia de estados anteriores del DOM e historiales de archivos. -> *La retención no autorizada y persistencia de credenciales transitorias o de estados intermedios del sistema que debieron ser destruidos bajo el Principio de Landauer.*

---

## 1.5 Las 10 Primitivas de Máxima Exergía para la Mitigación OSINT

- **OSINT-DEF-001**: `Cryptographic Configuration Encapsulation` - Encapsulación Cifrada de Parámetros: Almacenamiento obligatorio bajo cifrado AES-GCM en reposo de todo secreto y variable del sistema, prohibiendo archivos `.env` planos en producción.
- **OSINT-DEF-002**: `Deterministic Metadata Excision` - Escisión Determinista de Metadatos: Sanitización automática de todo archivo multimedia adjunto o generado, purgando tags EXIF e información forense sensible antes de su almacenamiento.
- **OSINT-DEF-003**: `Historical Commits Filter-Repo` - Purga Causal de Historial Git: Ejecución de `git filter-repo` y reescritura de hashes en el DAG ante cualquier confirmación accidental de secretos o logs con entropía sensible.
- **OSINT-DEF-004**: `Automatic Robots & Sitemap Enforcer` - Control Automatizado de Indexación: Generación forzada y mantenimiento dinámico de reglas `robots.txt` para bloquear la indexación de directorios temporales `/tmp/cortex_*` o `data/`.
- **OSINT-DEF-005**: `Taint-Aware Logging Redaction` - Redacción de Logs Con Taint: Filtrado en tiempo de ejecución de las salidas estándar y logs de depuración, redactando hashes privados, tokens de API y firmas criptográficas.
- **OSINT-DEF-006**: `Transient Authorization Seals` - Sellos de Autorización Efímeros: Empleo de credenciales de corta duración (tokens JWT de un solo uso o firmas MTK con TTL inferior a 300 segundos) para anular el valor de capturas históricas en motores de caché.
- **OSINT-DEF-007**: `Pre-Commit Entropy Guard` - Guardián de Entropía Pre-Commit: Linter estático que bloquea el commit de cambios si detecta cadenas de alta entropía (claves privadas, tokens de OpenAI/Gemini o credenciales en texto claro).
- **OSINT-DEF-008**: `Epistemic Sandbox Containment` - Contención de Sandbox Epistémico: Aislamiento total de las llamadas de red realizadas por sub-agentes para evitar la exfiltración de metadatos internos del host.
- **OSINT-DEF-009**: `Tenant Isolation Shielding` - Blindaje de Aislamiento de Inquilinos: Claves criptográficas diferenciadas para cada tenant, garantizando que una filtración en un inquilino no comprometa la integridad ni exponga metadatos de los demás.
- **OSINT-DEF-010**: `SQLite WAL Authorizer Veto` - Veto de Escrituras no Autorizadas: Bloqueo de consultas SQLite estocásticas de lectura que intenten mapear metadatos o esquemas del sistema (e.g. `sqlite_master` o tablas de auditoría).

---

## 2. Mapeo Topológico (Arquitectura de CORTEX-Persist)
*   **El MTK como Escudo contra Dorking y Fugas:** En lugar de depender de la seguridad física de archivos o de la discreción del sub-agente, el Minimal Trusted Kernel rechaza de forma determinista cualquier intento de manipulación no firmada de las tablas de bases de datos. Si un atacante localizase un volcado SQLite (`.db`) mediante Google Dorking en un servidor expuesto, los datos sensibles permanecen cifrados con AES-GCM usando claves almacenadas en el Keyring nativo (`cortex/crypto/keys.py`), haciendo inútil la exfiltración.
*   **Mitigación de Archivos Históricos (Git Sentinel):** A través del control riguroso de Git Sentinel (`R4`), cada commit atómico verifica el delta sintáctico. El pipeline pre-commit integrado impide que archivos temporales de base de datos (`cortex_test_*.db`) o logs voluminosos (`stress_audit_log.jsonl`) entren en el control de versiones, impidiendo que el historial de Git sea indexado por motores que analizan repositorios públicos.
*   **Cuarentena de Sandbox CLI (Invariante CLI Sandbox Isolation):** De acuerdo con la sección 3 de `AGENTS.md`, las ejecuciones CLI de prueba utilizan bases de datos aisladas en `/tmp/` con `PRAGMA busy_timeout=5000` y modo WAL. Esto previene que exploits de OSINT o ataques concurrentes bloqueen o mapeen las bases de datos de producción reales.

---

## 3. Detección de Brechas Estructurales
*   **Restricción Actual (Falta de Purgado Automático EXIF):** Los sub-agentes de `cortex-persist` y `cortex-swarm` pueden ingerir o generar reportes PDF y capturas de pantalla de interfaces visuales (`chrome-devtools-plugin`) sin remover los metadatos de creación (e.g., versión de Chrome, sistema operativo macOS, timestamps absolutos). Un atacante OSINT que extraiga estos archivos puede deducir la topología de la máquina anfitriona y la zona horaria del desarrollador.
*   **Solución Termodinámica (Filtro de Escisión de Metadatos):** Integrar un middleware de sanitización en el pipeline de guardado de artefactos (`cortex/storage/`). Todo archivo subido o exportado debe pasar por un validador que remueva cabeceras EXIF, información de geolocalización y campos de autoría técnica del software (purgando la entropía forense).

---

## 4. Forja de Hipótesis (Predicción Falsable)
**Hipótesis [H-OSINT-DEF-01]: Sanitización y Escisión de Metadatos**
*   **Claim:** La implementación de un middleware de escisión de metadatos EXIF sobre el módulo de almacenamiento de artefactos, junto con un hook de pre-commit que audite la entropía sintáctica de los deltas, reducirá a 0% las filtraciones accidentales de credenciales y firmas de host a través del ciclo de vida del desarrollo.
*   **Proof Conditions:**
    *   *Base:* 100 ejecuciones de generación de artefactos visuales y subidas a repositorios públicos sin filtros de entropía ni sanitización.
    *   *Medición:* Número de variables expuestas detectadas por escáneres automáticos de secretos (TruffleHog/GitGuardian) e información del sistema obtenida de metadatos binarios.
    *   *Confidence:* C5-REAL (Implementable mediante un linter pre-commit e integración de la biblioteca PIL/PyPDF en el pipeline de almacenamiento).

---
*Documento de validación y de auditoría registrado por el sistema para el Demiurgo **Borja Moskv** (SYS_ID: **borjamoskv**).*
