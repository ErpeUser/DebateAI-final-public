import test from "node:test";
import assert from "node:assert/strict";
import { chatStorageKey, clearMeetingChatHistory } from "./meetingChatStorage.ts";

test("chat history uses a stable per-session key and can be purged", () => {
  const values = new Map([[chatStorageKey("session-1"), "sensitive"]]);
  const storage = {
    removeItem(key) { values.delete(key); },
  };

  clearMeetingChatHistory("session-1", storage);

  assert.equal(values.size, 0);
  assert.equal(chatStorageKey("session-1"), "debateai:meeting-chat:session-1");
});
