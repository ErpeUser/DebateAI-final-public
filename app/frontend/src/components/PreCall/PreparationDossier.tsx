import { useCallback, useEffect, useState } from "react";
import * as api from "../../services/api";

export default function PreparationDossier({
  sessionId,
}: {
  sessionId: string;
}) {
  const [entries, setEntries] = useState<api.DossierEntry[]>([]);
  const [kind, setKind] = useState<"thesis" | "term" | "counterposition">(
    "thesis",
  );
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [origin, setOrigin] = useState("Eigene Notiz");
  const [page, setPage] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(
    () => api.getDossier(sessionId).then((value) => setEntries(value.entries)),
    [sessionId],
  );
  useEffect(() => {
    void load();
  }, [load]);

  const add = async () => {
    if (!title.trim() || !body.trim()) return;
    setBusy(true);
    try {
      await api.addDossierEntry(sessionId, {
        kind,
        title: title.trim(),
        body: body.trim(),
        origin: origin.trim() || "Eigene Notiz",
        page_reference: page.trim(),
      });
      setTitle("");
      setBody("");
      setPage("");
      await load();
    } finally {
      setBusy(false);
    }
  };

  const upload = async (file: File) => {
    setBusy(true);
    try {
      await api.uploadDossierFile(sessionId, file, page);
      await load();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-3">
      <p className="rounded bg-brand-light-gray-2 px-3 py-2 font-body text-xs leading-5 text-brand-gray">
        Das Dossier bleibt lokal und unterstützt den lokalen Sofortcoach. Eigene
        Thesen und Notizen werden ausdrücklich nicht als unabhängige Quelle
        behandelt.
      </p>
      <div className="grid gap-2 sm:grid-cols-2">
        <select
          value={kind}
          onChange={(event) => setKind(event.target.value as typeof kind)}
          className="rounded border px-3 py-2 font-body text-xs"
        >
          <option value="thesis">Eigene Kernthese</option>
          <option value="term">Begriff / Definition</option>
          <option value="counterposition">Gegenposition</option>
        </select>
        <input
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="Kurztitel"
          className="rounded border px-3 py-2 font-body text-xs"
        />
        <input
          value={origin}
          onChange={(event) => setOrigin(event.target.value)}
          placeholder="Herkunft"
          className="rounded border px-3 py-2 font-body text-xs"
        />
        <input
          value={page}
          onChange={(event) => setPage(event.target.value)}
          placeholder="Seite / Abschnitt (optional)"
          className="rounded border px-3 py-2 font-body text-xs"
        />
        <textarea
          value={body}
          onChange={(event) => setBody(event.target.value)}
          placeholder="Inhalt"
          rows={3}
          className="sm:col-span-2 rounded border px-3 py-2 font-body text-xs"
        />
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={busy || !title.trim() || !body.trim()}
          onClick={() => void add()}
          className="rounded bg-brand-teal px-3 py-2 font-body text-xs font-semibold text-white disabled:opacity-50"
        >
          Notiz hinzufügen
        </button>
        <label className="cursor-pointer rounded border border-brand-teal px-3 py-2 font-body text-xs font-semibold text-brand-teal">
          Lokale Unterlage auswählen
          <input
            type="file"
            className="sr-only"
            disabled={busy}
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void upload(file);
              event.target.value = "";
            }}
          />
        </label>
        {entries.length > 0 && (
          <button
            type="button"
            onClick={async () => {
              if (
                window.confirm(
                  "Ganzes Dossier und alle Retrievalreferenzen löschen?",
                )
              ) {
                await api.deleteDossier(sessionId);
                setEntries([]);
              }
            }}
            className="rounded border border-red-300 px-3 py-2 font-body text-xs text-red-700"
          >
            Dossier löschen
          </button>
        )}
      </div>
      {entries.length > 0 && (
        <ul className="space-y-2">
          {entries.map((entry) => (
            <li
              key={entry.id}
              className="flex items-start justify-between gap-3 rounded border px-3 py-2 font-body text-xs"
            >
              <div>
                <p className="font-semibold text-brand-dark-gray">
                  {entry.title}
                </p>
                <p className="text-brand-mid-gray">
                  {entry.origin}
                  {entry.page_reference
                    ? ` · ${entry.page_reference}`
                    : ""} ·{" "}
                  {entry.independent_evidence
                    ? "Unterlage"
                    : "Nutzermeinung/Notiz"}
                </p>
              </div>
              <button
                type="button"
                onClick={async () => {
                  await api.deleteDossierEntry(sessionId, entry.id);
                  await load();
                }}
                className="text-red-700"
              >
                Entfernen
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
