export const CHAT_STORAGE_PREFIX = "debateai:meeting-chat:";

export function chatStorageKey(sessionId: string): string {
  return `${CHAT_STORAGE_PREFIX}${sessionId}`;
}

export function clearMeetingChatHistory(
  sessionId: string,
  storage: Pick<Storage, "removeItem"> = window.sessionStorage,
): void {
  try {
    storage.removeItem(chatStorageKey(sessionId));
  } catch {
    // Storage can be unavailable in private browsing or an embedded shell.
  }
}
