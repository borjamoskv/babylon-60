---
title: "Codebases legacy, arquitecturas no convencionales o documentación escasa"
description: "Un agente autónomo con control nativo sobre macOS puede navegar codebases legacy, arquitecturas no convencionales o proyectos con documentación escasa."
---

# Codebases legacy, arquitecturas no convencionales o documentación escasa: cómo un agente con control total del sistema operativo cambia las reglas

**Meta description:** Un agente autónomo con control nativo sobre macOS puede navegar codebases legacy, arquitecturas no convencionales o proyectos con documentación escasa. Patrones reales con el stack mac_maestro + CORTEX.

**Keywords:** legacy codebase AI agent, macOS automation AI, undocumented code analysis, agent system control, mac_maestro, CORTEX persist, autonomous code archaeology

---

## El escenario real: heredas un proyecto sin README

Día 1 en un proyecto nuevo. Te dan acceso a un repositorio con:

- 47 archivos Python sin docstrings
- Un `requirements.txt` con 23 dependencias sin versiones fijadas
- Cero tests
- Un README de dos líneas: "Run `python main.py`"
- El último commit es de hace 14 meses

Esto no es un caso extremo. Es el estado normal del 80% del software corporativo.

---

## Por qué los agentes actuales no sirven aquí

La mayoría de los agentes de código asumen tres cosas:

1. **Documentación legible** — README, docstrings, ADRs, changelogs
2. **Arquitectura convencional** — MVC, microservicios, monolito estándar  
3. **Entorno controlado** — CI/CD, tests, linter configurado

Cuando falta todo eso, el agente estándar hace lo mismo que un junior: lee el código, intenta inferir la estructura, y se pierde en las dependencias circulares.

El problema no es cognitivo. Es **perceptual**. El agente no tiene ojos. No puede:

- Abrir la aplicación y ver qué hace realmente
- Navegar la UI para descubrir flujos no documentados
- Inspeccionar procesos en ejecución para mapear dependencias runtime
- Leer logs del sistema operativo para entender fallos silenciosos

---

## La capa que falta: control nativo del sistema operativo

CORTEX implementa una capa de control macOS llamada `mac_maestro`. No es un wrapper de AppleScript. Es una cadena de ejecución con tres componentes:

### 1. MaestroExecutor — Ejecución con ledger

```python
class MaestroExecutor:
    """Ejecuta MacIntents via MacMaestro-Ω SDK 
    y registra cada acción en el ledger soberano."""
    
    def execute_intent(self, intent: MacIntent, 
                       oracle: VerificationOracle | None = None,
                       apply_safety_gate: bool = True) -> list[str]:
```

Cada acción del agente sobre el sistema operativo se convierte en un `LedgerEvent` con:
- **Timestamp** y latencia en ms
- **Correlación** con el intent original (por qué el agente hizo esto)
- **Verificación** opcional via `VerificationOracle`
- **Hash-chain** inmutable para auditoría posterior

### 2. MacIntent — Intenciones declarativas

El agente no ejecuta "click en coordenada (423, 891)". Declara intenciones:

```python
@dataclass
class MacIntent:
    goal: str           # "Descubrir la estructura de la app legacy"
    actions: list[MacAction]
    correlation_id: str # Traza de vuelta al objetivo
    trace_id: str       # Para observabilidad distribuida
```

Cada `MacAction` define:
- `action`: click, type, inspect, scroll
- `app`: bundle ID de la aplicación objetivo
- `role` / `title` / `identifier`: query de elemento UI (no coordenadas)
- `unsafe_override`: flag explícito para acciones destructivas

### 3. VerificationOracle — Validación post-acción

Después de cada acción, el oracle verifica que el estado del sistema es el esperado. Si la verificación falla, la secuencia se rompe:

```python
if not ok or verification_ok is False:
    logger.warning("Intent sequence broken at action: %s", action.action)
    break
```

---

## Protocolo de arqueología para codebases legacy

Con control total del OS, un agente puede ejecutar un protocolo de descubrimiento que no depende de documentación:

### Fase 1: Excavación estática (sin ejecutar nada)

| Acción | Método | Output |
|---|---|---|
| Escanear estructura de directorios | `list_dir` recursivo | Mapa de módulos |
| Extraer imports | AST parsing (como hace Seal 8) | Grafo de dependencias |
| Detectar dead code | Ruff + análisis de imports no usados | Lista de módulos fantasma |
| Identificar patrones | Regex sobre `class`, `def`, decoradores | Taxonomía arquitectónica |
| Verificar dependencias | Dependency Ghost Check (Seal 8) | Dependencias declaradas vs usadas |

### Fase 2: Excavación dinámica (ejecutar y observar)

Aquí es donde el control del OS marca la diferencia:

| Acción | Sin control OS | Con mac_maestro |
|---|---|---|
| Ejecutar la app | `python main.py` y leer stdout | Lanzar la app, capturar la UI, inspeccionar el árbol de accesibilidad |
| Descubrir endpoints | Leer código del router | Ejecutar la app + hacer requests + observar la respuesta en el navegador |
| Mapear flujos de usuario | Inferir desde handlers | Navegar la UI programáticamente, registrar cada pantalla |
| Diagnosticar errores | Leer logs en terminal | Monitorizar `Console.app`, correlacionar con procesos del sistema |
| Medir rendimiento | `time python main.py` | `CascadeTelemetry` + métricas de CPU/RAM por proceso via `sysctl` nativo |

### Fase 3: Documentación generativa

Con la información de las fases 1 y 2, el agente genera:

1. **Mapa de arquitectura** basado en imports reales y comportamiento observado
2. **Flujos de usuario** documentados desde la navegación UI
3. **Inventario de dependencias** con estado (activa/fantasma/vulnerable)
4. **Tests de humo** basados en los flujos descubiertos
5. **README técnico** que describe el sistema como es, no como alguien imaginó que sería

Todo registrado en el ledger para trazabilidad.

---

## Arquitecturas no convencionales: cuando el patrón no existe en Stack Overflow

Algunos proyectos no siguen MVC, no son microservicios, no son monolitos. Son:

- **Pipelines de datos** con DAGs implícitos
- **State machines** distribuidas entre archivos sin diagrama
- **Event sourcing** casero con SQLite y archivos JSON
- **Sistemas de plugins** con carga dinámica y convenciones no documentadas

Un agente con reading estática puede confundirlos con código desestructurado. Un agente con control del OS puede:

1. **Ejecutar el sistema** y observar el flujo real de datos
2. **Instrumentar** puntos clave con logging temporal
3. **Visualizar** el comportamiento en tiempo real
4. **Correlacionar** eventos del OS (procesos, red, ficheros) con la lógica de negocio

### Ejemplo real: el módulo `mac_maestro` de CORTEX

El propio CORTEX tiene un módulo que no sigue patrones web convencionales:

```
cortex/mac_maestro/
├── __init__.py       # 327 bytes — Import gate
├── events.py         # Transformación de acciones a LedgerEvents
├── executor.py       # 136 LOC — Orquestación con safety gates
├── intent.py         # Modelo declarativo de intenciones
├── oracle.py         # Verificación post-ejecución
```

5 archivos. 136 LOC en el ejecutor. Sin framework web, sin API REST, sin ORM. Es una cadena directa: `Intent → Action → SDK Call → Oracle Verify → Ledger Append`. Un agente sin control del OS no podría descubrir que esto controla ventanas, procesos y elementos UI de macOS. Necesita **ejecutar** el intent y **ver** el resultado.

---

## Documentación escasa: el problema no es que falte, es que miente

Hay algo peor que no tener documentación: tener documentación desactualizada. Un README que describe una arquitectura que dejó de existir hace 6 meses es más dañino que un repositorio vacío, porque establece un modelo mental incorrecto.

### El protocolo de verificación

Con CORTEX, cada pieza de documentación puede ser verificada contra el código:

1. **ContractionGuard** detecta si un nuevo hecho contradice hechos anteriores
2. **Seal 8 (Dependency Ghost Check)** compara imports declarados vs. imports reales
3. **Seal 9 (Compliance & Aesthetic)** busca placeholders y stubs no implementados
4. **SovereignLedger** registra cuándo se documentó algo vs. cuándo se modificó el código

Si la documentación dice "usamos Redis para caché" pero `cortex/memory/distributed_cache.py` usa SQLite, la contradicción es detectable y registrable.

---

## Implicaciones para equipos

### Para CTOs heredando legacy

No necesitas reescribir el sistema para entenderlo. Un agente con control total del OS puede hacer en horas lo que un equipo de arqueología de código tarda semanas:

- Mapa de dependencias reales (no las del `requirements.txt`)
- Flujos de usuario observados (no los del Confluence de 2022)
- Inventario de riesgos técnicos basado en ejecución real

### Para el developer solitario

Si mantienes un proyecto legacy tú solo, el agente con control del OS es tu segundo par de ojos. No solo lee código: **ejecuta la aplicación, navega la UI, y correlaciona lo que ve con lo que el código dice que debería pasar**.

### Para auditorías de seguridad

Un auditor puede usar el protocolo de excavación para descubrir:
- Endpoints no documentados
- Procesos fantasma que el equipo olvidó
- Dependencias transitivas con vulnerabilidades conocidas (Seal 3, Bandit)
- Datos sensibles en logs del sistema (PII Sanitizer)

---

## Lo que no puede hacer (aún)

Transparencia sobre limitaciones reales:

1. **No puede modificar código en producción** sin aprobación humana — `apply_safety_gate=True` por defecto
2. **No funciona en Linux/Windows** — `mac_maestro` usa APIs de Quartz y Accessibility de macOS
3. **El SDK requiere permisos de accesibilidad** — El usuario debe autorizar explícitamente
4. **La excavación dinámica consume tiempo** — Cada acción UI tiene latencia real (50-200ms por paso)
5. **No reemplaza la comprensión humana** — Genera artefactos; el juicio final es del ingeniero

---

## Resumen ejecutivo

| Capacidad | Agente estándar | Agente con control OS |
|---|---|---|
| Leer código | ✅ | ✅ |
| Ejecutar la app | ✅ (terminal) | ✅ (terminal + UI completa) |
| Navegar interfaces | ❌ | ✅ (programático, con audit trail) |
| Diagnosticar procesos | ❌ | ✅ (sysctl nativo, ctypes) |
| Verificar post-ejecución | ❌ | ✅ (VerificationOracle) |
| Registrar en ledger inmutable | ❌ | ✅ (hash-chain SHA-256) |
| Trabajar sin documentación | Limitado | Funcional (excavación dinámica) |

**El control del sistema operativo no es un lujo. Para codebases legacy sin documentación, es la diferencia entre adivinar y observar.**

---

*Las capacidades descritas en este artículo referencian implementaciones en el repositorio cortex-persist (v0.3.0b2). mac_maestro: 5 archivos, 136 LOC en executor, protocolo intent-action-verify-ledger.*
