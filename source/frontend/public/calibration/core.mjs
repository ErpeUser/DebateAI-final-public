export function formatPercent(value) {
  return typeof value === 'number' && Number.isFinite(value) ? `${(100 * value).toFixed(1)} %` : '\u2014';
}

export function validateBlindCase(value) {
  if (!value || typeof value.case_id !== 'string' || !value.case_id.trim() || value.case_id.length > 200 ||
      !['hart', 'ueberzeugen'].includes(value.mode) || !Array.isArray(value.candidates) || value.candidates.length !== 2) {
    throw new Error('Erwartet: case_id, mode (hart/ueberzeugen) und genau zwei candidates.');
  }
  if (value.context !== undefined && (typeof value.context !== 'string' || value.context.length > 12000)) {
    throw new Error('Kontext muss Text mit hoechstens 12000 Zeichen sein.');
  }
  if (value.context_sha256 != null && (typeof value.context_sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(value.context_sha256))) {
    throw new Error('Ungueltige Kontext-Pruefsumme.');
  }
  if (value.prompt_version != null && (typeof value.prompt_version !== 'string' || value.prompt_version.length > 200)) {
    throw new Error('Ungueltige Promptversion.');
  }
  for (const c of value.candidates) {
    if (c?.context_sha256 != null && c.context_sha256 !== value.context_sha256) {
      throw new Error('Die Kandidaten stammen nicht aus demselben Kontext.');
    }
    if (!c || typeof c.id !== 'string' || !c.id.trim() || c.id.length > 200 ||
        typeof c.text !== 'string' || !c.text.trim() || c.text.length > 4000) {
      throw new Error('Jeder Kandidat braucht eine eindeutige ID und 1 bis 4000 Zeichen Antworttext.');
    }
  }
  if (value.candidates[0].id === value.candidates[1].id) throw new Error('Kandidaten-IDs muessen verschieden sein.');
  return value;
}

export function createBlindTrial(value, randomByte = () => crypto.getRandomValues(new Uint8Array(1))[0]) {
  validateBlindCase(value);
  const order = randomByte() % 2 ? [1, 0] : [0, 1];
  const candidates = order.map(i => ({...value.candidates[i]}));
  return {
    caseId: value.case_id, mode: value.mode, context: value.context ?? '', contextHash: value.context_sha256 ?? null,
    promptVersion: value.prompt_version ?? null,
    cards: candidates.map((c, i) => ({label: i === 0 ? 'A' : 'B', text: c.text})),
    identities: candidates, voted: false,
  };
}

export function recordVote(trial, choice, ratings) {
  if (trial.voted) throw new Error('Dieser Durchgang ist bereits bewertet.');
  if (!['A', 'B', 'tie', 'both_bad'].includes(choice)) throw new Error('Ungueltige Bewertung.');
  const clean = {};
  for (const key of ['speakability', 'relevance']) {
    if (ratings[key] !== undefined) {
      if (!Number.isInteger(ratings[key]) || ratings[key] < 1 || ratings[key] > 5) throw new Error('Bewertung muss 1 bis 5 sein.');
      clean[key] = ratings[key];
    }
  }
  trial.voted = true;
  return {
    case_id: trial.caseId, mode: trial.mode, context_sha256: trial.contextHash,
    prompt_version: trial.promptVersion, choice, ratings: clean,
    winner_id: ['A', 'B'].includes(choice) ? trial.identities[choice === 'A' ? 0 : 1].id : null,
    presentation_order: trial.identities.map(c => c.id),
    feedback_kind: 'usefulness', factual_status: 'unverified', created_at: new Date().toISOString(),
  };
}

export class Recorder {
  constructor({mediaDevices = globalThis.navigator?.mediaDevices, MediaRecorderClass = globalThis.MediaRecorder,
               onClip = () => {}, onError = () => {}, onIdle = () => {}, maxMs = 30000} = {}) {
    Object.assign(this, {mediaDevices, MediaRecorderClass, onClip, onError, onIdle, maxMs});
    this.state = 'idle'; this.generation = 0; this.stream = null; this.recorder = null; this.timer = null;
  }
  async start(deviceId = '') {
    if (this.state !== 'idle') throw new Error('Aufnahme laeuft bereits.');
    if (!this.mediaDevices?.getUserMedia || !this.MediaRecorderClass) throw new Error('Mikrofonaufnahme wird hier nicht unterstuetzt. Audiodatei verwenden.');
    this.state = 'requesting'; const generation = ++this.generation;
    let stream;
    try {
      stream = await this.mediaDevices.getUserMedia({audio: deviceId ? {deviceId:{exact:deviceId}} : true});
      if (generation !== this.generation) { stream.getTracks().forEach(t => t.stop()); return; }
      this.stream = stream;
      const types = ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/webm'];
      const mimeType = types.find(t => this.MediaRecorderClass.isTypeSupported?.(t));
      const recorder = new this.MediaRecorderClass(stream, mimeType ? {mimeType} : undefined);
      this.recorder = recorder;
      const chunks = []; let size = 0; let invalid = false;
      recorder.ondataavailable = event => {
        if (!event.data?.size || invalid) return;
        size += event.data.size;
        if (size > 16 * 1024 * 1024) {
          invalid = true; this.cancel(); this.onError(new Error('Aufnahme ueberschreitet 16 MiB.')); return;
        }
        chunks.push(event.data);
      };
      recorder.onerror = () => { invalid = true; this.cancel(); this.onError(new Error('Audioaufnahme fehlgeschlagen.')); };
      recorder.onstop = () => {
        stream.getTracks().forEach(t => t.stop());
        if (generation !== this.generation) return;
        clearTimeout(this.timer); this.timer = null; this.stream = null; this.recorder = null; this.state = 'idle';
        if (!invalid && chunks.length) this.onClip(new Blob(chunks, {type: recorder.mimeType || mimeType || 'audio/webm'}));
        this.onIdle();
      };
      recorder.start(200); this.state = 'recording';
      this.timer = setTimeout(() => this.stop(), this.maxMs);
    } catch (error) {
      stream?.getTracks().forEach(t => t.stop());
      if (generation === this.generation) { this.state = 'idle'; this.stream = null; this.recorder = null; }
      throw error;
    }
  }
  stop() {
    clearTimeout(this.timer); this.timer = null;
    if (this.recorder?.state === 'recording') { this.state = 'stopping'; this.recorder.stop(); }
    else if (this.state === 'requesting') this.cancel();
  }
  cancel() {
    ++this.generation; clearTimeout(this.timer); this.timer = null;
    if (this.recorder?.state === 'recording') this.recorder.stop();
    this.stream?.getTracks().forEach(t => t.stop());
    this.stream = null; this.recorder = null; this.state = 'idle';
    this.onIdle();
  }
}

export function validateBlindSuite(value) {
  const cases = Array.isArray(value?.cases) ? value.cases : [value];
  if (value?.cases !== undefined && value.schema_version !== 1) throw new Error('Unbekannte Vergleichsversion.');
  if (cases.length < 1 || cases.length > 100) throw new Error('Ein Vergleichspaket braucht 1 bis 100 Faelle.');
  const seen = new Set();
  for (const item of cases) {
    validateBlindCase(item);
    const key = JSON.stringify([item.case_id, item.mode]);
    if (seen.has(key)) throw new Error('Doppelter Fall im selben Modus.');
    seen.add(key);
  }
  return cases;
}
