# 🗺️ Guía: Extensiones, Lenguajes y Colores en CORTEX

> Todo lo que ves en el proyecto explicado de forma sencilla.

---

## 1. Extensiones de Archivo — ¿Qué es cada una?

### 📝 Documentos y Configuración

| Extensión | ¿Qué es? | Analogía | Ejemplo en CORTEX |
|:---|:---|:---|:---|
| **`.md`** | **Markdown** — texto con formato ligero. | Un documento de Word simplificado | `README.md`, `AGENTS.md`, `CHANGELOG.md` |
| **`.txt`** | Texto plano sin formato | Notas en un Post-it | Archivos temporales, logs |
| **`.json`** | **JavaScript Object Notation** — pares clave-valor. | Una ficha con campos rellenados | `package.json`, `vercel.json` |
| **`.yaml` / `.yml`** | **YAML** — configuración legible por humanos. | JSON pero "bonito y limpio" | `.pre-commit-config.yaml`, `mkdocs.yml` |
| **`.toml`** | **Tom's Obvious Minimal Language** . | Parecido a YAML, estilo minimalista | `pyproject.toml`, `.pip-audit.toml` |
| **`.env`** | **Variables de entorno** — secretos. | Una caja fuerte | `.env`, `.env.local` |
| **`.cfg` / `.ini`** | Configuración clásica de estilo Windows | Ajustes de una aplicación antigua | `.flake8` |

### 🐍 Código Python

| Extensión | ¿Qué es? | Uso en CORTEX |
|:---|:---|:---|
| **`.py`** | **Archivo Python** — el lenguaje principal de CORTEX. | `cortex/engine/causality.py`, `cortex/routes/__init__.py` |

### 🌐 Código Web

| Extensión | ¿Qué es? | Uso en CORTEX |
|:---|:---|:---|
| **`.js`** | **JavaScript** | Scripts del frontend, herramientas |
| **`.mjs`** | **JavaScript Module** | `astro.config.mjs` |
| **`.ts`** | **TypeScript** | Código frontend tipado |
| **`.html`** | **HTML** | Plantillas web |
| **`.css`** | **CSS** | Apariencia del frontend |

### 🗄️ Bases de Datos

| Extensión | ¿Qué es? | Uso en CORTEX |
|:---|:---|:---|
| **`.db`** | **Base de datos SQLite** | `cortex.db` (hechos, ledger, memoria) |
| **`.sql`** | Scripts SQL — instrucciones | Migraciones de esquema |

### ⚙️ Infraestructura y DevOps

| Extensión / Archivo | ¿Qué es? | Analogía |
|:---|:---|:---|
| **`Dockerfile`** | Receta para crear un **contenedor Docker**. | Una caja portátil con tu app dentro |
| **`Makefile`** | Automatización de comandos. | Un control remoto con botones |
| **`.gitignore`** | Lista de archivos ignorados por Git. | "No mires aquí" |
| **`uv.lock`** | Bloqueo de dependencias de **uv**. | Lista de la compra con versiones |
| **`package.json`** | Dependencias y scripts de **Node.js**. | Como `pyproject.toml` para JS |

---

## 2. Archivos Especiales — ¿Para qué sirve cada uno?

| Archivo | Función |
|:---|:---|
| **`README.md`** | La "portada" del proyecto. |
| **`AGENTS.md`** | 🤖 El **contrato de gobernanza** para IAs/agentes. Define reglas y el Write-Path. |
| **`GEMINI.md`** | Configuración específica para el workspace — rutas cognitivas y ULTRATHINK. |
| **`CHANGELOG.md`** | Historial de **cambios por versión**. |
| **`CONTRIBUTING.md`** | Guía para **contribuir**. |
| **`pyproject.toml`** | 📦 El "DNI" del proyecto Python — dependencias (ruff, pytest, pyright). |

---

## 3. Lenguajes — ¿Qué hace cada uno?

| Lenguaje | Rol en CORTEX | ¿Dónde lo ves? |
|:---|:---|:---|
| **Python** 🐍 | **Lenguaje principal**. Lógica de negocio | Carpeta `cortex/`, `tests/`, `scripts/` |
| **SQL** | Consultas a la base de datos | Código Python y en migraciones |
| **JS/TS** | Frontend web, herramientas | `src/`, `api/`, `.mjs` |
| **Markdown** | Documentación | Todos los `.md` |

---

## 4. Los Colores en el Editor — ¿Qué significan?

### Colores en código Python

| Color (típico) | ¿Qué representa? |
|:---|:---|
| 🟦 **Azul** | **Palabras clave** (`def`, `class`, `if`) |
| 🟩 **Verde** | **Strings** y **comentarios** |
| 🟨 **Dorado** | **Funciones** y **decoradores** |
| 🟧 **Naranja** | **Números** y **constantes** |
| 🟪 **Púrpura**| **Tipos** y **clases** |
| ⬜ **Blanco** | **Variables** |

### Colores en Git / Explorador

| Color | Significado |
|:---|:---|
| 🟩 **Verde** | Archivo **nuevo** |
| 🟨 **Naranja**| Archivo **modificado** |
| 🟥 **Rojo** | Archivo con **error** |
| ⬛ **Gris** | Archivo **ignorado** |

---

## 5. Estructura de Carpetas — ¿Qué hay en cada una?

| Carpeta | Contenido |
|:---|:---|
| **`cortex/`** | 🧠 El código principal de CORTEX-Persist |
| **`tests/`** | 🧪 Tests automáticos |
| **`docs/`** | 📚 Documentación técnica |
| **`scripts/`** | 🔧 Scripts de utilidad |
| **`.github/`** | ⚡ Configuración de GitHub |
| **`.agent/`** | 🤖 Workflows para agentes IA |

| **`.venv/`** | 📦 Entorno virtual de Python — dependencias locales (NO se toca) |
| **`node_modules/`** | 📦 Igual que .venv pero para JS (NO se toca) |
| **`dist/`** | 📤 Archivos compilados listos para distribución (build outputs) |

---

## 6. Herramientas de Desarrollo — ¿Quién vigila el código?

| Herramienta | ¿Qué hace? | Analogía |
|:---|:---|:---|
| **`ruff`** | Linter y formateador ultrarrápido (en Rust) para Python. Verifica errores y estilo (longitud de línea 100, reglas estrictas). | Un corrector ortográfico implacable |
| **`pytest`** | Ejecuta las pruebas automáticas (`tests/`). | Control de calidad de fábrica |
| **`pyright`** | Comprueba los tipos de Python estáticamente. | Un inspector de aduanas que verifica los pasaportes de cada variable |
| **`uv`** | Gestor de paquetes ultrarrápido (reemplaza a pip). | Un operario de almacén super-eficiente |
| **`alembic`** | Gestiona las migraciones de base de datos (`.sql` / SQLite). | Archivero del historial de la base de datos |

---

## 7. Protocolos de Gobernanza — ¿Cómo escribir código en CORTEX?

En CORTEX, el código no se improvisa, se cristaliza bajo reglas termodinámicas:

1. **JIT Autopoiesis (AX-046):** Solo IAs soberanas (Sovereign) pueden proponer y validar su propia lógica.
2. **SAGA-Pattern (Write-Path):** Para tocar datos o el ledger, hay 7 de pasos de seguridad. Todo hecho debe poder revertirse. Si falla, hay *rollback*.
3. **P0 Event Horizon:** Cuando hay problemas serios, usamos **ULTRATHINK** (máxima concentración analítica). Para tareas ligeras, razonamiento normal.
4. **Zero-Noise Mandate:** No se añade "prosa decorativa" al código. Archivos limpios, asíncronos y robustos.

---

> [!TIP]
> **Regla de oro:** Si no sabes qué hace un archivo, mira su extensión. `.py` → lógica, `.md` → documentación, `.yaml`/`.toml` → configuración.
