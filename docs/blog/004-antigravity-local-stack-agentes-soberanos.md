---
title: "Antigravity Local: el Stack Soberano para Agentes que no Dependen de la Nube"
date: 2026-05-06
author: CORTEX Research Lab
tags: [antigravity, agentes-locales, ollama, privacidad, arquitectura]
description: "Cómo pensar un stack de agentes local-first: modelos locales para volumen, frontera para desbloqueos puntuales y memoria propia como límite de soberanía."
slug: antigravity-local-stack-agentes-soberanos
---

# Antigravity Local: el Stack Soberano para Agentes que no Dependen de la Nube

La pregunta no es si la nube sirve. Sirve. La pregunta es qué parte de tu sistema
puede permitirse depender de ella.

Para agentes de desarrollo, auditoría o investigación, la dependencia total de
un proveedor introduce tres problemas: coste variable, pérdida de privacidad y
fragilidad operativa. Cuando cada decisión pasa por una API remota, el sistema
funciona mientras el proveedor, la cuota, la red y el plan comercial estén de tu
lado.

Un stack soberano empieza con otra premisa: la nube es acelerador, no columna
vertebral.

## La regla 90/10

La arquitectura local-first más práctica no intenta que todo sea local a cualquier
precio. Ese absolutismo suele acabar en frustración. La regla útil es 90/10:

- **90% local**: tareas repetibles, navegación de archivos, refactors pequeños,
  extracción, clasificación, borradores y pruebas de bajo riesgo.
- **10% frontera**: bloqueos de arquitectura, razonamiento difícil, auditorías
  de alto impacto y decisiones donde el coste de equivocarse es mayor que el
  coste de llamar a un modelo superior.

El objetivo no es ahorrar por ahorrar. Es reservar los modelos frontera para los
momentos donde realmente cambian el resultado.

## Componentes de un stack local

Un stack de agentes local no necesita ser complejo. Necesita límites claros:

| Capa | Función |
|---|---|
| Modelo local | Inferencia barata, privada y disponible |
| Orquestador | Divide tareas, decide cuándo escalar y verifica resultados |
| Herramientas | Shell, navegador, editor, linters, tests y APIs locales |
| Memoria | Continuidad entre sesiones y modelos |
| Políticas | Qué puede tocar, qué necesita aprobación y qué debe registrar |

Ollama, modelos abiertos, wrappers de navegador y herramientas tipo Codex o
Antigravity encajan en esta lógica si se conectan a una memoria propia y a un
perímetro de permisos sobrio.

El error es creer que el modelo local es el producto. El producto es el circuito
cerrado: observar, actuar, validar, recordar.

## Privacidad como propiedad arquitectónica

Un agente de código ve cosas que no deberían salir de la máquina: rutas internas,
arquitectura propietaria, fragmentos de configuración, nombres de clientes,
errores de producción y a veces secretos que no deberían estar ahí.

La privacidad no se arregla con una promesa comercial si el flujo completo manda
todo el contexto fuera. Se diseña reduciendo superficie:

- filtrar antes de enviar;
- mantener memoria local;
- usar modelos locales para triage;
- escalar solo fragmentos mínimos;
- registrar qué salió, por qué y con qué redacción;
- bloquear categorías sensibles por defecto.

Un buen stack local no es paranoico. Es selectivo.

## El router como órgano central

La pieza crítica es el router. No debe elegir modelo por moda, sino por intención,
riesgo y evidencia disponible.

Ejemplos:

| Señal | Ruta razonable |
|---|---|
| "corrige este typo" | modelo rápido local |
| "refactor multiarchivo con tests" | modelo de código fuerte |
| "amenaza de seguridad en ruta crítica" | modelo frontera + verificación local |
| "resume estos logs sensibles" | local, sin salida externa |
| "diseña estrategia de migración" | frontera, con contexto minimizado |

Cuando el router está bien diseñado, el sistema no pregunta "qué modelo es más
inteligente". Pregunta "qué nivel de inteligencia, privacidad y coste requiere
esta tarea".

## Memoria independiente del modelo

Cambiar de modelo no debería borrar la continuidad del agente. Si ayer una tarea
falló con cierto enfoque, esa experiencia debe estar disponible hoy aunque el
motor sea otro.

Por eso la memoria debe vivir fuera del proveedor. El agente puede usar un modelo
local para ejecutar, un modelo frontera para razonar y otro distinto para revisar,
pero todos deberían consultar la misma biografía operativa.

La soberanía aparece cuando el modelo es reemplazable y la memoria permanece.

## Verificación antes de autonomía

Un stack local potente puede ejecutar mucho. Eso aumenta la necesidad de frenos.

Antes de conceder autonomía amplia, conviene exigir:

1. sandbox por defecto;
2. allowlist de herramientas;
3. tests o checks después de cambios;
4. diff visible para superficies críticas;
5. bloqueo de secretos;
6. logs locales con redacción;
7. estrategia clara de rollback.

La autonomía sin verificación solo mueve el riesgo más rápido.

## La forma madura del agente local

El agente local-first no es un rechazo de la nube. Es una relación más adulta con
ella.

Usa lo local para preservar control, privacidad y continuidad. Usa la frontera
para momentos donde la dificultad lo justifica. Usa memoria propia para que cada
sesión sea acumulativa. Usa políticas para que la velocidad no atraviese la
línea de seguridad.

El futuro práctico no será "todo local" ni "todo cloud".

Será un agente que sabe exactamente qué puede resolver en casa y qué merece
salir al exterior.
