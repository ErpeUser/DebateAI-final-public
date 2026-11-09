export function isCurrentSessionResponse(
  requestedSessionId: string,
  currentSessionId: string | null,
): boolean {
  return requestedSessionId === currentSessionId;
}

export function shouldRecoverTranscriptsFromStatus(
  state: string,
  isVisibleSession: boolean,
): boolean {
  return isVisibleSession && ["connecting", "active", "completed"].includes(state);
}

export function hideActiveProvisionalRevisions<
  T extends { provisional?: boolean; utterance_id?: string | null },
>(entries: T[], activeSegmentIds: Set<string>): T[] {
  return entries.filter((entry) => !(
    entry.provisional
    && entry.utterance_id
    && activeSegmentIds.has(entry.utterance_id)
  ));
}
