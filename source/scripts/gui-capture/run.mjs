import { createHash, randomUUID } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { AgentBrowser, prepareCapture, restoreCapture, scrollContainers, moveScroll, waitForContent, validateCaptureUrl } from './capture.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const option = (name, fallback) => { const i = args.indexOf(name); return i < 0 ? fallback : args[i + 1]; };
const url = validateCaptureUrl(option('--url', 'http://127.0.0.1:8474/?desktop=1'));
const folder = resolve(option('--output', join(here, '../../../evidence/gui-capture', new Date().toISOString().replace(/[:.]/g, '-'))));
mkdirSync(folder, { recursive: true });
const browser = new AgentBrowser(`gui-capture-${randomUUID().slice(0, 12)}`);
const manifest = { startedAt: new Date().toISOString(), engine: 'agent-browser', engineVersion: null, url,
  sourceHead: execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8', cwd: here }).trim(),
  sourceDirty: !!execFileSync('git', ['status', '--porcelain', '--untracked-files=no'], { encoding: 'utf8', cwd: here }).trim(),
  evidence: 'Browser rendering of the supplied local application; browser-only debate fixtures, genuine read-only settings. No Windows build or hardware test.',
  captureCode: Object.fromEntries(['run.mjs', 'capture.mjs', 'fixtures.js'].map(file => [file, createHash('sha256').update(readFileSync(join(here, file))).digest('hex')])),
  scope: 'Main application, creation, both active debate modes (paused fixtures), preparation, all discovered review/settings tabs, material, sources, laboratory iframe. Excludes native tray/installer and authenticated external login windows.',
  viewport: { width: Number(option('--width', 1440)), height: Number(option('--height', 900)) }, surfaces: [], errors: [] };
if (!Number.isInteger(manifest.viewport.width) || !Number.isInteger(manifest.viewport.height) || manifest.viewport.width < 800 || manifest.viewport.height < 600) throw new Error('Viewport must be at least 800 x 600');
const escape = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const slug = text => text.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-zA-Z0-9]+/g, '-').replace(/^-|-$/g, '').toLowerCase();
function shot(name, kind, metadata = {}) {
  const file = `${name}.png`, path = join(folder, file);
  const dialog = kind === 'full' && browser.evaluate(() => {
    const el = [...document.querySelectorAll('dialog[open],[role=dialog][aria-modal=true]')].find(el => el.getClientRects().length);
    if (el) el.setAttribute('data-gui-full-target', 'true'); return !!el;
  });
  browser.run('screenshot', ...(dialog ? ['[data-gui-full-target="true"]'] : kind === 'full' ? ['--full'] : []), path);
  const bytes = readFileSync(path);
  return { file, kind, width: bytes.readUInt32BE(16), height: bytes.readUInt32BE(20),
    sha256: createHash('sha256').update(bytes).digest('hex'), ...metadata };
}
function click(name, scope = 'body', prefix = false) {
  browser.evaluate((name, scope, prefix) => {
    const norm = s => s.replace(/\s+/g, ' ').trim();
    const nodes = [...document.querySelectorAll(`${scope} button,${scope} [role=tab]`)];
    const target = nodes.find(el => el.getClientRects().length && !el.disabled &&
      [el.getAttribute('aria-label'), el.getAttribute('title'), el.textContent].some(s => s && (prefix ? norm(s).startsWith(name) : norm(s) === name)));
    if (!target) throw new Error(`Visible control missing: ${name}`);
    target.click(); return true;
  }, name, scope, prefix);
  browser.evaluate(async () => { await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))); return true; });
}
function waitText(text) { browser.run('wait', '--fn', `document.body.innerText.toLowerCase().includes(${JSON.stringify(text.toLowerCase())})`); }
async function surface(name) {
  const item = { name, status: 'running', screenshots: [] }; manifest.surfaces.push(item);
  try {
    item.readiness = browser.evaluate(waitForContent);
    item.screenshots.push(shot(`${name}-original`, 'original-viewport'));
    const expanded = browser.evaluate(prepareCapture, { flatten: false });
    item.expanded = expanded.expanded;
    item.screenshots.push(shot(`${name}-viewport`, 'viewport'));
    const containers = browser.evaluate(scrollContainers);
    item.scrollContainers = containers;
    let count = 0;
    for (const container of containers) {
      if (!container.height) throw new Error('Zero-height scroll container');
      const end = container.total - container.height;
      const offsets = [];
      for (let offset = 0; offset < end; offset += Math.max(100, Math.floor(container.height * .8))) offsets.push(offset);
      offsets.push(end);
      const right = container.totalWidth - container.width, horizontal = [];
      for (let offset = 0; offset < right; offset += Math.max(100, Math.floor(container.width * .8))) horizontal.push(offset);
      horizontal.push(right);
      for (const offset of offsets) for (const left of horizontal) {
        if (++count > 200) throw new Error('Scroll coverage limit exceeded (not complete)');
        const actual = browser.evaluate(moveScroll, container, offset, left);
        if (Math.abs(actual.top - offset) > 3 || Math.abs(actual.left - left) > 3) throw new Error(`Scroll ${container.id} missed requested position`);
        item.screenshots.push(shot(`${name}-${container.id}-${String(count).padStart(3, '0')}`, 'scroll-viewport', { container: container.id, framePath: container.framePath, offset: actual }));
      }
      browser.evaluate(moveScroll, container, container.original, container.originalLeft);
    }
    browser.evaluate(restoreCapture);
    item.fullContent = browser.evaluate(prepareCapture);
    item.screenshots.push(shot(`${name}-full-content`, 'full', { layout: 'Expanded scroll containers; use viewport tiles to judge original layout' }));
    const bad = r => r.remaining.length || r.overflow.length || r.uncapturedFrames.length || r.frames.some(bad);
    if (bad(item.fullContent)) throw new Error('Uncaptured disclosure, scroll content or frame; inspect fullContent in manifest');
    item.status = 'captured';
    console.log(`Captured ${name} (${item.screenshots.length} images)`);
  } catch (error) { item.status = 'failed'; item.error = error.message; throw error; }
  finally { browser.evaluate(restoreCapture); }
}
async function step(name, fn) {
  try { await fn(); } catch (error) { manifest.errors.push({ name, error: error.message.slice(0, 600) }); console.error(`FAILED ${name}: ${error.message.slice(0, 200)}`); }
}
async function tabs(prefix, selector) {
  const labels = browser.evaluate(selector => [...document.querySelectorAll(selector)].filter(el => el.getClientRects().length)
    .map(el => ({ id: el.id, text: el.textContent.replace(/\s+/g, ' ').trim() })), selector);
  if (!labels.length) throw new Error(`No tabs discovered for ${prefix}`);
  for (const [i, tab] of labels.entries()) await step(`${prefix}-${tab.text}`, async () => {
    if (tab.id) browser.evaluate(id => { document.getElementById(id).click(); return true; }, tab.id);
    else click(tab.text);
    await surface(`${prefix}-${String(i + 1).padStart(2, '0')}-${slug(tab.text)}`);
  });
}
try {
  manifest.engineVersion = execFileSync(browser.binary, ['--version'], { encoding: 'utf8', windowsHide: true }).trim();
  browser.run('--init-script', join(here, 'fixtures.js'), 'open', url);
  browser.run('set', 'viewport', manifest.viewport.width, manifest.viewport.height);
  waitText('Einstellungen');
  if (!browser.evaluate(() => window.__guiCaptureEvidence?.fixture === true)) throw new Error('Read-only fixture guard did not initialize');
  manifest.applicationVersion = browser.evaluate(async () => (await (await fetch('/api/meta')).json()).version);
  const theme = option('--theme', 'dark');
  const themeButton = theme === 'dark' ? 'Zum dunklen Design wechseln' : 'Zum hellen Design wechseln';
  if (browser.evaluate(label => [...document.querySelectorAll('button')].some(el => el.getAttribute('aria-label') === label || el.title === label), themeButton)) click(themeButton);
  manifest.theme = theme;
  if (browser.evaluate(() => !!document.querySelector('button[title="Zurück"]'))) click('Zurück');
  await step('welcome', () => surface('01-welcome'));
  await step('create', async () => {
    click('Neue Debatte'); browser.run('wait', '[role=dialog] input'); await surface('02-create');
    click('Erstellen', '[role=dialog]'); waitText('Gespräch starten'); await surface('03-created-preparation');
  });
  for (const [name, title] of [['04-active-persuasive', 'GUI – Aktive Ansicht'], ['05-active-forceful', 'GUI – Brutal-sachlich']]) {
    await step(name, async () => { click(title, 'body', true); waitText('Live-Argumente'); await surface(name); });
  }
  await step('review', async () => {
    click('GUI – Abgeschlossene Debatte', 'body', true); browser.run('wait', '[role=tablist][aria-label="Nachbereitung"]');
    await tabs('06-review', '[role=tablist][aria-label="Nachbereitung"] [role=tab]');
  });
  for (const [name, title] of [['07-material', 'Material'], ['08-sources', 'Quellen']]) {
    await step(name, async () => { click(title); await surface(name); });
  }
  await step('source-create-form', async () => {
    click('Neue Wissensquelle'); await surface('08-sources-create-form'); click('Abbrechen');
  });
  await step('settings', async () => {
    click('Einstellungen'); waitText('KI-Anbieter');
    await tabs('09-settings', 'nav[aria-label="Bereiche der Einstellungen"] button');
  });
  await step('laboratory', async () => {
    click('Testlabor');
    browser.run('wait', '--fn', "!!document.querySelector('iframe')?.contentDocument?.querySelector('select')");
    await surface('10-laboratory');
    browser.evaluate(() => { document.querySelector('iframe').contentDocument.getElementById('load-demo').click(); return true; });
    await surface('11-laboratory-blind-demo');
  });
  manifest.writeGuard = browser.evaluate(() => window.__guiCaptureEvidence);
} catch (error) { manifest.errors.push({ name: 'startup', error: error.message.slice(0, 600) }); }
finally {
  try { browser.run('close'); } catch { manifest.errors.push({ name: 'cleanup', error: 'Browser session did not close' }); }
  manifest.finishedAt = new Date().toISOString();
  manifest.status = manifest.errors.length ? 'incomplete' : 'complete-for-declared-scope';
  writeFileSync(join(folder, 'manifest.json'), JSON.stringify(manifest, null, 2));
  writeFileSync(join(folder, 'index.html'), `<!doctype html><html lang="de"><meta charset="utf-8"><title>DebateAI GUI-Kontrolle</title>
    <style>body{font:16px system-ui;background:#15191e;color:#eee;max-width:1200px;margin:30px auto}a{color:#c8ed87}img{max-width:100%;height:auto;border:1px solid #555}details{padding:12px}pre{white-space:pre-wrap}</style>
    <h1>DebateAI GUI-Kontrolle</h1><p>${escape(manifest.status)}</p><p>${escape(manifest.evidence)}</p><p>${escape(manifest.scope)}</p>
    <p>Vollinhalt-Bilder lösen Scrollgrenzen für die Inhaltskontrolle auf. Die unveränderte Darstellung steht in den Ausschnitten mit dokumentierten Scrollpositionen. Keine zusammengesetzten Fensterkopien.</p>
    <p><a href="manifest.json">Vollständiger Abdeckungsbericht mit Prüfsummen</a></p><pre>${escape(JSON.stringify(manifest.errors, null, 2))}</pre>
    ${manifest.surfaces.map(s => `<h2>${escape(s.name)} — ${escape(s.status)}</h2>${s.screenshots.map(img => `<details><summary>${escape(img.file)} (${img.width} × ${img.height})</summary><a href="${img.file}"><img loading="lazy" src="${img.file}"></a></details>`).join('')}`).join('')}</html>`);
}
console.log(`GUI report: ${folder}`);
if (manifest.errors.length) process.exitCode = 1;
