// Browser-only fixtures. Never writes sessions, settings, recordings or tokens.
(() => {
  const nativeFetch = window.fetch.bind(window);
  const base = { created_at: '2026-11-14T09:00:00Z', started_at: null, ended_at: null, notes: null,
    meeting_type: 'debate_persuasive', meeting_context: 'Visuelle Kontrolle mit Beispieldaten. Keine echte Aufnahme.',
    group_id: null, speaker_context_dirty: false, speaker_context_enhanced_at: null };
  const sessions = [
    { ...base, id: 'gui-pre', name: 'GUI – Vorbereitung', state: 'pre_call' },
    { ...base, id: 'gui-active', name: 'GUI – Aktive Ansicht (pausiert)', state: 'active', started_at: base.created_at },
    { ...base, id: 'gui-completed', name: 'GUI – Abgeschlossene Debatte', state: 'completed', started_at: base.created_at, ended_at: '2026-11-14T09:05:00Z' },
    { ...base, id: 'gui-forceful', name: 'GUI – Brutal-sachlich (pausiert)', meeting_type: 'debate_forceful', state: 'active', started_at: base.created_at },
  ];
  const json = value => new Response(JSON.stringify(value), { status: 200, headers: { 'Content-Type': 'application/json' } });
  window.__guiCaptureEvidence = { fixture: true, blockedWrites: 0 };
  window.fetch = async (input, options = {}) => {
    const url = new URL(typeof input === 'string' ? input : input.url || input, location.href);
    const method = (options.method || input.method || 'GET').toUpperCase();
    if (url.origin !== location.origin) throw new Error('External requests disabled during GUI capture');
    if (url.pathname === '/api/sessions' && method === 'POST') {
      const body = JSON.parse(options.body || '{}');
      const session = { ...base, id: 'gui-created', name: body.name || 'GUI – Neu erstellt', meeting_type: body.meeting_type || base.meeting_type, state: 'pre_call' };
      sessions.push(session); return json(session);
    }
    if (url.pathname.startsWith('/api/') && !['GET', 'HEAD'].includes(method)) {
      window.__guiCaptureEvidence.blockedWrites++;
      return new Response(JSON.stringify({ detail: 'Visual capture is read-only' }), { status: 403, headers: { 'Content-Type': 'application/json' } });
    }
    if (url.pathname === '/api/sessions') return json(sessions);
    if (url.pathname === '/api/session-groups' || url.pathname === '/api/groups') return json([]);
    if (url.pathname.startsWith('/api/sessions/gui-')) {
      const [, , , id, resource] = url.pathname.split('/');
      if (!resource) return json(sessions.find(item => item.id === id));
      if (resource === 'dossier') return json({ source_id: '', entries: [] });
      if (resource === 'transcripts') return json(Array.from({ length: ['gui-pre', 'gui-created'].includes(id) ? 0 : 24 }, (_, i) => ({
        id: `tx-${i}`, session_id: id, sequence: i + 1, timestamp: `2026-11-14T09:0${i % 5}:00Z`, speaker_id: 'speaker-1',
        text: `Beispiel ${i + 1}: Ich stimme nicht zu. Welche Quelle belegt die Zahl von 23,5 Prozent? Eine Behauptung ist noch kein Beweis.`,
      })));
      if (resource === 'speakers') return json([{ id: 'speaker-1', session_id: id, name: 'Beispielperson', role: 'Diskussion', color: '#729b65', is_user: false, speaker_type: 'external', display_name: 'Beispielperson', display_name_enabled: true, created_at: base.created_at }]);
      if (resource === 'questions') return json(Array.from({ length: 8 }, (_, i) => ({ id: `q-${i}`, session_id: id,
        item_type: i % 2 ? 'objection' : 'question', question: `Beispielargument ${i + 1}: Welche unabhängigen Belege stützen diese Aussage?`,
        rationale: 'Korrelation ist nicht automatisch Kausalität. Alternative Erklärungen müssen geprüft werden.',
        source_context: 'Die Zahl allein erklärt weder Ursache noch Vergleichsmaßstab.', directive_id: null, starred: false,
        dismissed: false, answered: false, answer_summary: '', needs_followup: false, followup_question: '', created_at: base.created_at })));
      if (resource === 'synthesis') return json(null);
      if (resource === 'token-usage') return json({ input_tokens: 0, output_tokens: 0, thinking_tokens: 0, total_tokens: 0, audio_seconds: 0, by_source: [], by_model: [] });
      if (resource === 'argument-graph') return json({ nodes: [], edges: [], claims: [], relations: [] });
      if (resource === 'debate-review' || resource === 'pii-summary' || resource === 'enhance-insights') return json(null);
      return json([]);
    }
    return nativeFetch(input, options);
  };
  // No socket connection, microphone request or native bridge in a fixture run.
  window.WebSocket = class extends EventTarget { static CLOSED = 3; readyState = 3; close() {} send() {} };
  if (navigator.mediaDevices) navigator.mediaDevices.getUserMedia = async () => { throw new Error('Microphone disabled for visual capture'); };
  document.addEventListener('DOMContentLoaded', () => {
    const tag = document.createElement('div'); tag.textContent = 'GUI-KONTROLLE · BEISPIELDATEN · KEIN LIVE-/HARDWARETEST';
    tag.style.cssText = 'position:fixed;bottom:0;left:0;z-index:2147483647;background:#18202f;color:#fff;font:11px monospace;padding:4px 8px;pointer-events:none';
    tag.id = 'gui-capture-label'; document.body.append(tag);
  });
})();
