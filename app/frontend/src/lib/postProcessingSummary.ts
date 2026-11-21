// Formats the post-processing summary line shown under the "Post-processing"
// progress panel and the post-call completion banner.
//
// The backend's drain `details` counters describe ONLY the final analysis
// pass that runs while the call is ending:
// - insights_saved: new insights created by the final consolidated analyst pass
// - synthesizer_ops: updates applied to already-saved insights by the final
//   synthesizer reconciliation pass
// - opportunity_ops: offering matches applied by the final opportunity pass
// - session_insight_total: the session's total insight count at drain
//   completion (server-counted; may be absent on older backends)
//
// The copy must make the pass-vs-lifetime distinction explicit so "3 new"
// next to a session header showing 23 total insights is not confusing.

function count(details: Record<string, unknown>, key: string): number {
  const value = Number(details[key] ?? 0);
  return Number.isFinite(value) && value > 0 ? value : 0;
}

export function formatPostProcessingSummary(
  details?: Record<string, unknown>,
): string | null {
  if (!details) return null;
  const newInsights = count(details, "insights_saved");
  const updates = count(details, "synthesizer_ops");
  const matches = count(details, "opportunity_ops");
  const rawTotal = details.session_insight_total;
  const total =
    typeof rawTotal === "number" && Number.isFinite(rawTotal) && rawTotal >= 0
      ? Math.floor(rawTotal)
      : null;

  const parts = [
    newInsights
      ? `${newInsights} ${newInsights === 1 ? "neues Argument" : "neue Argumente"}`
      : null,
    updates
      ? `${updates} ${updates === 1 ? "Argument aktualisiert" : "Argumente aktualisiert"}`
      : null,
    matches
      ? `${matches} ${matches === 1 ? "Materialtreffer" : "Materialtreffer"}`
      : null,
  ].filter(Boolean);

  if (parts.length === 0 && total === null) return null;

  const passText =
    parts.length > 0
      ? `Abschließende Analyse: ${parts.join(", ")}`
      : "Abschließende Analyse: keine Änderungen";
  if (total === null) return passText;
  return `${passText} - insgesamt ${total} ${total === 1 ? "Argument" : "Argumente"} in dieser Debatte`;
}

/**
 * The drain summary the backend persisted on the session at finalize.
 *
 * Stored as JSON text so the shape stays additive. Returns null for anything
 * unusable rather than throwing: an old session has an empty column, and a
 * malformed one must not take the post-call view down with it.
 */
export function parseSavedDrainSummary(
  raw?: string | null,
): (Record<string, unknown> & { message?: string }) | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed)
      ? parsed
      : null;
  } catch {
    return null;
  }
}
