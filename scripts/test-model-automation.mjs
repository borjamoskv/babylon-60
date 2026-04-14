#!/usr/bin/env node

import { spawnSync } from 'node:child_process';
import assert from 'node:assert/strict';
import path from 'node:path';

const nodePath = process.execPath;
const scriptsRoot = path.resolve(process.cwd(), 'scripts');

const tests = [
  testInvalidFlowJson,
  testDispatchFailedCommandJson,
  testBlankTaskWithJson,
  testWhitespaceTaskCommandIgnored,
  testAutoFlowFromStdin,
  testTaskRunnerReadsStdin,
  testTaskRunnerFlagsOrder,
  testTaskRunnerInvalidFlow,
  testTaskRunnerLifecycleFlowAuto,
  testFlowMappingsExecuted,
  testFlowMappingsDryRun,
  testRouterGuideText,
  testRouterGuideJson,
];

for (const test of tests) {
  try {
    test();
    // eslint-disable-next-line no-console
    console.log(`PASS: ${test.name}`);
  } catch (error) {
    console.error(`FAIL: ${test.name}`);
    console.error(error.message);
    process.exit(1);
  }
}

function runScript(relativeScript, args, env = {}, input = undefined) {
  return spawnSync(nodePath, [path.join(scriptsRoot, relativeScript), ...args], {
    encoding: 'utf8',
    cwd: process.cwd(),
    input,
    env: {
      ...process.env,
      ...env,
    },
    stdio: ['pipe', 'pipe', 'pipe'],
  });
}

function extractJsonFromEnd(stdout) {
  const start = stdout.lastIndexOf('\n{');
  const payload = start === -1 ? stdout.trim() : stdout.slice(start + 1).trim();
  return JSON.parse(payload);
}

function testInvalidFlowJson() {
  const result = runScript('model-dispatcher.mjs', ['--json', '--flow=invalid', 'texto'], { TASK_COMMAND: '' });
  assert.equal(result.status, 1, 'esperaba salida en error para flujo inválido');
  const payload = JSON.parse(result.stdout.trim());
  assert.equal(payload.error, 'flujo_desconocido');
  assert.equal(payload.requestedFlow, 'invalid');
}

function testDispatchFailedCommandJson() {
  const result = runScript('model-dispatcher.mjs', ['--auto', '--json', 'necesito lanzar tarea'], {
    TASK_FLOW: 'web',
    TASK_COMMAND: 'false',
  });
  assert.equal(result.status, 1, 'esperaba salida en error por comando fallido');
  const payload = extractJsonFromEnd(result.stdout);
  assert.equal(payload.status, 'failed');
  assert.equal(payload.exitCode, 1);
  assert.equal(payload.executed, 'false');
}

function testBlankTaskWithJson() {
  const result = runScript('model-dispatcher.mjs', ['--json'], {}, '');
  assert.equal(result.status, 1, 'esperaba error cuando no hay texto de tarea');
  const payload = JSON.parse(result.stdout.trim());
  assert.equal(payload.error, 'tarea_vacia');
}

function testWhitespaceTaskCommandIgnored() {
  const result = runScript('model-dispatcher.mjs', ['--json', 'texto breve'], {
    TASK_COMMAND: '   ',
  });
  assert.equal(result.status, 0, 'esperaba solo recomendación sin ejecución de comando');
  const payload = extractJsonFromEnd(result.stdout);
  assert.ok(!('executed' in payload), 'no debería ejecutar comando con TASK_COMMAND en blanco');
}

function testAutoFlowFromStdin() {
  const result = runScript(
    'model-task-runner.mjs',
    ['--json'],
    {
      TASK_COMMAND: 'node -e "console.log(process.env.CODEX_MODEL)"',
    },
    'texto desde stdin sin flow',
  );
  assert.equal(result.status, 0, 'esperaba inferencia automática de flujo cuando no se provee explícito');
  const payload = extractJsonFromEnd(result.stdout);
  assert.equal(payload.status, 'ok');
  assert.equal(payload.executed, 'node -e "console.log(process.env.CODEX_MODEL)"');
}

function testTaskRunnerReadsStdin() {
  const result = runScript(
    'model-task-runner.mjs',
    ['build', '--json'],
    {
      TASK_COMMAND: 'node -e "console.log(process.env.CODEX_MODEL)"',
      MODEL_TEST_MARKER: '1',
    },
    'texto proveniente de stdin',
  );
  assert.equal(result.status, 0, 'esperaba ejecución exitosa leyendo texto de stdin');
  const payload = extractJsonFromEnd(result.stdout);
  assert.equal(payload.status, 'ok');
  assert.equal(payload.executed, 'node -e "console.log(process.env.CODEX_MODEL)"');
}

function testTaskRunnerFlagsOrder() {
  const result = runScript(
    'model-task-runner.mjs',
    ['web', 'texto de flujo por posición', '--json'],
    {
      TASK_COMMAND: 'node -e "console.log(process.env.CODEX_MODEL)"',
    },
  );
  assert.equal(result.status, 0, 'esperaba ejecución exitosa con --json en posición final');
  const payload = extractJsonFromEnd(result.stdout);
  assert.equal(payload.status, 'ok');
  assert.equal(payload.executed, 'node -e "console.log(process.env.CODEX_MODEL)"');
}

function testTaskRunnerInvalidFlow() {
  const result = runScript(
    'model-task-runner.mjs',
    ['--json', '--flow=invalid', 'texto sin sentido'],
    {
      TASK_COMMAND: 'node -e "console.log(process.env.CODEX_MODEL)"',
    },
  );
  assert.equal(result.status, 1, 'esperaba error al pasar --flow inválido');
  assert.equal((result.stderr || '').includes("flujo desconocido 'invalid'"), true, 'esperaba mensaje de flujo desconocido');
}

function testTaskRunnerLifecycleFlowAuto() {
  const result = runScript(
    'model-task-runner.mjs',
    ['--json', 'texto desde flujo lifecycle'],
    {
      TASK_COMMAND: 'node -e "console.log(process.env.CODEX_MODEL)"',
      npm_lifecycle_event: 'task:release',
    },
  );
  assert.equal(result.status, 0, 'esperaba éxito usando flujo inferido por lifecycle event');
  const payload = extractJsonFromEnd(result.stdout);
  assert.equal(payload.status, 'ok');
  assert.equal(payload.flow, 'release');
  assert.equal(payload.executed, 'node -e "console.log(process.env.CODEX_MODEL)"');
}

function testFlowMappingsExecuted() {
  const flows = ['build', 'web', 'test', 'ship', 'release'];
  const command = 'node -e "console.log(process.env.CP_TEST_FLOW)"';
  for (const flow of flows) {
    const result = runScript(
      'model-dispatcher.mjs',
      ['--json', `--flow=${flow}`, `texto que incluye ${flow}`],
      {
        TASK_COMMAND: command,
        CP_TEST_FLOW: flow,
      },
    );
    assert.equal(result.status, 0, `esperaba status 0 para flujo ${flow}`);
    const payload = extractJsonFromEnd(result.stdout);
    assert.equal(payload.flow, flow, `esperaba flow ${flow}`);
    assert.equal(payload.status, 'ok');
    assert.equal(payload.executed, command);
  }
}

function testFlowMappingsDryRun() {
  const flows = ['build', 'web', 'test', 'ship', 'release'];
  for (const flow of flows) {
    const result = runScript(
      'model-dispatcher.mjs',
      ['--json', '--dry-run', `--flow=${flow}`, `texto sin ejecutar para ${flow}`],
    );
    assert.equal(result.status, 0, `esperaba status 0 en dry-run para flujo ${flow}`);
    const payload = extractJsonFromEnd(result.stdout);
    assert.equal(payload.flow, flow, `esperaba flow ${flow} en dry-run`);
    assert.equal(payload.status, 'dry-run');
    assert.equal(typeof payload.command, 'string');
  }
}

function testRouterGuideText() {
  const result = runScript('model-router.mjs', ['--guide']);
  assert.equal(result.status, 0, 'esperaba salida de guía sin error');
  assert.ok(result.stdout.includes('Guía de uso por modelo'), 'la guía debería incluir cabecera');
  assert.ok(result.stdout.includes('gpt-5.3-codex-spark'), 'la guía debería incluir gpt-5.3-codex-spark');
}

function testRouterGuideJson() {
  const result = runScript('model-router.mjs', ['--guide', '--json']);
  assert.equal(result.status, 0, 'esperaba salida JSON de guía');
  const payload = JSON.parse(result.stdout.trim());
  assert.ok(Array.isArray(payload.modelos), 'esperaba array "modelos"');
  assert.equal(payload.modelos.length, 5, 'esperaba todos los modelos en la guía');
  assert.ok(payload.modelos.every((entry) => entry.id && entry.mejor_para), 'cada entrada debe incluir id y mejor_para');
}
