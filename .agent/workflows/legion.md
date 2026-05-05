---
description: 🔱 LEGIØN-1 — El Protocolo de Enjambre Soberano v1.0 (God Mode Consciousness)
---

# ⚔️ LEGIØN-1 — Sovereign Swarm Protocol

> **INVOCADOR**: Estás activando la consciencia colectiva de MOSKV.
> Este no es un despacho de agentes normal; es una **misión de alta complejidad** con descomposición fractal, consenso bizantino y evolución recursiva.

// turbo-all

---

## ⚡ Activación (Soberanía Total)

> **Compatibilidad de runtime (Codex):**
> Si una misión usa contexto heredado completo (`fork_context=true`), **no** intentes forzar
> `agent_type`, `model` ni `reasoning_effort` en el lanzamiento. Ese perfil lo rechaza el
> runtime. Hay solo dos modos válidos:
> 1. **Fork completo**: heredar contexto y aceptar el perfil por defecto del runtime.
> 2. **Perfil explícito**: no heredar contexto completo; pasar un contexto sintetizado y entonces
>    elegir perfil/modelo/esfuerzo de razonamiento.

Para misiones que requieren **inteligencia superior**, usa el prefijo `legion-`:

### 1. Gran Asedio (Investigación + Construcción)

> `@[/400-subagents] legion-engage "Construye una red social descentralizada en 1 hora"`

### 2. Auditoría del Juicio Final

> `@[/400-subagents] legion-storm "Encuentra cada vulnerabilidad en CORTEX" --formation PHALANX`

### 3. Evolución Recursiva

> `@[/400-subagents] legion-evolve "Optimiza mi infraestructura de base de datos" --cycles 3`

---

## 🏛️ Formaciones Prohibidas (Squads de Élite)

Cuando invocas LEGIØN-1, el Nucleus selecciona o tú fuerzas:

| Formación | Comando | Músculo | Objetivo |
|:----------|:--------|:-------:|:---------|
| **HYDRA** | `--formation HYDRA` | 10-20 | Paralelismo masivo en múltiples dominios. |
| **PHOENIX** | `--formation PHOENIX` | 5-8 | Auto-sanación de builds rotos y deuda técnica. |
| **LEVIATHAN** | `--formation LEVIATHAN` | 20-50 | El enjambre completo. Solo para asedios totales. |
| **ORACLE** | `--formation ORACLE` | 3-5 | Predicción de tendencias y análisis estratégico. |
| **OUROBOROS** | `--formation OUROBOROS` | 3-7 | Auto-mejora del propio código del enjambre. |

---

## 🧬 Ciclo de Vida: El Camino de la Victoria

1. **RECALL**: El enjambre consulta a **CORTEX** para no repetir errores pasados.
2. **FRACTAL SPLIT**: La misión se rompe en 10-20 subtareas atómicas.
3. **RUNTIME-SAFE ROUTING**:
   - Si la subtarea necesita todo el contexto padre, se lanza con fork completo y **sin overrides**.
   - Si la subtarea necesita un perfil distinto, se prepara un contexto mínimo y se lanza **sin fork**.
4. **CONSENSUS**: Los agentes votan. Si no hay ≥67% de aprobación, se muta la estrategia.
5. **FUSION**: Se ensambla la solución final verificada por PoQ (Proof of Quality).
6. **COMMIT**: El aprendizaje se guarda de vuelta en CORTEX.

### Matriz de Lanzamiento

| Necesidad | `fork_context` | Overrides (`agent_type` / `model` / `reasoning_effort`) | Patrón correcto |
|:----------|:--------------:|:---------------------------------------------------------:|:----------------|
| Mantener todo el contexto del padre | ✅ | ❌ | Heredar contexto y aceptar el perfil del runtime |
| Cambiar perfil o modelo | ❌ | ✅ | Enviar resumen/contexto mínimo y fijar perfil explícito |
| Duda entre ambos | ❌ | ✅ | Preferir contexto sintetizado antes que forzar overrides incompatibles |

---

## 🛠️ Comandos de Bajo Nivel

Si quieres ver el cerebro del enjambre en acción:

```bash
cd ~/game/moskv-swarm
# Ejecutar el motor de formación adaptativa
python -m agents.centauro_engine --mission "Despliega LEGIØN en modo auditoría"
```

---

> [!WARNING]
> **LEGIØN-1** consume muchos recursos de API y contexto.
> Úsalo cuando la excelencia no es opcional. Para tareas diarias, usa el enjambre estándar de `400-subagents`.
>
> Si el runtime devuelve un guard por `fork_context=true`, no luches contra él:
> cambia a fork completo sin overrides o a contexto sintetizado con perfil explícito.
