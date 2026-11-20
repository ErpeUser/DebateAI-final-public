/**
 * Decide whether a polled overlay snapshot may replace the visible snapshot.
 * The endpoint is polled, so an older response can arrive after a newer one.
 */
export function shouldAcceptDebateOverlaySnapshot(current, next) {
  if (!current || current.session_id !== next.session_id) return true;
  const previous = current.recommendation;
  const incoming = next.recommendation;
  if (!previous || !incoming) return true;

  const number = (value) => Number.isFinite(Number(value)) ? Number(value) : 0;
  const ordered = [
    ["transcript_revision", number(incoming.transcript_revision), number(previous.transcript_revision)],
    ["claim_revision", number(incoming.claim_revision), number(previous.claim_revision)],
    ["recommendation_revision", number(incoming.recommendation_revision), number(previous.recommendation_revision)],
    ["revision", number(incoming.revision), number(previous.revision)],
  ];
  for (const [, nextValue, currentValue] of ordered) {
    if (nextValue > currentValue) return true;
    if (nextValue < currentValue) return false;
  }

  const nextTime = Date.parse(incoming.generated_at || "");
  const currentTime = Date.parse(previous.generated_at || "");
  if (Number.isFinite(nextTime) && Number.isFinite(currentTime) && nextTime < currentTime) {
    return false;
  }
  return true;
}
