import { useMemo, useState } from "react";
import type { AtomicClaim, DebateSource } from "../types";
import { sourceStatusLabel } from "../lib/debateSource";
import * as api from "../services/api";

interface SourceInspectorProps {
  sessionId: string;
  claimId: string;
  source: DebateSource;
  atomicClaims?: AtomicClaim[];
  onCorrected?: (source: DebateSource) => void;
}

export default function SourceInspector({
  sessionId,
  claimId,
  source,
  atomicClaims = [],
  onCorrected,
}: SourceInspectorProps) {
  const initial = useMemo(
    () =>
      source.affected_claim_ids?.length
        ? source.affected_claim_ids
        : atomicClaims.map((claim) => claim.id),
    [atomicClaims, source.affected_claim_ids],
  );
  const [relation, setRelation] = useState<
    "supports" | "contradicts" | "unclear"
  >(
    source.claim_relation ??
      (source.verification_status === "supports" ||
      source.verification_status === "contradicts"
        ? source.verification_status
        : "unclear"),
  );
  const [affected, setAffected] = useState<string[]>(initial);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const displayedClaims =
    atomicClaims.length > 0
      ? atomicClaims
      : (source.affected_claim_ids ?? []).map((id, index) => ({
          id,
          text: source.affected_claims?.[index] || id,
        }));

  const save = async () => {
    setSaving(true);
    setSaved(false);
    try {
      const corrected = await api.correctDebateSource(sessionId, {
        claim_id: source.claim_id || claimId,
        source_url: source.url,
        relation,
        affected_claim_ids: affected,
      });
      setSaved(true);
      onCorrected?.(corrected);
    } finally {
      setSaving(false);
    }
  };

  return (
    <details className="min-w-0 rounded-md border border-brand-light-gray-1 bg-surface px-3 py-2">
      <summary className="cursor-pointer font-body text-xs font-semibold text-brand-dark-gray">
        {source.title || source.url} ·{" "}
        {sourceStatusLabel(source.verification_status)}
      </summary>
      <div className="mt-2 space-y-2 font-body text-[11px] leading-4 text-brand-gray">
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="bc-accent-text break-all underline"
        >
          Quelle öffnen
        </a>
        <p>
          <strong>Herausgeber:</strong> {source.publisher || "nicht angegeben"}
        </p>
        <p>
          <strong>Datum:</strong>{" "}
          {source.published_at || source.retrieved_at || "nicht angegeben"}
        </p>
        {source.section && (
          <p>
            <strong>Abschnitt:</strong> {source.section}
          </p>
        )}
        <p>
          <strong>Geprüfte Aussage:</strong> {source.claim || "nicht angegeben"}
        </p>
        {(source.passage || source.snippet) && (
          <blockquote className="rounded border-l-2 border-brand-teal bg-brand-light-gray-2 px-2 py-1.5 text-brand-dark-gray">
            {source.passage || source.snippet}
          </blockquote>
        )}
        {displayedClaims.length > 0 && (
          <fieldset className="rounded bg-brand-light-gray-2 p-2">
            <legend className="font-semibold text-brand-dark-gray">
              Betroffene Teilclaims
            </legend>
            {displayedClaims.map((claim) => (
              <label key={claim.id} className="mt-1 flex items-start gap-2">
                <input
                  type="checkbox"
                  checked={affected.includes(claim.id)}
                  onChange={(event) =>
                    setAffected((current) =>
                      event.target.checked
                        ? [...current, claim.id]
                        : current.filter((id) => id !== claim.id),
                    )
                  }
                  className="mt-0.5 accent-brand-teal"
                />
                <span>{claim.text}</span>
              </label>
            ))}
          </fieldset>
        )}
        <div className="flex flex-wrap items-center gap-2">
          <label
            className="font-semibold text-brand-dark-gray"
            htmlFor={`source-relation-${source.url}`}
          >
            Zuordnung
          </label>
          <select
            id={`source-relation-${source.url}`}
            value={relation}
            onChange={(event) =>
              setRelation(event.target.value as typeof relation)
            }
            className="rounded border border-brand-light-gray-1 bg-surface px-2 py-1"
          >
            <option value="supports">stützt</option>
            <option value="contradicts">widerspricht</option>
            <option value="unclear">unklar</option>
          </select>
          <button
            type="button"
            disabled={saving || !(source.claim_id || claimId)}
            onClick={() => void save()}
            className="rounded bg-brand-teal px-2 py-1 font-semibold text-white disabled:opacity-50"
          >
            {saving ? "Speichert…" : "Zuordnung speichern"}
          </button>
          {saved && (
            <span role="status" className="text-emerald-700">
              Graph und Empfehlung aktualisiert
            </span>
          )}
        </div>
      </div>
    </details>
  );
}
