import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createDesktopSession } from '../public/calibration/session.mjs';

test('concurrent lab requests authenticate before loading catalog or posting audio', async () => {
  const calls = [];
  const session = createDesktopSession(async (url, options) => {
    calls.push({url, options});
    return new Response('{}', {headers: url === '/api/meta'
      ? {'X-DebateAI-Instance':'instance-test'} : {}});
  });
  const body = new FormData();
  body.append('reference', 'Test');
  await Promise.all([
    session.fetch('/api/calibration/catalog'),
    session.fetch('/api/calibration/asr', {method:'POST', body}),
  ]);
  assert.equal(calls.filter(c=>c.url === '/api/meta').length, 1);
  assert.equal(calls[0].url, '/api/meta');
  assert.equal(calls[1].options.headers.get('X-DebateAI-Instance'), 'instance-test');
  assert.equal(calls[2].options.headers.get('X-DebateAI-Instance'), 'instance-test');
  assert.equal(calls[2].options.body, body);
  assert.equal(calls[2].options.headers.has('Content-Type'), false);
});

test('a failed bootstrap prevents mutations and permits a later retry', async () => {
  const calls = [];
  const session = createDesktopSession(async url => {
    calls.push(url);
    return new Response('{}', {status: calls.length === 1 ? 503 : 200});
  });
  await assert.rejects(session.fetch('/api/calibration/asr', {method:'POST'}));
  assert.deepEqual(calls, ['/api/meta']);
  await session.fetch('/api/calibration/catalog');
  assert.deepEqual(calls, ['/api/meta', '/api/meta', '/api/calibration/catalog']);
});

test('identical repeated instance headers remain one token on later requests', async () => {
  const calls = [];
  const session = createDesktopSession(async (url, options) => {
    calls.push({url, options});
    const headers = new Headers();
    headers.append('X-DebateAI-Instance', 'instance-test');
    headers.append('X-DebateAI-Instance', 'instance-test');
    return new Response('{}', {headers});
  });
  await session.fetch('/api/calibration/catalog');
  await session.fetch('/api/sessions');
  assert.equal(calls[1].options.headers.get('X-DebateAI-Instance'), 'instance-test');
  assert.equal(calls[2].options.headers.get('X-DebateAI-Instance'), 'instance-test');
  assert.equal(session.getToken(), 'instance-test');
});

test('conflicting bootstrap instance headers block the protected request', async () => {
  const calls = [];
  const session = createDesktopSession(async url => {
    calls.push(url);
    return new Response('{}', {headers: {'X-DebateAI-Instance': 'instance-a, instance-b'}});
  });
  await assert.rejects(session.fetch('/api/calibration/asr', {method:'POST'}));
  assert.deepEqual(calls, ['/api/meta']);
  assert.equal(session.getToken(), '');
});
