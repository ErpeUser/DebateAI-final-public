import { useCallback, useEffect, useState } from "react";
import * as api from "../services/api";
import {
  closeOAuthWindow,
  navigateOAuthWindow,
  reserveOAuthWindow,
} from "../lib/oauthWindow";

type LoginFlow = {
  provider: api.SubscriptionProvider;
  state: string;
  authUrl: string;
};

export default function SubscriptionAccountsCard({ onChanged }: { onChanged?: () => void }) {
  const [status, setStatus] = useState<api.SubscriptionAccountsStatus | null>(null);
  const [flow, setFlow] = useState<LoginFlow | null>(null);
  const [busy, setBusy] = useState<api.SubscriptionProvider | "verify" | "">("");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    try {
      setStatus(await api.getSubscriptionAccountsStatus());
    } catch {
      setStatus(null);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    if (!flow) return;
    let stopped = false;
    const timer = window.setInterval(() => {
      void api.pollSubscriptionLogin(flow.provider, flow.state).then((next) => {
        if (stopped) return;
        setStatus(next);
        setMessage(next.message);
        if (next.login_state !== "pending") {
          setBusy("");
          setFlow(null);
          if (next.login_state === "complete") onChanged?.();
        }
      }).catch((error) => {
        if (stopped) return;
        setBusy("");
        setFlow(null);
        setMessage(error instanceof Error ? error.message : "Anmeldung fehlgeschlagen.");
      });
    }, 1000);
    return () => { stopped = true; window.clearInterval(timer); };
  }, [flow, onChanged]);

  const startLogin = async (provider: api.SubscriptionProvider) => {
    const loginWindow = provider === "codex" ? reserveOAuthWindow() : null;
    setBusy(provider);
    setMessage("");
    try {
      const next = await api.startSubscriptionLogin(provider);
      setStatus(next);
      if (!next.auth_url || !next.state) throw new Error("Die Anmeldeseite fehlt.");
      setFlow({ provider, state: next.state, authUrl: next.auth_url });
      const opened = provider !== "codex" || navigateOAuthWindow(loginWindow, next.auth_url);
      setMessage(
        opened
          ? next.message
          : `${next.message} Das Browserfenster wurde blockiert; nutze den Link unten.`,
      );
    } catch (error) {
      closeOAuthWindow(loginWindow);
      setBusy("");
      setMessage(error instanceof Error ? error.message : "Anmeldung fehlgeschlagen.");
    }
  };

  const verifyGemini = async () => {
    setBusy("verify");
    setMessage(`${status?.gemini.model || "Gemini"} wird mit einer kurzen echten High-Anfrage geprüft ...`);
    try {
      const next = await api.verifyGeminiCliHigh();
      setStatus(next);
      setMessage(next.message);
      onChanged?.();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Prüfung fehlgeschlagen.");
    } finally {
      setBusy("");
    }
  };

  if (status && !status.available) return null;

  return (
    <div className="rounded-xl border border-sky-200 bg-surface p-5 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-display text-base font-bold text-brand-dark-gray">Kontozugänge ohne API-Key</h3>
        <span className={`rounded-full px-2 py-0.5 font-body text-[10px] font-medium text-white ${status?.gemini.ready ? "bg-brand-teal" : "bg-sky-600"}`}>
          {status?.gemini.ready ? `${status.gemini.model} bereit` : "OAuth lokal"}
        </span>
      </div>
      <p className="mt-1 font-body text-xs leading-relaxed text-brand-gray">
        Die lokale Bridge speichert Google- und OpenAI-OAuth getrennt in deinem Windows-Profil. Debate AI erhält weder API-Key noch OAuth-Token.
      </p>

      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <div className="rounded-lg border border-sky-100 bg-sky-50/60 p-3">
          <p className="font-body text-sm font-semibold text-brand-dark-gray">Gemini CLI</p>
          <p className="mt-1 font-body text-xs text-brand-gray">
            Google-Anmeldung für das beste tatsächlich verfügbare Gemini-Modell. Tiefenanalysen senden die Denkstufe High.
          </p>
          <button
            type="button"
            onClick={() => void startLogin("gemini-cli")}
            disabled={Boolean(busy) || Boolean(status?.gemini.ready)}
            className="mt-3 rounded bg-sky-700 px-3 py-1.5 font-body text-xs font-medium text-white disabled:opacity-40"
          >
            {busy === "gemini-cli" ? "Anmeldung läuft ..." : status?.gemini.ready ? "Anmeldung gespeichert" : "Mit Google anmelden"}
          </button>
          {status?.gemini.ready && (
            <button
              type="button"
              onClick={() => void verifyGemini()}
              disabled={Boolean(busy)}
              className="ml-2 mt-3 rounded border border-sky-700 px-3 py-1.5 font-body text-xs font-medium text-sky-800 disabled:opacity-40"
              title="Sendet eine kurze echte Modellanfrage über dein Gemini-CLI-Konto."
            >
              {busy === "verify" ? "High wird geprüft ..." : `${status.gemini.model} echt prüfen`}
            </button>
          )}
        </div>

        <div className="rounded-lg border border-sky-100 bg-sky-50/60 p-3">
          <p className="font-body text-sm font-semibold text-brand-dark-gray">OpenAI / Codex</p>
          <p className="mt-1 font-body text-xs text-brand-gray">
            Melde deinen neuen OpenAI-Account über den ChatGPT-Plan-OAuth an. Vorhandene Konten werden dabei nicht ungefragt gelöscht.
          </p>
          <button
            type="button"
            onClick={() => void startLogin("codex")}
            disabled={Boolean(busy) || Boolean(status?.openai.ready)}
            className="mt-3 rounded bg-sky-700 px-3 py-1.5 font-body text-xs font-medium text-white disabled:opacity-40"
          >
            {busy === "codex" ? "Anmeldung läuft ..." : status?.openai.ready ? "Anmeldung gespeichert" : "Neuen OpenAI-Account anmelden"}
          </button>
        </div>
      </div>

      {flow && (
        <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3">
          <p className="font-body text-xs text-amber-900">Die lokale OAuth-Sitzung wartet. Öffne jetzt die Anmeldeseite:</p>
          <a
            href={flow.authUrl}
            target="_blank"
            rel="noreferrer"
            className="mt-2 inline-block rounded bg-amber-600 px-3 py-1.5 font-body text-xs font-medium text-white"
          >
            Sichere Anmeldeseite öffnen
          </a>
        </div>
      )}

      <p className={`mt-3 font-body text-xs ${status?.login_state === "error" ? "text-red-600" : "text-brand-teal"}`}>
        {message || status?.message}
      </p>
      {status?.gemini.ready && (
        <p className="mt-1 font-body text-[11px] text-brand-gray">
          Route: <span className="font-mono">endpoint:subscription-ai:{status.gemini.model}</span> · Denkstufe {status.gemini.thinking}
        </p>
      )}
    </div>
  );
}
