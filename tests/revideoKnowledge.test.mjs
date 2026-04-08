import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildExcerpt,
  buildBucketStats,
  buildLongestPages,
  filterPages,
  normalizePageCatalog,
  tokenize,
} from '../src/lib/revideoKnowledge.js';

const sampleCatalog = {
  'https://redotvideo.github.io/api/core/signals': {
    url: 'https://redotvideo.github.io/api/core/signals',
    title: 'signals | Revideo',
    bucket: 'api/core',
    status: 'success',
    content_length: 11515,
    bundle_refs: ['api__core__41'],
    strategy: 'http_fast',
    elapsed_ms: 120,
    content_hash: 'a1',
  },
  'https://redotvideo.github.io/platform/render-endpoint': {
    url: 'https://redotvideo.github.io/platform/render-endpoint',
    title: 'Using your Render Endpoint | Revideo',
    bucket: 'platform',
    status: 'success',
    content_length: 3016,
    bundle_refs: ['platform__01'],
    strategy: 'http_fast',
    elapsed_ms: 98,
    content_hash: 'b2',
  },
  'https://redotvideo.github.io/flow': {
    url: 'https://redotvideo.github.io/flow',
    title: 'Animation flow | Revideo',
    bucket: 'guides',
    status: 'success',
    content_length: 8759,
    bundle_refs: ['guides__11', 'guides__12'],
    strategy: 'http_fast',
    elapsed_ms: 77,
    content_hash: 'c3',
  },
};

const sampleScrapeResults = [
  {
    url: 'https://redotvideo.github.io/api/core/signals',
    content: 'Signals orchestrate timeline changes and state propagation across animation scenes.',
  },
  {
    url: 'https://redotvideo.github.io/platform/render-endpoint',
    content: 'Render endpoint setup for production pipelines and remote rendering.',
  },
  {
    url: 'https://redotvideo.github.io/flow',
    content: 'Animation flow describes scene timing, sequencing, and timeline control.',
  },
];

test('normalizePageCatalog converts the stored catalog into an array', () => {
  const pages = normalizePageCatalog(sampleCatalog, sampleScrapeResults);

  assert.equal(pages.length, 3);
  assert.equal(pages[0].status, 'success');
  assert.ok(pages.every((page) => Array.isArray(page.bundleRefs)));
  assert.ok(pages.every((page) => typeof page.excerpt === 'string'));
});

test('buildBucketStats aggregates bucket counts and average lengths', () => {
  const pages = normalizePageCatalog(sampleCatalog, sampleScrapeResults);
  const buckets = buildBucketStats(pages);

  assert.equal(buckets[0].bucket, 'api/core');
  assert.equal(buckets[0].count, 1);
  assert.ok(buckets.some((bucket) => bucket.bucket === 'guides'));
});

test('filterPages ranks lexical matches above unrelated pages', () => {
  const pages = normalizePageCatalog(sampleCatalog, sampleScrapeResults);
  const matches = filterPages(pages, { query: 'render endpoint', sort: 'relevance' });

  assert.equal(matches[0].url, 'https://redotvideo.github.io/platform/render-endpoint');
  assert.ok(matches[0].searchScore > 0);
});

test('filterPages respects bucket filters and alternate sorting', () => {
  const pages = normalizePageCatalog(sampleCatalog, sampleScrapeResults);
  const matches = filterPages(pages, { bucket: 'guides', sort: 'length' });

  assert.equal(matches.length, 1);
  assert.equal(matches[0].url, 'https://redotvideo.github.io/flow');
});

test('buildLongestPages and tokenize stay deterministic', () => {
  const pages = normalizePageCatalog(sampleCatalog, sampleScrapeResults);
  const longest = buildLongestPages(pages, 2);

  assert.deepEqual(tokenize('Signals / timeline 2026!'), ['signals', 'timeline']);
  assert.equal(longest[0].url, 'https://redotvideo.github.io/api/core/signals');
  assert.equal(longest.length, 2);
});

test('excerpt-aware ranking can match terms that only appear in scraped content', () => {
  const pages = normalizePageCatalog(sampleCatalog, sampleScrapeResults);
  const matches = filterPages(pages, { query: 'timeline control', sort: 'relevance' });

  assert.equal(matches[0].url, 'https://redotvideo.github.io/flow');
  assert.ok(matches[0].excerpt.includes('timeline'));
});

test('buildExcerpt trims long content predictably', () => {
  const excerpt = buildExcerpt('alpha beta gamma delta epsilon zeta eta theta', 20);

  assert.equal(excerpt, 'alpha beta gamma ...');
});
