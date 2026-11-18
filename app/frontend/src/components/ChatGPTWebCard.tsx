import { useCallback, useEffect, useState } from "react";
import * as api from "../services/api";
import { useConfirm } from "./ConfirmProvider";

export default function ChatGPTWebCard({ onChanged }: { onChanged?: () => void }) {
  const { confirm } = useConfirm();
  const [status, setStatus] = useState<api.ChatGPTWebStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    try { setStatus(await api.getChatGPTWebStatus()); } catch { setStatus(null); }
  }, []);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (status?.login_state !== "pending") return;
    const controller = new AbortController();
    let timer: number | undefined;
    const poll = async () => {
      try {
        const next = await api.pollChatGPTWebLogin(controller.signal);
        if (controller.signal.aborted) return;
        setStatus(next);
        setMessage(next.message);
        if (next.login_state !== "pending") {
          setBusy(false);
          if (next.ready) onChanged?.();
          return;
        }
        timer = window.setTimeout(() => void poll(), 1000);
      } catch (error) {
        if (controller.signal.aborted) return;
        const message = error instanceof Error ? error.message : "Anmeldung fehlgeschlagen.";
        setStatus((current) => current ? { ...current, login_state: "error", message } : current);
        setBusy(false);
        setMessage(message);
      }
    };
    timer = window.setTimeout(() => void poll(), 1000);
    return () => {
      controller.abort();
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [onChanged, status?.login_state]);

  const startLogin = async () => {
    setBusy(true);
    setMessage("");
    try {
      const next = await api.startChatGPTWebLogin();
      setStatus(next);
      setMessage(next.message);
    } catch (error) {
      setBusy(false);
      setMessage(error instanceof Error ? error.message : "Anmeldung fehlgeschlagen.");
    }
  };

  const refresh = async () => {
    setBusy(true);
    try {
      const next = await api.getChatGPTWebStatus();
      setStatus(next);
      setMessage(next.message);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Status konnte nicht aktualisiert werden.");
    } finally {
      setBusy(false);
    }
  };

  const disconnect = async () => {
    const ok = await confirm({
      title: "ChatGPT-Verbindung trennen",
      message: "Nur der bestätigte Debate-AI-Zugang wird getrennt. Das dedizierte lokale Sitzungsprofil bleibt für eine erneute Anmeldung erhalten.",
      confirmLabel: "Verbindung trennen",
      tone: "danger",
    });
    if (!ok) return;
    setBusy(true);
    try {
      const next = await api.disconnectChatGPTWeb();
      setStatus(next);
      setMessage(next.message);
      onChanged?.();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Trennen fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  };

  const switchAccount = async () => {
    const ok = await confirm({
      title: "ChatGPT-Konto wechseln",
      message: "Das ausschließlich von Debate AI verwendete ChatGPT-Profil wird wiederherstellbar archiviert. Dein normales Browserprofil bleibt unberührt; danach öffnet sich die Anmeldung für das neue Konto.",
      confirmLabel: "Konto wechseln",
      tone: "danger",
    });
    if (!ok) return;
    setBusy(true);
    try {
      const next = await api.switchChatGPTWebAccount();
      setStatus(next);
      setMessage(next.message);
    } catch (error) {
      setBusy(false);
      setMessage(error instanceof Error ? error.message : "Kontowechsel fehlgeschlagen.");
    }
  };

  if (status && !status.available) return null;
  const badge = status?.ready ? "GPT-6 Extra High bestätigt" : "Nicht angemeldet";
  return (
    <div className="rounded-xl border border-violet-200 bg-surface p-5 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-display text-base font-bold text-brand-dark-gray">ChatGPT Web über normalen Zugang</h3>
        <span className={`rounded-full px-2 py-0.5 font-body text-[10px] font-medium text-white ${status?.ready ? "bg-brand-teal" : "bg-violet-500"}`}>
          {badge}
        </span>
      </div>
      <p className="mt-1 font-body text-xs leading-relaxed text-brand-gray">
        Nutzt dein normales ChatGPT-Konto in einem eigenen lokalen Chrome-Profil. Dieser Zugang ist vollständig vom Codex-OAuth-Zugang getrennt.
      </p>
      <p className="mt-2 rounded-lg bg-violet-50 px-3 py-2 font-body text-xs text-violet-900">
        Inoffizielle Browser-Automatisierung: OpenAI kann die Oberfläche ändern oder den Zugriff einschränken. Es werden keine Cookies in Debate AI kopiert oder protokolliert.
      </p>
      {status?.ready && (
        <p className="mt-2 font-body text-xs text-brand-gray">
          Nachweis: {status.model} · Denkstufe {status.thinking} · {status.verification}
          {status.latency_ms ? ` · ${status.latency_ms} ms` : ""}
        </p>
      )}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {status?.login_available && (
          <button
            type="button"
            onClick={startLogin}
            disabled={busy || status.login_state === "pending"}
            className="rounded bg-violet-600 px-3 py-1.5 font-body text-xs font-medium text-white disabled:opacity-40"
          >
            {status.login_state === "pending" ? "Anmeldung und Prüfung laufen ..." : status.ready ? "Verbindung testen" : "Mit ChatGPT anmelden"}
          </button>
        )}
        {status?.ready && status.login_available && (
          <button type="button" onClick={startLogin} disabled={busy} className="rounded px-2 py-1.5 font-body text-xs text-brand-mid-gray disabled:opacity-40">
            Erneut anmelden
          </button>
        )}
        <button type="button" onClick={refresh} disabled={busy} className="rounded px-2 py-1.5 font-body text-xs text-brand-mid-gray disabled:opacity-40">
          Status aktualisieren
        </button>
        {status?.ready && (
          <button type="button" onClick={disconnect} disabled={busy} className="rounded px-2 py-1.5 font-body text-xs text-brand-mid-gray hover:text-red-600 disabled:opacity-40">
            Verbindung trennen
          </button>
        )}
        {status?.login_available && (
          <button type="button" onClick={switchAccount} disabled={busy} className="rounded px-2 py-1.5 font-body text-xs text-brand-mid-gray hover:text-red-600 disabled:opacity-40">
            Konto wechseln
          </button>
        )}
      </div>
      <p className={`mt-2 font-body text-xs ${status?.login_state === "error" ? "text-red-600" : "text-brand-teal"}`}>
        {message || status?.message}
      </p>
    </div>
  );
}
