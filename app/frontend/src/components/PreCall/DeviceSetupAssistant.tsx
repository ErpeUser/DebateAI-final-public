import { useEffect, useMemo, useState } from "react";
import * as api from "../../services/api";
import type { ModelInfo } from "../../types";

export default function DeviceSetupAssistant() {
  const [devices, setDevices] = useState<api.NativeAudioDevice[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [readiness, setReadiness] = useState<api.TranscriptionReadiness | null>(null);
  const stored = (() => {
    try { return JSON.parse(window.localStorage.getItem("debateai:audio-devices") || "{}"); }
    catch { return {}; }
  })();
  const [microphone, setMicrophone] = useState<string>(stored.microphone_id || "");
  const [loopback, setLoopback] = useState<string>(stored.loopback_id || "");
  const [level, setLevel] = useState(0);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    void Promise.all([
      api.getNativeAudioDevices().then((value) => setDevices(value.devices)).catch(() => setDevices([])),
      api.getTranscriptionReadiness().then(setReadiness).catch(() => setReadiness(null)),
      api.listModels().then(setModels).catch(() => setModels([])),
    ]);
  }, []);

  const microphones = useMemo(() => devices.filter((device) => !device.loopback), [devices]);
  const loopbacks = useMemo(() => devices.filter((device) => device.loopback), [devices]);
  const localCoachReady = models.some((model) => model.runs_locally && model.supports_text && model.key_available);

  const persist = (nextMicrophone = microphone, nextLoopback = loopback) => {
    window.localStorage.setItem("debateai:audio-devices", JSON.stringify({
      microphone_mode: nextMicrophone ? "fixed" : "follow_default",
      loopback_mode: nextLoopback ? "fixed" : "follow_default",
      ...(nextMicrophone ? { microphone_id: nextMicrophone } : {}),
      ...(nextLoopback ? { loopback_id: nextLoopback } : {}),
    }));
  };

  const test = async () => {
    const selected = microphones.find((device) => device.endpoint_id === microphone)?.index ?? microphones.find((device) => device.is_default)?.index;
    if (selected === undefined) return;
    setTesting(true);
    try {
      const result = await api.probeNativeMicrophone(selected);
      setLevel(result.level);
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <label className="font-body text-xs font-semibold text-brand-dark-gray">
        Mikrofon
        <select value={microphone} onChange={(event) => { const value = event.target.value; setMicrophone(value); persist(value, loopback); }} className="mt-1 block w-full rounded border border-brand-light-gray-1 bg-surface px-3 py-2 font-normal">
          <option value="">Windows-Standard folgen</option>
          {microphones.map((device) => <option key={device.endpoint_id} value={device.endpoint_id}>{device.name}</option>)}
        </select>
      </label>
      <label className="font-body text-xs font-semibold text-brand-dark-gray">
        Wiedergabemix (WASAPI-Loopback)
        <select value={loopback} onChange={(event) => { const value = event.target.value; setLoopback(value); persist(microphone, value); }} className="mt-1 block w-full rounded border border-brand-light-gray-1 bg-surface px-3 py-2 font-normal">
          <option value="">Windows-Standard folgen</option>
          {loopbacks.map((device) => <option key={device.endpoint_id} value={device.endpoint_id}>{device.name}</option>)}
        </select>
      </label>
      <div className="md:col-span-2 flex items-center gap-3">
        <button type="button" disabled={testing || microphones.length === 0} onClick={() => void test()} className="rounded border border-brand-teal px-3 py-1.5 font-body text-xs font-semibold text-brand-teal disabled:opacity-50">
          {testing ? "Pegel wird geprüft…" : "Mikrofonpegel prüfen"}
        </button>
        <div aria-label="Mikrofonpegel" className="h-2 flex-1 overflow-hidden rounded bg-brand-light-gray-1">
          <div className="h-full bg-brand-teal transition-[width]" style={{ width: `${Math.max(2, level * 100)}%` }} />
        </div>
      </div>
      <p className="md:col-span-2 rounded border border-amber-200 bg-amber-50 px-3 py-2 font-body text-xs leading-5 text-amber-900">
        WASAPI-Loopback erfasst den gesamten Mix des gewählten Windows-Ausgabegeräts. Das ist nicht automatisch nur Discord oder WhatsApp; auch andere dort hörbare Programme können enthalten sein.
      </p>
      <div className="md:col-span-2 grid gap-2 sm:grid-cols-2">
        <p className={`rounded px-3 py-2 font-body text-xs ${readiness?.ready ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-900"}`}>
          Transkription: {readiness?.ready ? "lokal bereit" : readiness?.reason || "wird geprüft"}
        </p>
        <p className={`rounded px-3 py-2 font-body text-xs ${localCoachReady ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-900"}`}>
          Lokaler Debattencoach: {localCoachReady ? "bereit" : "lokales Textmodell prüfen"}
        </p>
      </div>
    </div>
  );
}
