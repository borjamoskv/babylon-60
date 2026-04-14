#!/usr/bin/env node

/**
 * Ejecuta el dispatcher con un flujo predefinido y un texto de tarea.
 * Uso:
 *   node scripts/model-task-runner.mjs build "texto"
 *   npm run task:build -- "texto"
 */
import { spawnSync } from 'node:child_process';
import * as path from 'node:path';
import * as fs from 'node:fs';

const SUPPORTED_FLOWS = ['auto', 'build', 'release', 'ship', 'web', 'test'];

const args = process.argv.slice(2);
if (args.includes('--help') || args.includes('-h') || args.length === 0) {
  printUsage();
  process.exit(args.length === 0 ? 1 : 0);
}

const lifecycleFlow = getLifecycleFlow();
const parsed = parseArgs(args);
let flow = parsed.flow || lifecycleFlow;
let taskPrompt = parsed.taskPrompt.trim();

if (!flow && !lifecycleFlow && !parsed.forceFlowFromPrompt) {
  flow = 'auto';
} else if (!flow && parsed.forceFlowFromPrompt) {
  flow = parsed.firstToken;
}

if (!SUPPORTED_FLOWS.includes(flow)) {
  process.stderr.write(`model task runner failed: flujo desconocido '${flow || '<vacío>'}'. Usa uno de: ${SUPPORTED_FLOWS.join(', ')}\n`);
  process.exit(1);
}

if (!taskPrompt && !lifecycleFlow) {
  taskPrompt = parsed.taskFromFlowAwarePrompt.trim();
}

const wantsJson = parsed.wantsJson;
if (!taskPrompt) {
  taskPrompt = fs.readFileSync(0, 'utf8').toString().trim();
}

if (!taskPrompt) {
  printUsage();
  process.exit(1);
}

const dispatcher = path.resolve(process.cwd(), 'scripts/model-dispatcher.mjs');
const runnerArgs = ['--auto'];
if (flow !== 'auto') {
  runnerArgs.push(`--flow=${flow}`);
}
if (wantsJson) {
  runnerArgs.push('--json');
}
runnerArgs.push(taskPrompt);

const run = spawnSync(process.execPath, [dispatcher, ...runnerArgs], {
  stdio: 'inherit',
});

if (run.error) {
  process.stderr.write(`model task runner failed: ${run.error.message}\n`);
  process.exit(1);
}

process.exit(run.status ?? 0);

function printUsage() {
  const lines = [
    'Uso:',
    '  npm run task:build -- "Texto de tarea"',
    '  npm run task:web -- --json "Texto de tarea"  # opción JSON',
    '  echo "Texto de tarea" | npm run task:web -- --json',
    `Flujos soportados: ${SUPPORTED_FLOWS.join(', ')}`,
  ];
  process.stdout.write(`${lines.join('\n')}\n`);
}

function parseArgs(argv) {
  const result = {
    flow: '',
    wantsJson: false,
    taskPrompt: '',
    taskFromFlowAwarePrompt: '',
    forceFlowFromPrompt: false,
    firstToken: '',
  };

  const parts = [];
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--help' || arg === '-h') {
      printUsage();
      process.exit(0);
    }

    if (arg === '--json') {
      result.wantsJson = true;
      continue;
    }

    if (arg.startsWith('--flow=')) {
      result.flow = arg.slice('--flow='.length);
      continue;
    }

    if (arg === '--flow' && argv[i + 1]) {
      result.flow = argv[i + 1];
      i += 1;
      continue;
    }

    if (arg.startsWith('-') || arg === '') {
      continue;
    }

    parts.push(arg);
  }

  result.taskPrompt = parts.join(' ');
  result.taskFromFlowAwarePrompt = parts[0] === result.flow ? parts.slice(1).join(' ') : result.taskPrompt;
  result.firstToken = parts[0] || '';

  if (!result.flow && result.firstToken && SUPPORTED_FLOWS.includes(result.firstToken)) {
    result.forceFlowFromPrompt = true;
    result.flow = result.firstToken;
    result.taskFromFlowAwarePrompt = parts.slice(1).join(' ');
  }

  return result;
}

function getLifecycleFlow() {
  const event = process.env.npm_lifecycle_event || '';
  if (!event.startsWith('task:')) return '';
  const inferred = event.replace('task:', '');
  return SUPPORTED_FLOWS.includes(inferred) ? inferred : '';
}
