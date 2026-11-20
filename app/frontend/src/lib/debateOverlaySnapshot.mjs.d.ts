export interface DebateOverlaySnapshotLike {
  session_id: string;
  recommendation: {
    transcript_revision?: number;
    claim_revision?: number;
    recommendation_revision?: number;
    revision?: number;
    generated_at?: string;
  } | null;
}
export function shouldAcceptDebateOverlaySnapshot(
  current: DebateOverlaySnapshotLike,
  next: DebateOverlaySnapshotLike,
): boolean;
