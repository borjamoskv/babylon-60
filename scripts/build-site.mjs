import { cpSync, existsSync, mkdirSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';

const rootDir = process.cwd();
const siteUrl = (process.env.SITE_URL || 'https://cortexpersist.com').replace(/\/$/, '');
const marketingDir = resolve(rootDir, '.dist-marketing');
const docsDir = resolve(rootDir, '.dist-docs');
const finalDir = resolve(rootDir, 'dist');
const docsFinalDir = join(finalDir, 'docs');

const astroBin = process.platform === 'win32' ? 'npx.cmd' : 'npx';

function clean(path) {
  rmSync(path, { recursive: true, force: true });
}

function runBuild(outDir, env) {
  const result = spawnSync(astroBin, ['astro', 'build', '--outDir', outDir], {
    cwd: rootDir,
    stdio: 'inherit',
    env: {
      ...process.env,
      SITE_URL: siteUrl,
      ...env,
    },
  });

  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function copyIfPresent(source, destination) {
  if (existsSync(source)) {
    cpSync(source, destination, { recursive: true });
  }
}

function writeRootSitemap() {
  const xml = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    `  <url><loc>${siteUrl}/</loc></url>`,
    '</urlset>',
  ].join('\n');

  writeFileSync(join(finalDir, 'sitemap-0.xml'), `${xml}\n`, 'utf8');
}

function writeCombinedSitemap() {
  const rootSitemapPath = `${siteUrl}/sitemap-0.xml`;
  const docsSitemapPath = `${siteUrl}/docs/sitemap-0.xml`;
  const xml = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    `  <sitemap><loc>${rootSitemapPath}</loc></sitemap>`,
    `  <sitemap><loc>${docsSitemapPath}</loc></sitemap>`,
    '</sitemapindex>',
  ].join('\n');

  writeFileSync(join(finalDir, 'sitemap-index.xml'), `${xml}\n`, 'utf8');
}

clean(marketingDir);
clean(docsDir);
clean(finalDir);

runBuild(marketingDir, {
  PUBLIC_SITE_VARIANT: 'marketing',
});

runBuild(docsDir, {
  PUBLIC_SITE_VARIANT: 'docs',
  PUBLIC_MARKETING_ORIGIN: siteUrl,
});

mkdirSync(finalDir, { recursive: true });

for (const entry of readdirSync(marketingDir)) {
  copyIfPresent(join(marketingDir, entry), join(finalDir, entry));
}

clean(docsFinalDir);
mkdirSync(docsFinalDir, { recursive: true });
for (const entry of readdirSync(docsDir)) {
  copyIfPresent(join(docsDir, entry), join(docsFinalDir, entry));
}

writeRootSitemap();
writeCombinedSitemap();

clean(marketingDir);
clean(docsDir);
