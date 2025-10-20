import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://www.virtauto.de',
  output: 'static',
  markdown: { shikiConfig: { theme: 'github-dark' } }
});
