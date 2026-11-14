import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { AgentBrowser, prepareCapture, restoreCapture, scrollContainers, moveScroll, waitForContent, validateCaptureUrl } from './capture.mjs';

test('expands nested content, ignores hidden tabs/menus, exposes bottom, restores layout', async () => {
  const html = `<main style="height:200px;overflow:auto"><button aria-expanded="false" aria-controls="outer" onclick="const opening=this.getAttribute('aria-expanded')==='false';this.setAttribute('aria-expanded',String(opening));document.querySelector('#outer').hidden=!opening">Outer</button>
    <div id="outer" hidden><details><summary>Nested</summary><p id="bottom" style="margin-top:1800px">BOTTOM MARKER</p></details></div>
    <button aria-expanded="false" aria-haspopup="menu" onclick="window.unsafe=true">Delete menu</button>
    <div hidden><button aria-expanded="false" onclick="window.unsafe=true">Hidden tab</button></div>
    <button onclick="window.unsafe=true">Start microphone</button></main>`;
  const browser = new AgentBrowser(`capture-test-${process.pid}`);
  try {
    browser.run('open', `data:text/html;charset=utf-8,${encodeURIComponent(html)}`);
    const report = browser.evaluate(prepareCapture);
    assert.equal(report.remaining.length, 0);
    assert.equal(report.expanded.length, 2);
    assert.equal(browser.evaluate(() => !!window.unsafe), false);
    assert.ok(browser.evaluate(() => document.documentElement.scrollHeight) > 1800);
    assert.equal(browser.evaluate(() => document.querySelector('#bottom').getClientRects().length > 0), true);
    assert.equal(browser.evaluate(() => document.querySelector('main').scrollHeight > document.querySelector('main').clientHeight + 2), false);
    browser.evaluate(restoreCapture);
    assert.equal(browser.evaluate(() => document.querySelector('main').style.height), '200px');
    assert.equal(browser.evaluate(() => document.querySelector('#outer').hidden), true);
  } finally {
    browser.run('close');
  }
});

test('fixture guard creates only in browser memory and blocks real API writes', async () => {
  let forwarded = 0;
  const window = { fetch: async () => { forwarded++; return new Response('{}'); } };
  runInNewContext(readFileSync(new URL('./fixtures.js', import.meta.url), 'utf8'), {
    window, location: { href: 'http://127.0.0.1:8474/', origin: 'http://127.0.0.1:8474' },
    document: { addEventListener() {} }, navigator: { mediaDevices: {} }, URL, Response, EventTarget,
  });
  const created = await (await window.fetch('/api/sessions', { method: 'POST', body: JSON.stringify({ name: 'Test' }) })).json();
  assert.equal(created.id, 'gui-created');
  assert.equal((await window.fetch('/api/settings', { method: 'PUT', body: '{}' })).status, 403);
  assert.equal((await window.fetch('/api/sessions/real-user-session', { method: 'DELETE' })).status, 403);
  assert.equal(forwarded, 0);
  await window.fetch('/api/meta');
  assert.equal(forwarded, 1);
  assert.equal(window.__guiCaptureEvidence.blockedWrites, 2);
});

test('captures horizontal scrolling and independent same-origin iframe scrolling', () => {
  const html = `<main><div style="width:180px;height:100px;overflow:auto"><p style="width:900px;height:700px">WIDE CONTENT</p></div>
    <iframe srcdoc="<p style='height:1900px'>FRAME BOTTOM</p>" style="height:200px"></iframe></main>`;
  const browser = new AgentBrowser(`capture-frame-${process.pid}`);
  try {
    browser.run('open', `data:text/html;charset=utf-8,${encodeURIComponent(html)}`);
    browser.run('wait', '--fn', '!!document.querySelector("iframe").contentDocument?.querySelector("p")');
    const containers = browser.evaluate(scrollContainers);
    const wide = containers.find(x => x.totalWidth > x.width);
    const frame = containers.find(x => x.framePath.length > 0);
    assert.ok(wide); assert.ok(frame);
    assert.equal(browser.evaluate(moveScroll, wide, 100, 200).left, 200);
    assert.ok(browser.evaluate(moveScroll, frame, 400, 0).top >= 400);
    const report = browser.evaluate(prepareCapture);
    assert.equal(report.frames.length, 1);
    assert.equal(report.uncapturedFrames.length, 0);
    browser.evaluate(restoreCapture);
  } finally { browser.run('close'); }
});

test('scroll identities cannot collide with a previous surface or hidden panel', () => {
  const html = `<main style="height:200px;overflow:auto"><p style="height:800px">CONTENT</p><div id="next"></div></main>`;
  const browser = new AgentBrowser(`capture-scroll-${process.pid}`);
  try {
    browser.run('open', `data:text/html;charset=utf-8,${encodeURIComponent(html)}`);
    browser.evaluate(scrollContainers);
    browser.evaluate(() => { document.querySelector('main').style.height = 'auto'; document.querySelector('main').style.overflow = 'visible';
      document.querySelector('#next').innerHTML = '<div style="height:100px;overflow:auto"><p style="height:900px">NEXT</p></div>'; return true; });
    const next = browser.evaluate(scrollContainers);
    assert.ok(next.length > 0);
    assert.equal(browser.evaluate(() => document.querySelectorAll('[data-gui-scroll="gui-scroll-0"]').length), 1);
  } finally { browser.run('close'); }
});

test('retains mutually exclusive disclosure content in explicitly transformed capture', () => {
  const html = `<main><section><button aria-expanded="true" onclick="toggle(this)">First</button><div>FIRST CONTENT</div></section>
    <section><button aria-expanded="false" onclick="toggle(this)">Second</button></section></main>
    <script>function toggle(button){document.querySelectorAll('section div').forEach(x=>x.remove());document.querySelectorAll('button').forEach(x=>x.setAttribute('aria-expanded','false'));button.setAttribute('aria-expanded','true');button.insertAdjacentHTML('afterend','<div>SECOND CONTENT</div>')}</script>`;
  const browser = new AgentBrowser(`capture-exclusive-${process.pid}`);
  try {
    browser.run('open', `data:text/html;charset=utf-8,${encodeURIComponent(html)}`);
    const report = browser.evaluate(prepareCapture);
    assert.equal(report.remaining.length, 0);
    assert.ok(browser.evaluate(() => document.body.innerText).includes('FIRST CONTENT'));
    assert.ok(browser.evaluate(() => document.body.innerText).includes('SECOND CONTENT'));
  } finally { browser.run('close'); }
});

test('waits for independently loading content and rejects persistent placeholders', () => {
  const browser = new AgentBrowser(`capture-ready-${process.pid}`);
  try {
    browser.run('open', 'data:text/html,<main>Settings</main>');
    browser.evaluate(() => { document.querySelector('main').innerHTML = '<p>Einstellungen werden geladen...</p>';
      setTimeout(() => { document.querySelector('main').innerHTML = '<h2>CONTENT READY</h2>'; }, 1200); return true; });
    const report = browser.evaluate(waitForContent, { timeout: 3000 });
    assert.ok(report.waitedMs >= 600);
    assert.ok(browser.evaluate(() => document.body.innerText).includes('CONTENT READY'));
    browser.evaluate(() => { document.querySelector('main').innerHTML = '<p>Wird geprüft ...</p>'; return true; });
    // Catch inside Chromium: the CLI intentionally normalizes timeout errors.
    const failure = browser.evaluate(async source => {
      try { await (0, eval)(`(${source})`)({ timeout: 150 }); return ''; }
      catch (error) { return error.message; }
    }, waitForContent.toString());
    assert.match(failure, /Content not ready/);
  } finally { browser.run('close'); }
});

test('rejects credential-bearing or remote URLs before recording or launching', () => {
  assert.equal(validateCaptureUrl('http://localhost:8474/?desktop=1'), 'http://localhost:8474/?desktop=1');
  for (const url of ['http://user:secret@localhost:8474/', 'http://localhost:8474/?token=secret',
    'http://localhost:8474/#secret', 'https://example.com/', 'http://localhost:8474/?unknown=secret']) {
    assert.throws(() => validateCaptureUrl(url));
  }
});
