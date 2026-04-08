const TOKEN_RE = /[a-z0-9]+/g;

function fallbackTitle(url) {
  const segments = url.split('/').filter(Boolean);
  return segments[segments.length - 1] || url;
}

export function buildExcerpt(text = '', length = 220) {
  const normalized = text.replace(/\s+/g, ' ').trim();
  if (normalized.length <= length) {
    return normalized;
  }
  return `${normalized.slice(0, length - 3)}...`;
}

function derivePathLabel(url) {
  try {
    const { pathname } = new URL(url);
    return pathname === '/' ? '/' : pathname.replace(/\/$/, '');
  } catch {
    return url;
  }
}

export function normalizePageCatalog(pageCatalog = {}, scrapeResults = []) {
  const scrapeByUrl = new Map(scrapeResults.map((record) => [record.url, record]));

  return Object.values(pageCatalog)
    .map((page) => ({
      ...page,
      url: page.url,
      title: page.title || fallbackTitle(page.url),
      bucket: page.bucket || 'unknown',
      status: page.status || 'unknown',
      contentLength: Number(page.content_length || 0),
      bundleRefs: Array.isArray(page.bundle_refs) ? page.bundle_refs : [],
      strategy: page.strategy || 'unknown',
      elapsedMs: Number(page.elapsed_ms || 0),
      contentHash: page.content_hash || '',
      pathLabel: derivePathLabel(page.url),
      excerpt: buildExcerpt(scrapeByUrl.get(page.url)?.content || ''),
    }))
    .sort((left, right) => left.url.localeCompare(right.url));
}

export function tokenize(text = '') {
  return Array.from(
    new Set(
      (text.toLowerCase().match(TOKEN_RE) || []).filter(
        (token) => token.length >= 3 && !/^\d+$/.test(token),
      ),
    ),
  );
}

export function buildBucketStats(pages) {
  const buckets = new Map();

  for (const page of pages) {
    const current = buckets.get(page.bucket) || {
      bucket: page.bucket,
      count: 0,
      totalChars: 0,
      maxChars: 0,
    };

    current.count += 1;
    current.totalChars += page.contentLength;
    current.maxChars = Math.max(current.maxChars, page.contentLength);
    buckets.set(page.bucket, current);
  }

  return Array.from(buckets.values())
    .map((bucket) => ({
      ...bucket,
      averageChars: Math.round(bucket.totalChars / Math.max(bucket.count, 1)),
    }))
    .sort((left, right) => right.count - left.count || left.bucket.localeCompare(right.bucket));
}

export function buildLongestPages(pages, limit = 12) {
  return [...pages]
    .sort((left, right) => right.contentLength - left.contentLength)
    .slice(0, limit);
}

function scorePage(page, queryTokens, rawQuery) {
  if (!rawQuery) {
    return page.contentLength / 1000 + page.bundleRefs.length * 0.35;
  }

  const title = page.title.toLowerCase();
  const url = page.url.toLowerCase();
  const bucket = page.bucket.toLowerCase();
  const pathLabel = (page.pathLabel || '').toLowerCase();
  const excerpt = (page.excerpt || '').toLowerCase();
  const haystack = `${title} ${url} ${bucket} ${pathLabel} ${excerpt}`;

  let score = 0;

  if (haystack.includes(rawQuery)) {
    score += 12;
  }

  for (const token of queryTokens) {
    if (title.includes(token)) {
      score += 5;
    }
    if (url.includes(token)) {
      score += 4;
    }
    if (bucket.includes(token)) {
      score += 3;
    }
    if (pathLabel.includes(token)) {
      score += 3;
    }
    if (excerpt.includes(token)) {
      score += 1.5;
    }
  }

  const overlap = queryTokens.filter((token) => haystack.includes(token)).length;
  if (queryTokens.length) {
    score += overlap * 2;
  }

  return score + Math.min(page.bundleRefs.length, 8) * 0.08;
}

export function filterPages(
  pages,
  {
    query = '',
    bucket = 'all',
    sort = 'relevance',
  } = {},
) {
  const rawQuery = query.trim().toLowerCase();
  const queryTokens = tokenize(rawQuery);

  const filtered = pages
    .filter((page) => bucket === 'all' || page.bucket === bucket)
    .map((page) => ({
      ...page,
      searchScore: scorePage(page, queryTokens, rawQuery),
    }))
    .filter((page) => !rawQuery || page.searchScore > 0);

  switch (sort) {
    case 'length':
      return filtered.sort(
        (left, right) =>
          right.contentLength - left.contentLength || left.title.localeCompare(right.title),
      );
    case 'title':
      return filtered.sort(
        (left, right) => left.title.localeCompare(right.title) || left.url.localeCompare(right.url),
      );
    default:
      return filtered.sort(
        (left, right) =>
          right.searchScore - left.searchScore ||
          right.contentLength - left.contentLength ||
          left.title.localeCompare(right.title),
      );
  }
}

export function formatNumber(value) {
  return new Intl.NumberFormat('en-US').format(value);
}
