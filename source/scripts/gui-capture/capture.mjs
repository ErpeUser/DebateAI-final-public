import { execFileSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { join } from 'node:path';

export function validateCaptureUrl(value) {
  const url = new URL(value);
  if (!['http:', 'https:'].includes(url.protocol) || !['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname)) throw new Error('Capture requires a loopback HTTP application');
  if (url.username || url.password || url.hash || [...url.searchParams.keys()].some(key => !['desktop', 'view', 'overlay'].includes(key))) throw new Error('Credentials, fragments and unknown query parameters are not allowed in capture URLs');
  if (['desktop', 'overlay'].some(key => url.searchParams.has(key) && !['0', '1'].includes(url.searchParams.get(key)))) throw new Error('Invalid desktop/overlay parameter');
  if (url.searchParams.has('view') && url.searchParams.get('view') !== 'about') throw new Error('Invalid view parameter');
  return url.href;
}

// Wait for rendered card bodies, not network-idle (the app has polling).
// Error prose is not a pending loader; diagnostic result text is preserved.
export async function waitForContent({ timeout = 20000 } = {}) {
  const started = performance.now();
  const pending = /^(?:(?:Konfiguration|Ansicht) wird geladen|(?:Angebote|Änderungen|Modellpreise|Einträge|Einstellungen) werden geladen|Wird geladen|Wird geprüft|Neuer Versuch)\s*(?:\.{3}|…)?$/i;
  let settled = 0;
  while (performance.now() - started < timeout) {
    const labels = [...document.querySelectorAll('main *,dialog[open] *,[role=dialog] *')]
      .filter(el => el.childElementCount === 0 && el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden')
      .map(el => el.textContent.replace(/\s+/g, ' ').trim()).filter(text => pending.test(text));
    if (!labels.length) { if (++settled === 3) return { waitedMs: Math.round(performance.now() - started), pending: [] }; }
    else settled = 0;
    await new Promise(resolve => requestAnimationFrame(resolve));
  }
  throw new Error('Content not ready: loading placeholders did not finish within capture timeout');
}

// No shell quoting, user profile reuse, browser credentials or API tokens.
export class AgentBrowser {
  constructor(session) {
    this.session = session;
    this.binary = process.env.AGENT_BROWSER_BINARY || (process.platform === 'win32'
      ? join(process.env.APPDATA, 'npm/node_modules/agent-browser/bin/agent-browser-win32-x64.exe') : 'agent-browser');
    if (process.platform === 'win32' && !existsSync(this.binary)) throw new Error('Install agent-browser 0.43.0 or set AGENT_BROWSER_BINARY.');
  }
  run(...args) {
    let output;
    try {
      output = execFileSync(this.binary, ['--session', this.session, '--json', ...args.map(String)], {
        encoding: 'utf8', timeout: 90000, maxBuffer: 8 * 1024 * 1024,
        windowsHide: true, env: { ...process.env, AGENT_BROWSER_DEFAULT_TIMEOUT: '20000' },
      });
    } catch (error) {
      // The CLI returns structured failures with a nonzero exit code. Do not
      // replace that diagnosis with argv/base64 scripts or potentially secret URLs.
      try { output = JSON.parse(error.stdout); } catch { throw new Error(`Browser ${args[0]} failed or timed out`); }
      throw new Error(typeof output.error === 'string' ? output.error : 'Browser command failed');
    }
    const result = JSON.parse(output);
    if (!result.success) throw new Error(result.error || 'Browser command failed');
    return result.data;
  }
  evaluate(fn, ...args) {
    const source = `(${fn.toString()})(...${JSON.stringify(args)})`;
    return this.run('eval', '-b', Buffer.from(source).toString('base64')).result;
  }
}

// Serialized into the browser. Only disclosure controls within visible content
// are eligible; navigation, hidden tabs, dropdowns and action menus are not.
export async function prepareCapture({ flatten = true } = {}) {
  if (window.__guiCaptureRestore) throw new Error('Capture transform already active');
  const undo = [], expanded = [], frames = [], failed = [], retainedPanels = [];
  const visible = el => el.getClientRects().length > 0 && getComputedStyle(el).visibility !== 'hidden';
  const eligible = el => visible(el) && !el.disabled && !el.closest('nav,aside,[role="tablist"],[role="menu"]') &&
    !el.hasAttribute('aria-haspopup') && !['tab', 'combobox'].includes(el.getAttribute('role'));
  const root = [...document.querySelectorAll('dialog[open],[role="dialog"][aria-modal="true"]')].find(visible) || document.querySelector('main') || document.body;
  const seen = new WeakSet();
  const initialOpen = [...root.querySelectorAll('button[aria-expanded="true"]')].filter(eligible);
  initialOpen.forEach(el => seen.add(el));
  undo.push(() => initialOpen.forEach(el => { if (el.isConnected && el.getAttribute('aria-expanded') !== 'true') el.click(); }));
  const panels = new Map();
  const rememberPanels = () => {
    for (const button of root.querySelectorAll('button[aria-expanded="true"]')) {
      if (!eligible(button) || button.hasAttribute('aria-controls') || panels.has(button)) continue;
      const anchor = button.nextElementSibling && ['DIV', 'SECTION', 'UL'].includes(button.nextElementSibling.tagName) ? button : button.parentElement;
      const panel = anchor?.nextElementSibling;
      if (panel && ['DIV', 'SECTION', 'UL'].includes(panel.tagName) && visible(panel)) panels.set(button, { anchor, panel: panel.cloneNode(true) });
    }
  };
  rememberPanels();
  for (let pass = 0; pass < 30; pass++) {
    const nodes = [...root.querySelectorAll('details:not([open]),button[aria-expanded="false"]')]
      .filter(el => eligible(el) && !seen.has(el));
    if (!nodes.length) break;
    for (const el of nodes) {
      seen.add(el);
      const label = (el.getAttribute('aria-label') || el.getAttribute('title') || el.textContent || '').trim().slice(0, 100);
      if (el.tagName === 'DETAILS') { el.open = true; undo.push(() => { el.open = false; }); }
      else { el.click(); undo.push(() => { if (el.isConnected && el.getAttribute('aria-expanded') === 'true') el.click(); }); }
      expanded.push(label);
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      rememberPanels();
    }
  }
  // Single-open accordions cannot all stay open through their event handlers.
  // Preserve each actually rendered body as a labelled, inert capture-only copy.
  for (const [button, { anchor, panel }] of panels) {
    if (button.isConnected && button.getAttribute('aria-expanded') === 'false') {
      panel.setAttribute('data-gui-static-disclosure', 'true'); panel.inert = true;
      anchor.after(panel); button.setAttribute('aria-expanded', 'true');
      retainedPanels.push(button.textContent.trim().slice(0, 100));
      undo.push(() => { panel.remove(); button.setAttribute('aria-expanded', 'false'); });
    }
  }
  const remaining = [...root.querySelectorAll('details:not([open]),button[aria-expanded="false"]')].filter(eligible)
    .map(el => (el.getAttribute('aria-label') || el.textContent || '').trim().slice(0, 100));
  const style = document.createElement('style');
  style.textContent = `*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important;caret-color:transparent!important}
    input[type=password],input[autocomplete*=token],input[autocomplete*=password]{-webkit-text-security:disc!important}`;
  document.head.append(style); undo.push(() => style.remove());
  function set(el, key, value) {
    const old = el.style.getPropertyValue(key), priority = el.style.getPropertyPriority(key);
    undo.push(() => old ? el.style.setProperty(key, old, priority) : el.style.removeProperty(key));
    el.style.setProperty(key, value, 'important');
  }
  // Child frames have independent scrolling documents (the laboratory).
  for (const frame of flatten ? root.querySelectorAll('iframe') : []) {
    if (!visible(frame)) continue;
    try {
      if (!frame.contentDocument?.body) throw new Error('Frame not accessible');
      const result = await frame.contentWindow.eval(`(${prepareCapture.toString()})()`);
      frames.push(result);
      undo.push(() => frame.contentWindow.__guiCaptureRestore?.());
      set(frame, 'height', `${Math.max(frame.contentDocument.documentElement.scrollHeight, frame.contentDocument.body.scrollHeight)}px`);
      set(frame, 'min-height', frame.style.height); set(frame, 'flex', 'none');
    } catch { failed.push('Uncaptured iframe (cross-origin or not ready)'); }
  }
  const changed = [];
  for (const el of flatten ? document.querySelectorAll('html,body,body *') : []) {
    if (!visible(el) || el.namespaceURI !== 'http://www.w3.org/1999/xhtml' || ['SCRIPT', 'STYLE', 'INPUT', 'SELECT', 'OPTION', 'IMG', 'IFRAME'].includes(el.tagName)) continue;
    const cs = getComputedStyle(el);
    const clipped = /(auto|scroll|hidden|clip)/.test(cs.overflowY) || (el.tagName === 'TEXTAREA' && el.scrollHeight > el.clientHeight);
    if (clipped) {
      changed.push({ tag: el.tagName, id: el.id, originalHeight: el.clientHeight, contentHeight: el.scrollHeight });
      for (let node = el; node; node = node.parentElement) {
        set(node, 'height', 'auto'); set(node, 'max-height', 'none'); set(node, 'min-height', '0');
        set(node, 'overflow', 'visible'); set(node, 'flex-shrink', '0');
      }
      if (el.tagName === 'TEXTAREA') set(el, 'height', `${el.scrollHeight + 4}px`);
    }
    if (['fixed', 'sticky'].includes(cs.position) && !el.closest('aside,nav') && el.id !== 'gui-capture-label') {
      set(el, 'position', 'relative'); set(el, 'inset', 'auto');
    }
  }
  await document.fonts?.ready;
  await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  const overflow = [...root.querySelectorAll('*')].filter(el => visible(el) && !['INPUT', 'SELECT', 'OPTION'].includes(el.tagName) &&
    /(auto|scroll|hidden|clip)/.test(getComputedStyle(el).overflowY) && el.scrollHeight > el.clientHeight + 3)
    .map(el => ({ tag: el.tagName, id: el.id, missingPixels: el.scrollHeight - el.clientHeight }));
  window.__guiCaptureRestore = () => { for (const fn of undo.reverse()) fn(); delete window.__guiCaptureRestore; };
  return { expanded, retainedPanels, remaining, transformedContainers: changed, uncapturedFrames: failed, frames, overflow,
    width: document.documentElement.scrollWidth, height: document.documentElement.scrollHeight };
}

export function restoreCapture() { window.__guiCaptureRestore?.(); return true; }

export function scrollContainers() {
  let index = 0;
  const results = [];
  function visit(doc, framePath) {
    doc.querySelectorAll('[data-gui-scroll]').forEach(el => el.removeAttribute('data-gui-scroll'));
    const root = [...doc.querySelectorAll('dialog[open],[role="dialog"][aria-modal="true"]')].find(el => el.getClientRects().length) || doc.querySelector('main') || doc.body;
    for (const el of new Set([doc.scrollingElement, ...root.querySelectorAll('*'), root])) {
      if (!el || !el.getClientRects().length || ['INPUT', 'SELECT', 'OPTION', 'IFRAME'].includes(el.tagName)) continue;
      const cs = doc.defaultView.getComputedStyle(el);
      const vertical = (el === doc.scrollingElement || /(auto|scroll)/.test(cs.overflowY)) && el.scrollHeight > el.clientHeight + 3;
      const horizontal = (el === doc.scrollingElement || /(auto|scroll)/.test(cs.overflowX)) && el.scrollWidth > el.clientWidth + 3;
      if (!vertical && !horizontal) continue;
      const id = `gui-scroll-${index++}`;
      el.setAttribute('data-gui-scroll', id);
      results.push({ id, framePath, height: el.clientHeight, total: vertical ? el.scrollHeight : el.clientHeight, original: el.scrollTop,
        width: el.clientWidth, totalWidth: horizontal ? el.scrollWidth : el.clientWidth, originalLeft: el.scrollLeft });
    }
    for (const [i, frame] of [...doc.querySelectorAll('iframe')].entries()) {
      if (root.contains(frame) && frame.getClientRects().length && frame.contentDocument?.body) visit(frame.contentDocument, [...framePath, i]);
    }
  }
  visit(document, []);
  return results;
}

export async function moveScroll(container, top, left) {
  let doc = document;
  for (const index of container.framePath) doc = doc.querySelectorAll('iframe')[index].contentDocument;
  const el = doc.querySelector(`[data-gui-scroll="${container.id}"]`);
  if (!el) throw new Error('Scroll container vanished');
  el.scrollIntoView({ block: 'center', behavior: 'instant' });
  el.scrollTo({ top, left, behavior: 'instant' });
  await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  return { top: el.scrollTop, left: el.scrollLeft };
}
