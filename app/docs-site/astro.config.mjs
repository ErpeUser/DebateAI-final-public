// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

const siteUrl = process.env.DEBATEAI_SITE_URL?.replace(/\/+$/, '') || undefined;
// Deployed as a Cloudflare Worker (see wrangler.jsonc) with the site/
// landing page at / and these docs at /docs/. Markdown cross-links are
// rewritten to relative URLs by sync-docs.mjs, so they work at any base.
export default defineConfig({
  site: siteUrl,
  base: '/docs',
  integrations: [
    starlight({
      title: 'DebateAI',
      description:
        'Real-time meeting transcription with AI agents that surface questions, objections, opportunities, and action items as the conversation happens.',
      logo: { src: './src/assets/mark.svg' },
      favicon: '/favicon.svg',
      components: { Head: './src/components/Head.astro' },
      head: [
        {
          tag: 'meta',
          attrs: { property: 'og:image', content: '/assets/og-image.png' },
        },
        {
          tag: 'meta',
          attrs: { name: 'twitter:image', content: '/assets/og-image.png' },
        },
      ],
      social: [
        {
          icon: 'github',
          label: 'GitHub',
          href: 'https://github.com/ErpeUser/DebateAI',
        },
      ],
      sidebar: [
        // ponytail: absolute path escapes the /docs base back to the landing page
        { label: '← Zur Startseite', link: '/' },
        {
          label: 'Erste Schritte',
          items: [
            { label: 'Übersicht', link: '/' },
            'quickstart',
            'api-keys',
            'architecture',
          ],
        },
        {
          label: 'Referenz',
          items: [
            'agents',
            'audio-pipeline',
            'websocket-protocol',
            'rest-api',
            'configuration',
            'deployment',
            'releasing',
          ],
        },
      ],
      customCss: ['./src/styles/custom.css'],
    }),
  ],
});
