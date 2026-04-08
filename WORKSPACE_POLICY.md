# CORTEX Workspace Policy

> El core de CORTEX no puede volver a operar como cajon de sastre. Este archivo fija el source of truth y separa core, docs, marketing, backups y rescues.

## 1. Canon Primario

Toda tarea de desarrollo de CORTEX se ejecuta por defecto en:

`/Users/borjafernandezangulo/30_CORTEX`

Este directorio es el unico source of truth del producto.

## 2. Repos Satelite Permitidos

Estos repos existen, pero no son canon del core:

- `Docs`: `/Users/borjafernandezangulo/30_CORTEX_DOCS`
- `Marketing / landing`: `/Users/borjafernandezangulo/cortexpersist-landing`
- `Profile`: `/Users/borjafernandezangulo/borjamoskv`
- `Proyecto separado`: `/Users/borjafernandezangulo/antigravity`

Cuando una tarea pertenezca claramente a uno de esos dominios, se trabaja alli. No se replica la misma modificacion causal entre el core y un repo satelite.

## 3. Zonas No Canonicas

Estas rutas no deben usarse como base de desarrollo normal:

- `Backup`: `/Users/borjafernandezangulo/30_CORTEX_BACKUP`
- `Worktree experimental`: `/Users/borjafernandezangulo/30_CORTEX-head`
- `Rescues`: `/Users/borjafernandezangulo/10_PROJECTS/cortex-rescues`
- `Quarantine`: `/Users/borjafernandezangulo/90_REPO_RESCUE`
- `Runtime state`: `/Users/borjafernandezangulo/.cortex`
- `Home root`: `/Users/borjafernandezangulo`

La antigua ruta `LinkAgents/Cortex-Persist` queda invalidada y no debe volver a usarse como checkout operativo.

## 4. Fronteras de Repositorio

El repo canon `30_CORTEX` no debe volver a contener:

- repos Git anidados
- worktrees ajenos al propio repo
- backups documentales mezclados con source of truth
- research/bounties fuera del scope del core
- shells de marketing o snapshots web
- SDKs paralelos que dupliquen `sdks/`

Toda nueva superficie de ese tipo debe vivir en un repo hermano bajo `10_PROJECTS`, en `30_CORTEX_DOCS`, en `cortexpersist-landing` o en `90_REPO_RESCUE`, segun corresponda.

## 5. Regla Operativa

Una tarea completa vive en un solo vector fisico:

- elegir el repo correcto al inicio
- no repartir la misma tarea entre clones del mismo producto
- no usar backups, rescues o mirrors como canon de facto

Si una ruta no esta claramente clasificada, se detiene la tarea y se decide primero su ownership.
