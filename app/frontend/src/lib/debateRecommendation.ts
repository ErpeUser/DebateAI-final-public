import type { DebateRecommendation } from "../types";

export interface DebateRecommendationState {
  sessionId: string | null;
  recommendation: DebateRecommendation | null;
}

export function emptyDebateState(
  sessionId: string | null = null,
): DebateRecommendationState {
  return { sessionId, recommendation: null };
}

export function reduceDebateUpdate(
  state: DebateRecommendationState,
  sessionId: string,
  incoming: DebateRecommendation,
): DebateRecommendationState {
  if (state.sessionId === sessionId && state.recommendation) {
    const current = state.recommendation;
    const incomingRevision =
      incoming.recommendation_revision ?? incoming.revision;
    const currentRevision = current.recommendation_revision ?? current.revision;
    const differentKnownClaim = Boolean(
      incoming.claim_id &&
      current.claim_id &&
      incoming.claim_id !== current.claim_id,
    );
    if (
      (differentKnownClaim &&
        incoming.transcript_revision <= current.transcript_revision) ||
      incomingRevision < currentRevision
    ) {
      return state;
    }
  }
  return { sessionId, recommendation: incoming };
}
