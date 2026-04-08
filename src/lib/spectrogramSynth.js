const TAU = Math.PI * 2;

export const GRID_WIDTH = 72;
export const GRID_HEIGHT = 48;
export const DEFAULT_SAMPLE_RATE = 16_000;
export const DEFAULT_DURATION_SECONDS = 4;

function clamp(value, min = 0, max = 1) {
  return Math.min(max, Math.max(min, value));
}

function hashString(value) {
  let hash = 1779033703 ^ value.length;

  for (let index = 0; index < value.length; index += 1) {
    hash = Math.imul(hash ^ value.charCodeAt(index), 3432918353);
    hash = (hash << 13) | (hash >>> 19);
  }

  return (hash >>> 0) || 1;
}

function mulberry32(seed) {
  let state = seed >>> 0;

  return () => {
    state += 0x6d2b79f5;
    let next = state;
    next = Math.imul(next ^ (next >>> 15), next | 1);
    next ^= next + Math.imul(next ^ (next >>> 7), next | 61);
    return ((next ^ (next >>> 14)) >>> 0) / 4294967296;
  };
}

function indexFor(x, y, width) {
  return y * width + x;
}

function stampGaussian(grid, width, height, centerX, centerY, radiusX, radiusY, intensity) {
  const minX = Math.max(0, Math.floor(centerX - radiusX * 3));
  const maxX = Math.min(width - 1, Math.ceil(centerX + radiusX * 3));
  const minY = Math.max(0, Math.floor(centerY - radiusY * 3));
  const maxY = Math.min(height - 1, Math.ceil(centerY + radiusY * 3));

  for (let y = minY; y <= maxY; y += 1) {
    for (let x = minX; x <= maxX; x += 1) {
      const dx = (x - centerX) / Math.max(radiusX, 0.0001);
      const dy = (y - centerY) / Math.max(radiusY, 0.0001);
      const falloff = Math.exp(-(dx * dx + dy * dy) * 0.5) * intensity;
      const pointer = indexFor(x, y, width);
      grid[pointer] = clamp(grid[pointer] + falloff);
    }
  }
}

function softenColumns(grid, width, height, strength) {
  const next = new Float32Array(grid.length);

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const self = grid[indexFor(x, y, width)];
      const left = grid[indexFor(Math.max(0, x - 1), y, width)];
      const right = grid[indexFor(Math.min(width - 1, x + 1), y, width)];
      const up = grid[indexFor(x, Math.max(0, y - 1), width)];
      const down = grid[indexFor(x, Math.min(height - 1, y + 1), width)];
      const blur = self * 0.4 + left * 0.22 + right * 0.22 + up * 0.08 + down * 0.08;
      next[indexFor(x, y, width)] = clamp(self * (1 - strength) + blur * strength);
    }
  }

  return next;
}

export function createEmptyGrid(width = GRID_WIDTH, height = GRID_HEIGHT) {
  return new Float32Array(width * height);
}

export function paintGrid(
  source,
  {
    width = GRID_WIDTH,
    height = GRID_HEIGHT,
    x,
    y,
    radius = 2,
    intensity = 0.9,
    mode = 'paint',
  },
) {
  const next = new Float32Array(source);
  const minX = Math.max(0, Math.floor(x - radius * 2));
  const maxX = Math.min(width - 1, Math.ceil(x + radius * 2));
  const minY = Math.max(0, Math.floor(y - radius * 2));
  const maxY = Math.min(height - 1, Math.ceil(y + radius * 2));

  for (let gridY = minY; gridY <= maxY; gridY += 1) {
    for (let gridX = minX; gridX <= maxX; gridX += 1) {
      const dx = (gridX - x) / Math.max(radius, 0.0001);
      const dy = (gridY - y) / Math.max(radius, 0.0001);
      const distance = dx * dx + dy * dy;

      if (distance > 1) {
        continue;
      }

      const falloff = (1 - distance) * intensity;
      const pointer = indexFor(gridX, gridY, width);

      if (mode === 'erase') {
        next[pointer] = clamp(next[pointer] - falloff * 0.8);
      } else {
        next[pointer] = clamp(next[pointer] + falloff);
      }
    }
  }

  return next;
}

export function seedPreset(
  presetId,
  {
    width = GRID_WIDTH,
    height = GRID_HEIGHT,
    seed = 1,
    brightness = 1,
  } = {},
) {
  const grid = createEmptyGrid(width, height);
  const random = mulberry32(hashString(`${presetId}:${seed}`));

  if (presetId === 'glass-cathedral') {
    for (let column = 0; column < width; column += 6) {
      stampGaussian(
        grid,
        width,
        height,
        column + random() * 3,
        height * (0.14 + random() * 0.22),
        1.2 + random() * 2.8,
        1.5 + random() * 3,
        0.55 + random() * 0.35,
      );
    }

    for (let index = 0; index < 7; index += 1) {
      stampGaussian(
        grid,
        width,
        height,
        random() * width,
        height * (0.55 + random() * 0.28),
        1.4 + random() * 3.2,
        3 + random() * 4,
        0.35 + random() * 0.3,
      );
    }
  } else if (presetId === 'subharmonic-rain') {
    for (let index = 0; index < 26; index += 1) {
      const baseColumn = random() * width;
      const baseRow = height * (0.58 + random() * 0.36);

      stampGaussian(grid, width, height, baseColumn, baseRow, 0.9, 3 + random() * 4.5, 0.72);
      stampGaussian(
        grid,
        width,
        height,
        baseColumn + 1.8 + random() * 2,
        Math.max(1, baseRow - (3 + random() * 6)),
        0.7,
        1.4 + random() * 2.4,
        0.3,
      );
    }
  } else if (presetId === 'neon-choir') {
    for (let band = 0; band < 5; band += 1) {
      const centerRow = height * (0.12 + band * 0.14) + random() * 2;

      for (let column = 0; column < width; column += 1) {
        const sway = Math.sin(column * 0.14 + band * 0.8) * (1.5 + random() * 1.2);
        stampGaussian(
          grid,
          width,
          height,
          column,
          centerRow + sway,
          0.9,
          1.1 + random() * 1.6,
          0.08 + random() * 0.05,
        );
      }
    }
  } else {
    for (let index = 0; index < 34; index += 1) {
      stampGaussian(
        grid,
        width,
        height,
        random() * width,
        random() * height,
        0.6 + random() * 2.2,
        0.8 + random() * 3.2,
        0.3 + random() * 0.55,
      );
    }

    for (let streak = 0; streak < 4; streak += 1) {
      const pivotY = random() * height;

      for (let column = 0; column < width; column += 1) {
        stampGaussian(
          grid,
          width,
          height,
          column,
          pivotY + Math.sin(column * 0.16 + streak) * (1.4 + streak),
          0.8,
          1.2,
          0.08,
        );
      }
    }
  }

  const softened = softenColumns(grid, width, height, 0.22);

  for (let pointer = 0; pointer < softened.length; pointer += 1) {
    softened[pointer] = clamp(softened[pointer] * brightness);
  }

  return softened;
}

export function diffuseGrid(
  source,
  {
    width = GRID_WIDTH,
    height = GRID_HEIGHT,
    amount = 0.34,
    jitter = 0.018,
    decay = 0.015,
    drift = 0.42,
    passes = 1,
    seed = 1,
  } = {},
) {
  let current = new Float32Array(source);

  for (let pass = 0; pass < passes; pass += 1) {
    const random = mulberry32(hashString(`${seed}:${pass}`));
    const next = new Float32Array(current.length);

    for (let y = 0; y < height; y += 1) {
      for (let x = 0; x < width; x += 1) {
        const pointer = indexFor(x, y, width);
        const self = current[pointer];
        const left = current[indexFor(Math.max(0, x - 1), y, width)];
        const right = current[indexFor(Math.min(width - 1, x + 1), y, width)];
        const up = current[indexFor(x, Math.max(0, y - 1), width)];
        const down = current[indexFor(x, Math.min(height - 1, y + 1), width)];
        const diagA = current[indexFor(Math.max(0, x - 1), Math.max(0, y - 1), width)];
        const diagB = current[indexFor(Math.min(width - 1, x + 1), Math.min(height - 1, y + 1), width)];
        const drifted =
          left * (0.28 + drift * 0.18) +
          right * 0.18 +
          up * 0.1 +
          down * 0.1 +
          diagA * 0.08 +
          diagB * 0.08;
        const blurred = self * 0.42 + drifted;
        const turbulence = (random() - 0.5) * jitter + Math.sin((x + pass) * 0.27 + y * 0.13) * 0.004;

        next[pointer] = clamp(self * (1 - amount) + blurred * amount - decay + turbulence);
      }
    }

    current = next;
  }

  return current;
}

function frequencyForBin(bin, height, minFrequency, maxFrequency) {
  const ratio = bin / Math.max(height - 1, 1);
  return maxFrequency * Math.pow(minFrequency / maxFrequency, ratio);
}

function applyFade(channel, fadeSamples) {
  const safeFadeSamples = Math.min(Math.floor(channel.length / 2), fadeSamples);

  for (let index = 0; index < safeFadeSamples; index += 1) {
    const gain = index / Math.max(safeFadeSamples - 1, 1);
    channel[index] *= gain;
    channel[channel.length - 1 - index] *= gain;
  }
}

export function renderGridToStereo(
  grid,
  {
    width = GRID_WIDTH,
    height = GRID_HEIGHT,
    durationSeconds = DEFAULT_DURATION_SECONDS,
    sampleRate = DEFAULT_SAMPLE_RATE,
    minFrequency = 55,
    maxFrequency = 4400,
    threshold = 0.035,
    stereoSpread = 0.34,
  } = {},
) {
  const totalSamples = Math.max(1, Math.floor(sampleRate * durationSeconds));
  const left = new Float32Array(totalSamples);
  const right = new Float32Array(totalSamples);
  const phases = new Float64Array(height);
  const phaseSteps = new Float64Array(height);

  for (let bin = 0; bin < height; bin += 1) {
    phaseSteps[bin] = (TAU * frequencyForBin(bin, height, minFrequency, maxFrequency)) / sampleRate;
  }

  for (let sample = 0; sample < totalSamples; sample += 1) {
    const scan = (sample / Math.max(totalSamples - 1, 1)) * (width - 1);
    const leftColumn = Math.floor(scan);
    const rightColumn = Math.min(width - 1, leftColumn + 1);
    const mix = scan - leftColumn;
    let frameLeft = 0;
    let frameRight = 0;
    let activeEnergy = 0;

    for (let bin = 0; bin < height; bin += 1) {
      const pointerA = indexFor(leftColumn, bin, width);
      const pointerB = indexFor(rightColumn, bin, width);
      const amplitude = grid[pointerA] + (grid[pointerB] - grid[pointerA]) * mix;
      phases[bin] += phaseSteps[bin];

      if (phases[bin] > TAU) {
        phases[bin] -= TAU;
      }

      if (amplitude < threshold) {
        continue;
      }

      const signal = Math.sin(phases[bin]) * amplitude;
      const pan = ((height - 1 - bin) / Math.max(height - 1, 1) - 0.5) * stereoSpread * 2;

      frameLeft += signal * (1 - pan);
      frameRight += signal * (1 + pan);
      activeEnergy += amplitude;
    }

    if (activeEnergy > 0) {
      const normalizer = 1 / Math.max(activeEnergy * 0.72, 1);
      left[sample] = Math.tanh(frameLeft * normalizer * 1.35);
      right[sample] = Math.tanh(frameRight * normalizer * 1.35);
    }
  }

  applyFade(left, Math.floor(sampleRate * 0.04));
  applyFade(right, Math.floor(sampleRate * 0.04));

  let peak = 0;

  for (let index = 0; index < totalSamples; index += 1) {
    peak = Math.max(peak, Math.abs(left[index]), Math.abs(right[index]));
  }

  const gain = peak > 0 ? 0.92 / peak : 1;

  for (let index = 0; index < totalSamples; index += 1) {
    left[index] *= gain;
    right[index] *= gain;
  }

  return {
    left,
    right,
    peak: peak * gain,
    sampleRate,
    durationSeconds,
  };
}

function writeAscii(view, offset, text) {
  for (let index = 0; index < text.length; index += 1) {
    view.setUint8(offset + index, text.charCodeAt(index));
  }
}

export function encodeWav(channels, sampleRate) {
  const channelCount = channels.length;
  const sampleCount = channels[0]?.length ?? 0;
  const bytesPerSample = 2;
  const blockAlign = channelCount * bytesPerSample;
  const dataSize = sampleCount * blockAlign;
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);

  writeAscii(view, 0, 'RIFF');
  view.setUint32(4, 36 + dataSize, true);
  writeAscii(view, 8, 'WAVE');
  writeAscii(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, channelCount, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * blockAlign, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bytesPerSample * 8, true);
  writeAscii(view, 36, 'data');
  view.setUint32(40, dataSize, true);

  let offset = 44;

  for (let sample = 0; sample < sampleCount; sample += 1) {
    for (let channel = 0; channel < channelCount; channel += 1) {
      const value = clamp(channels[channel][sample], -1, 1);
      view.setInt16(offset, value < 0 ? value * 0x8000 : value * 0x7fff, true);
      offset += 2;
    }
  }

  return buffer;
}
