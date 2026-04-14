#!/usr/bin/env node

const { spawnSync } = await import('node:child_process');
const path = await import('node:path');
const fs = await import('node:fs');

const argv = process.argv.slice(2);
const separator = argv.indexOf('--');
const controlArgs = separator === -1 ? argv : argv.slice(0, separator);
const commandArgsInput = separator === -1 ? [] : argv.slice(separator + 1);
const taskArgs = [];
for (let i = 0; i < controlArgs.length; i += 1) {
  if (isControlArg(controlArgs[i])) {
    if (controlArgs[i] === '--flow') {
      i += 1;
    }
    continue;
  }
  taskArgs.push(controlArgs[i]);
}

const usage = printUsage();
const wantsJson = controlArgs.includes('--json');
const enableAutoFlow = controlArgs.includes('--auto');
const wantsDryRun = controlArgs.includes('--dry-run');
let flow = readFlowArgument(controlArgs);

const AUTOMATION_FLOWS = {
  build: {
    command: 'npm run build',
    description: 'Compila la web de Cortex-Persist',
  },
  release: {
    command: 'npm run build && node -e "console.log(\'release candidate listo\')"',
    description: 'Pipeline mínimo de build para release',
  },
  ship: {
    command: 'npm run build && node -e "console.log(\'artefacto preparado\')"',
    description: 'Ruta de preparación técnica base para shipping',
  },
  web: {
    command: 'npm run build',
    description: 'Compilación web estándar',
  },
  test: {
    command: 'npm run build',
    description: 'Chequeo de compilación para validación rápida',
  },
};

const SUPPORTED_FLOWS = Object.keys(AUTOMATION_FLOWS);

if (controlArgs.includes('--help') || controlArgs.includes('-h') || controlArgs.length === 0) {
  process.stdout.write(usage);
  process.exit(0);
}

if (!flow) {
  flow = process.env.TASK_FLOW || process.env.CODEX_FLOW || process.env.MODEL_ROUTER_FLOW;
}

let commandArgs = [...commandArgsInput];

let taskText = taskArgs.join(' ').trim();
if (!taskText) {
  try {
    taskText = fs.readFileSync(0, 'utf8').toString().trim();
  } catch {
    taskText = '';
  }
}

if (!taskText) {
  const error = {
    error: 'tarea_vacia',
    message: 'texto de tarea vacío. Pasa un texto como argumento o por stdin.',
    usage: 'npm run model:dispatch -- "texto de tarea" -- "npm run build"',
  };
  if (wantsJson) {
    process.stdout.write(JSON.stringify(error, null, 2));
    process.stdout.write('\n');
  } else {
    process.stdout.write(usage);
  }
  process.exit(1);
}

if (flow && !SUPPORTED_FLOWS.includes(flow)) {
  const error = {
    error: 'flujo_desconocido',
    message: `flujo inválido '${flow}'. Use uno de: ${SUPPORTED_FLOWS.join(', ')}`,
    requestedFlow: flow,
    supportedFlows: SUPPORTED_FLOWS,
  };
  if (wantsJson) {
    process.stdout.write(JSON.stringify(error, null, 2));
    process.stdout.write('\n');
  } else {
    process.stderr.write(`model dispatch failed: flujo inválido '${flow}'. Use uno de: ${SUPPORTED_FLOWS.join(', ')}\n`);
  }
  process.exit(1);
}

if (!flow && enableAutoFlow) {
  flow = inferFlowFromTask(taskText);
}

if (!flow && enableAutoFlow) {
  process.stderr.write('model dispatch failed: --auto fue pedido, pero no se encontró flujo (TASK_FLOW o --flow=build|release|ship|web|test)\n');
  process.exit(1);
}

const routerPath = path.resolve(process.cwd(), 'scripts/model-router.mjs');
const picker = spawnSync(process.execPath, [routerPath, '--json', taskText], {
  encoding: 'utf8',
  stdio: ['ignore', 'pipe', 'pipe'],
});

if (picker.error) {
  process.stderr.write(`model dispatch failed: cannot execute router (${picker.error.message})\n`);
  process.exit(1);
}

if (picker.status !== 0 || !picker.stdout.trim()) {
  process.stderr.write(`model dispatch failed: router returned status ${picker.status || 0}\n`);
  if (picker.stderr?.trim()) process.stderr.write(picker.stderr);
  process.exit(picker.status || 1);
}

let decision;
try {
  decision = JSON.parse(picker.stdout);
} catch (error) {
  process.stderr.write(`model dispatch failed: invalid router payload (${error.message})\n`);
  process.exit(1);
}

const envCommand = (
  process.env.TASK_COMMAND
  || process.env.CODEX_TASK_COMMAND
  || process.env.MODEL_ROUTER_COMMAND
  || ''
).trim();
if (!commandArgs.length && envCommand) {
  commandArgs = [envCommand];
}

if (flow && !commandArgs.length) {
  const selectedFlow = AUTOMATION_FLOWS[flow];
  if (!selectedFlow) {
    process.stderr.write(`model dispatch failed: flujo desconocido '${flow}'. Flujos disponibles: ${Object.keys(AUTOMATION_FLOWS).join(', ')}\n`);
    process.exit(1);
  }
  commandArgs = [selectedFlow.command];
}

if (!commandArgs.length) {
  if (wantsJson) {
    const recommendation = flow ? { ...decision, flow } : decision;
    process.stdout.write(JSON.stringify(recommendation, null, 2));
    process.stdout.write('\n');
    process.exit(0);
  }
  process.stdout.write(`Recomendado: ${decision.recommended.id} (${Math.round(decision.recommended.confidence)}%)\n`);
  process.stdout.write(`Motivo: ${decision.recommended.reason}\n`);
  if (flow) {
    const selectedFlow = AUTOMATION_FLOWS[flow];
    process.stdout.write(`Flujo automático activo (${flow}): ${selectedFlow.description}\n`);
  }
  process.stdout.write(`Siguientes: ${decision.alternatives.map((entry) => `${entry.id} ${Math.round(entry.confidence)}%`).join(' | ')}\n`);
  process.exit(0);
}

const command = commandArgs.join(' ');

if (wantsDryRun) {
  const payload = {
    ...decision,
    flow,
    command,
    dryRun: true,
    status: 'dry-run',
  };
  if (wantsJson) {
    process.stdout.write(JSON.stringify(payload, null, 2));
    process.stdout.write('\n');
  } else {
    process.stdout.write(`Flujo: ${flow}\n`);
    process.stdout.write(`Comando: ${command}\n`);
    process.stdout.write(`Modelo sugerido: ${decision.recommended.id} (${Math.round(decision.recommended.confidence)}%)\n`);
    process.stdout.write('Modo simulación (sin ejecutar).\n');
  }
  process.exit(0);
}

const modelEnv = {
  ...process.env,
  CODEX_MODEL: decision.recommended.id,
  MODEL_DISPATCH: decision.recommended.id,
  MODEL_ROUTER_SELECTION: decision.recommended.id,
};

process.stdout.write(`Ejecutando con modelo ${decision.recommended.id}\n`);
const run = spawnSync(command, {
  shell: true,
  stdio: 'inherit',
  env: modelEnv,
});

if (run.error) {
  if (wantsJson) {
    process.stdout.write(JSON.stringify({ ...decision, executed: command, flow, status: 'failed', reason: run.error.message }, null, 2));
    process.stdout.write('\n');
  } else {
    process.stderr.write(`model dispatch failed while executing command: ${run.error.message}\n`);
  }
  process.exit(1);
}

if (run.status && run.status !== 0) {
  if (wantsJson) {
    process.stdout.write(JSON.stringify({ ...decision, executed: command, flow, status: 'failed', exitCode: run.status }, null, 2));
    process.stdout.write('\n');
  } else {
    process.stderr.write(`model dispatch command finished with status ${run.status}\n`);
  }
  process.exit(run.status);
}

if (wantsJson) {
  process.stdout.write(JSON.stringify({ ...decision, executed: command, flow, status: 'ok' }, null, 2));
  process.stdout.write('\n');
}

function printUsage() {
  return `Uso:
  npm run model:dispatch -- "texto de tarea"
  npm run model:dispatch -- "texto de tarea" -- "npm run build"
  npm run model:dispatch -- --json "texto de tarea" -- "npm run model:pick \"texto\""
  npm run model:dispatch -- --dry-run --auto --flow=web "texto de tarea"

Salida:
  - Sin comando: sugiere modelo (formato texto o JSON).
  - Con comando: ejecuta con la variable de entorno:
      CODEX_MODEL, MODEL_DISPATCH, MODEL_ROUTER_SELECTION
  - Con --dry-run: no ejecuta, solo muestra la resolución de comando y el modelo sugerido.
  - Alternativamente, define TASK_COMMAND (o CODEX_TASK_COMMAND / MODEL_ROUTER_COMMAND) para auto-ejecutar
    el comando sin pasar -- explícito.
  - Alternativamente, define TASK_FLOW (o CODEX_FLOW / MODEL_ROUTER_FLOW) para seleccionar un flujo predefinido.
  - Usa --auto --flow=<build|release|ship|web|test> para seleccionar un comando automático.
  - Si usas --auto sin flow, el dispatcher intenta inferir el flujo por contexto del texto.
\n`;
}

function readFlowArgument(args) {
  for (let i = 0; i < args.length; i += 1) {
    if (args[i] === '--flow' && args[i + 1]) {
      return args[i + 1];
    }
    if (args[i].startsWith('--flow=')) {
      return args[i].slice('--flow='.length);
    }
  }
  return '';
}

function isControlArg(arg) {
  return (
    arg === '--json'
    || arg === '--auto'
    || arg === '--help'
    || arg === '--dry-run'
    || arg === '-h'
    || arg === '--flow'
    || arg.startsWith('--flow=')
  );
}

function inferFlowFromTask(taskText) {
  const normalized = taskText.toLowerCase();
  const has = (keyword) => normalized.includes(keyword);

  if (has('release') || has('publica') || has('deploy') || has('despliegue') || has('shipping') || has('ship')) {
    return 'release';
  }
  if (has('test') || has('prueba') || has('verificar') || has('validar') || has('qa')) {
    return 'test';
  }
  if (has('artifact') || has('artefacto') || has('prepare') || has('prepara') || has('ship')) {
    return 'ship';
  }
  if (has('web') || has('sitio') || has('landing') || has('pagina') || has('página')) {
    return 'web';
  }
  return 'build';
}
