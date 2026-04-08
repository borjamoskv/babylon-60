import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import starlight from '@astrojs/starlight';

const siteVariant = process.env.PUBLIC_SITE_VARIANT === 'docs' ? 'docs' : 'marketing';
const isDocsVariant = siteVariant === 'docs';
const siteUrl = process.env.SITE_URL ?? 'https://cortexpersist.com';

export default defineConfig({
  site: siteUrl,
  base: isDocsVariant ? '/docs' : undefined,
  output: 'static',
  integrations: [
    react(),
    ...(isDocsVariant
      ? [
          starlight({
            title: 'CORTEX Docs',
            logo: {
              src: './src/assets/logo-white.svg',
            },
            social: {
              github: 'https://github.com/borjamoskv/Cortex-Persist',
            },
            sidebar: [
              {
                label: 'Documentation',
                autogenerate: { directory: '' },
              },
            ],
            customCss: [
              './src/styles/custom.css',
            ],
          }),
        ]
      : []),
  ],
});
