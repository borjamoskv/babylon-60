import { defineConfig } from 'astro/config';
import react from '@astrojs/react';

// CORTEX Unified Substrate — v1.0.0 Configuration
export default defineConfig({
  output: 'static',
  integrations: [
    react(),
  ],
});
