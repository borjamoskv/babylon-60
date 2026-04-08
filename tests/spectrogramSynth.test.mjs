import assert from 'node:assert/strict';
import test from 'node:test';

import {
  GRID_HEIGHT,
  GRID_WIDTH,
  diffuseGrid,
  encodeWav,
  paintGrid,
  renderGridToStereo,
  seedPreset,
} from '../src/lib/spectrogramSynth.js';

test('seedPreset returns bounded spectral energy', () => {
  const grid = seedPreset('glass-cathedral', { seed: 42 });

  assert.equal(grid.length, GRID_WIDTH * GRID_HEIGHT);
  assert.ok(grid.some((value) => value > 0.25));
  assert.ok(grid.every((value) => value >= 0 && value <= 1));
});

test('diffuseGrid spreads a concentrated impulse without leaving range', () => {
  const original = new Float32Array(GRID_WIDTH * GRID_HEIGHT);
  original[Math.floor(GRID_HEIGHT / 2) * GRID_WIDTH + Math.floor(GRID_WIDTH / 3)] = 1;

  const diffused = diffuseGrid(original, { passes: 3, amount: 0.5, seed: 7 });
  const centerIndex = Math.floor(GRID_HEIGHT / 2) * GRID_WIDTH + Math.floor(GRID_WIDTH / 3);
  const rightNeighborIndex = centerIndex + 1;

  assert.ok(diffused[centerIndex] < original[centerIndex]);
  assert.ok(diffused[rightNeighborIndex] > 0);
  assert.ok(diffused.every((value) => value >= 0 && value <= 1));
});

test('paintGrid adds and removes energy around the pointer', () => {
  const grid = new Float32Array(GRID_WIDTH * GRID_HEIGHT);
  const painted = paintGrid(grid, { x: 12, y: 14, radius: 3 });
  const erased = paintGrid(painted, { x: 12, y: 14, radius: 2, mode: 'erase' });

  assert.ok(painted.some((value) => value > 0));
  assert.ok(erased.reduce((sum, value) => sum + value, 0) < painted.reduce((sum, value) => sum + value, 0));
});

test('renderGridToStereo produces non-silent stereo output and valid wav header', () => {
  const grid = seedPreset('neon-choir', { seed: 11 });
  const rendered = renderGridToStereo(grid, { durationSeconds: 2.5, sampleRate: 8000 });
  const wav = encodeWav([rendered.left, rendered.right], rendered.sampleRate);

  assert.equal(rendered.left.length, rendered.right.length);
  assert.ok(rendered.left.some((value) => Math.abs(value) > 0.001));
  assert.ok(rendered.right.some((value) => Math.abs(value) > 0.001));
  assert.equal(Buffer.from(wav).subarray(0, 4).toString('ascii'), 'RIFF');
  assert.equal(Buffer.from(wav).subarray(8, 12).toString('ascii'), 'WAVE');
});
