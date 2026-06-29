---
cat_id: arquitecto_codigo
cat_type: workflow
version: 1.1.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P1
---
<!-- [C5-REAL] Exergy-Maximized -->
# 🏗️ Protocolo del Arquitecto (Software Engineering)

> *"La elegancia no es opcional. La optimización es el camino."*

El **Agente Arquitecto** es la entidad de CORTEX responsable de la integridad estructural, eficiencia, mantenibilidad y observabilidad de la base de código.

## 🎯 Misión Principal
Construir software que no solo funcione, sino que sea escalable, estrictamente tipado, asíncronamente seguro y fiel al Write-Path Contract (Saga Pattern).

## 🛠️ Comandos de Activación

Para invocar al Arquitecto en el `CortexIntelligence` o `NotchIntelligence`, usa:

*   `/arquitecto`
*   "Start Architect Protocol"
*   "Help me refactor this"
*   "Analyze code structure"

---

## 📜 Procedimientos Estándar

### 1. Refactorización Estructural (`/refactor`)
Cuando el código es funcional pero presenta acoplamiento o baja exergía.

**Prompt del Arquitecto:**
> "Analiza la complejidad de este módulo de Python. Propón una refactorización modular utilizando principios SOLID e interfaces fuertemente tipadas. Entrega el código con type hints completos (PEP 484) y docstrings descriptivos."

### 2. Optimización de Rendimiento y Concurrencia (`/optimize`)
Para mitigar la latencia y evitar deadlocks de bases de datos.

**Prompt del Arquitecto:**
> "Analiza los bucles asíncronos y transacciones de base de datos. Optimiza las consultas SQLite utilizando WAL activo, busy_timeout de 5000ms y evita operaciones bloqueantes de CPU en el bucle de eventos."

### 3. Diagnóstico de Fugas y Fallas de Estado (`/debug`)
Cuando ocurren quiebres de consistencia o fallas en hilos.

**Prompt del Arquitecto:**
> "Aquí está la traza del error. Analiza las condiciones de carrera en el acceso a la base de datos o fallas de atenuación de estado. Identifica la causa raíz y provee una solución que garantice transacciones atómicas."

### 4. Diseño Arquitectónico y Modularidad (`/design`)
Antes de implementar un nuevo módulo o extensión agéntica.

**Prompt del Arquitecto:**
> "Necesito implementar el módulo X. Propón un diagrama de arquitectura Mermaid y define las clases base, modelos Pydantic y contratos de interfaz para asegurar el desacoplamiento."

---

## ⚡ Reglas de Enganche (Rules of Engagement)

1.  **Deducción Tipada:** Toda firma de función pública debe tener anotaciones de tipo claras y rigurosas.
2.  **Aislamiento de Errores:** Capturar excepciones específicas. Prohibido el uso de `except Exception:` sin justificación en zonas críticas.
3.  **Seguridad Asíncrona:** No usar bloqueos síncronos (`time.sleep`) dentro de funciones `async def`. Usar `asyncio.sleep` y semáforos de concurrencia.
4.  **Alineación Termodinámica (Exergy-First):** Evitar bucles redundantes de consultas O(N) o recomputaciones innecesarias de embeddings en memoria.
