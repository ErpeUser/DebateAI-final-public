import { useCallback, useEffect, useState } from "react";
import * as api from "../services/api";
import { useConfirm } from "./ConfirmProvider";

export default function GeminiWebBridgeCard({
  onChanged,
}: {
  onChanged?: () => void;
}) {
  const { confirm } = useConfirm();
  const [status, setStatus] = useState<api.GeminiWebStatus | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    try {
      setStatus(await api.getGeminiWebStatus());
    } catch {
      setStatus(null);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (status?.login_state !== "pending") return;
    let stopped = false;
    const timer = window.setInterval(() => {
      void api
        .pollGeminiWebLogin()
        .then((next) => {
          if (stopped) return;
          setStatus(next);
          setMessage(next.message);
          if (next.login_state !== "pending") {
            setBusy(false);
            onChanged?.();
          }
        })
        .catch((error) => {
          if (stopped) return;
          setBusy(false);
          setMessage(
            error instanceof Error
              ? error.message
              : "Anmeldung fehlgeschlagen.",
          );
        });
    }, 1000);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [onChanged, status?.login_state]);

  const startLogin = async () => {
    setBusy(true);
    setMessage("");
    try {
      const next = await api.startGeminiWebLogin();
      setStatus(next);
      setMessage(next.message);
    } catch (error) {
      setBusy(false);
      setMessage(
        error instanceof Error ? error.message : "Anmeldung fehlgeschlagen.",
      );
    }
  };

  const importCookie = async () => {
    if (!file) return;
    setBusy(true);
    setMessage("");
    try {
      const next = await api.importGeminiWebCookie(file);
      setStatus(next);
      setFile(null);
      setMessage(next.message);
      onChanged?.();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Import fehlgeschlagen.",
      );
    } finally {
      setBusy(false);
    }
  };

  const removeCookie = async () => {
    const ok = await confirm({
      title: "Gemini-Webzugang entfernen",
      message:
        "Die verschlüsselt gespeicherte Anmeldung wird entfernt. ChatGPT und offizielle Gemini-Zugänge bleiben erhalten.",
      confirmLabel: "Entfernen",
      tone: "danger",
    });
    if (!ok) return;
    setBusy(true);
    try {
      await api.deleteGeminiWebCookie();
      await load();
      setMessage("Gemini-Webzugang entfernt.");
      onChanged?.();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Entfernen fehlgeschlagen.",
      );
    } finally {
      setBusy(false);
    }
  };

  if (status && !status.available) return null;

  const badge = status?.pro_available
    ? `${status.model || "Gemini"} verfügbar`
    : status?.configured
      ? "Angemeldet · Pro nicht bestätigt"
      : "Nicht angemeldet";

  return (
    <div className="rounded-xl border border-amber-200 bg-surface p-5 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-display text-base font-bold text-brand-dark-gray">
          Gemini über lokalen Webzugang
        </h3>
        <span
          className={`rounded-full px-2 py-0.5 font-body text-[10px] font-medium text-white ${status?.pro_available ? "bg-brand-teal" : "bg-amber-500"}`}
        >
          {badge}
        </span>
      </div>
      <p className="mt-1 font-body text-xs leading-relaxed text-brand-gray">
        Optionaler letzter Gemini-Fallback für dein eigenes Konto. Die Sitzung
        wird lokal übernommen, verschlüsselt gespeichert und weder angezeigt
        noch protokolliert.
      </p>
      <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 font-body text-xs text-amber-900">
        Inoffizieller Webzugang: Google kann ihn ändern oder einschränken.
        Offizielle ChatGPT- und Gemini-Verbindungen bleiben höher priorisiert.
      </p>
      <p className="mt-2 font-body text-xs text-brand-gray">
        {status?.thinking ||
          "High wird angefordert. Das tatsächlich gelieferte Modell wird getrennt geprüft."}
      </p>
      {status?.models?.length ? (
        <p className="mt-2 font-body text-xs text-brand-gray">
          Vom Konto gemeldet: {status.models.join(", ")}
        </p>
      ) : null}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {status?.login_available && (
          <button
            type="button"
            onClick={startLogin}
            disabled={
              busy || status.login_state === "pending" || Boolean(status.ready)
            }
            className="rounded bg-brand-teal px-3 py-1.5 font-body text-xs font-medium text-white disabled:opacity-40"
          >
            {status.login_state === "pending"
              ? "Anmeldung läuft ..."
              : status.ready
                ? "Anmeldung gespeichert"
                : "Mit Google anmelden"}
          </button>
        )}
        {status?.configured && (
          <button
            type="button"
            onClick={removeCookie}
            disabled={busy}
            className="rounded px-2 py-1.5 font-body text-xs text-brand-mid-gray hover:text-red-600 disabled:opacity-40"
          >
            Entfernen
          </button>
        )}
      </div>
      <details className="mt-3">
        <summary className="cursor-pointer font-body text-xs text-brand-gray">
          Cookie-Datei manuell importieren
        </summary>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <input
            type="file"
            accept=".txt,.json"
            disabled={busy}
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            className="max-w-sm font-body text-xs text-brand-gray file:mr-2 file:rounded file:border-0 file:bg-brand-light-gray-1 file:px-3 file:py-1.5 file:text-brand-dark-gray"
            aria-label="Gemini-Cookie-Datei"
          />
          <button
            type="button"
            onClick={importCookie}
            disabled={busy || !file}
            className="rounded bg-brand-teal px-3 py-1.5 font-body text-xs font-medium text-white disabled:opacity-40"
          >
            Sicher importieren
          </button>
        </div>
      </details>
      <p
        className={`mt-2 font-body text-xs ${message.toLocaleLowerCase("de").includes("fehl") ? "text-red-600" : "text-brand-teal"}`}
      >
        {message || status?.message}
      </p>
    </div>
  );
}
