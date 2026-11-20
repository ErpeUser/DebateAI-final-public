// Assembles the deployable site: the site/ landing page at /, the built
// Starlight docs at /docs/, and llms-full.txt (every docs page concatenated
// as plain markdown for AI agents, companion to site/llms.txt).
// wrangler deploys dist-site/ as Worker assets.
import { cpSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const root = import.meta.dirname;
const out = join(root, 'dist-site');
rmSync(out, { recursive: true, force: true });
cpSync(join(root, '..', 'site'), out, { recursive: true });
cpSync(join(root, 'dist'), join(out, 'docs'), { recursive: true });

// Sidebar reading order first (matches astro.config.mjs), then any new docs.
const DOCS_ORDER = ['DEBATEAI_CANONICAL_INDEX', 'quickstart', 'architecture',
  'websocket-protocol', 'rest-api', 'configuration', 'deployment',
  'releasing', 'generated-workspace', 'github-repository', 'windows-final-recovery'];
const docsSrc = join(root, '..', 'docs');
const all = readdirSync(docsSrc).filter((f) => f.endsWith('.md')).map((f) => f.replace(/\.md$/, ''));
const names = [...DOCS_ORDER.filter((n) => all.includes(n)), ...all.filter((n) => !DOCS_ORDER.includes(n))];
const sections = names.map((name) => {
  const text = readFileSync(join(docsSrc, `${name}.md`), 'utf8')
    .replace(/^<p align="center">[\s\S]*?<\/p>\s*/, '')
    .trim();
  const page = name === 'DEBATEAI_CANONICAL_INDEX' ? '' : `${name}/`;
  return `<!-- Canonical page: /docs/${page} -->\n\n${text}`;
});
writeFileSync(join(out, 'llms-full.txt'),
  '# DebateAI - full documentation\n\n' +
  '> Every page of /docs/ concatenated as plain\n' +
  '> markdown. Overview and key facts: /llms.txt\n\n' +
  sections.join('\n\n---\n\n') + '\n');
// Content under src/content/docs is a build staging area derived from app/docs.
// Remove it so the repository keeps a single editorial document source.
rmSync(join(root, 'src', 'content', 'docs'), { recursive: true, force: true });
console.log('Assembled', out, `(llms-full.txt: ${names.length} docs)`);
