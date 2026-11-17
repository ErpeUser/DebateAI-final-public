import assert from "node:assert/strict";
import test from "node:test";
import { migrateLegacyStorage } from "./storageMigration.ts";

// Only the Storage boundary is synthetic; the production migration runs unchanged.
function memoryStorage(initial = {}, beforeWrite = () => {}) {
  const storage = Object.assign(Object.create(null), initial);
  Object.defineProperties(storage, {
    getItem: { value: (key) => Object.hasOwn(storage, key) ? storage[key] : null },
    setItem: { value: (key, value) => { beforeWrite(key, value); storage[key] = String(value); } },
    removeItem: { value: (key) => { delete storage[key]; } },
    key: { value: (index) => Object.keys(storage)[index] ?? null },
    length: { get: () => Object.keys(storage).length },
  });
  return storage;
}

const mappings = [
  ["backchannel:audio-devices", "debateai:audio-devices"],
  ["backchannel:call-bar-mode", "debateai:call-bar-mode"],
  ["backchannel.last_seen_version", "debateai.last_seen_version"],
  ["bc-sidebar-collapsed", "debateai:sidebar-collapsed"],
  ["bc-sidebar-collapsed-groups", "debateai:sidebar-collapsed-groups"],
  ["bc-theme", "debateai:theme"],
  ["backchannel:ask-model:session-1", "debateai:ask-model:session-1"],
  ["backchannel:meeting-chat:session-2", "debateai:meeting-chat:session-2"],
];

for (const [legacy, canonical] of mappings) {
  test(`copy preserves the original value: ${legacy}`, () => {
    const storage = memoryStorage({ [legacy]: 'synthetic {"value":17}' });
    migrateLegacyStorage(storage);
    assert.equal(storage.getItem(canonical), 'synthetic {"value":17}');
    assert.equal(storage.getItem(legacy), 'synthetic {"value":17}');
  });

  test(`conflict preserves both values: ${legacy}`, () => {
    const storage = memoryStorage({ [legacy]: "old distinct value", [canonical]: "current custom value" });
    migrateLegacyStorage(storage);
    assert.equal(storage.getItem(canonical), "current custom value");
    assert.equal(storage.getItem(legacy), "old distinct value");
  });
}

for (const [legacy, canonical] of [mappings[5], mappings[7]]) {
  test(`empty canonical value remains authoritative: ${legacy}`, () => {
    const storage = memoryStorage({ [legacy]: "old", [canonical]: "" });
    migrateLegacyStorage(storage);
    assert.equal(storage.getItem(canonical), "");
    assert.equal(storage.getItem(legacy), "old");
  });

  test(`empty legacy value is retained and copied: ${legacy}`, () => {
    const storage = memoryStorage({ [legacy]: "" });
    migrateLegacyStorage(storage);
    assert.equal(storage.getItem(canonical), "");
    assert.equal(storage.getItem(legacy), "");
  });
}

test("retries are idempotent and cannot overwrite later canonical customization", () => {
  const initial = Object.fromEntries(mappings.map(([legacy], i) => [legacy, `original-${i}`]));
  const storage = memoryStorage(initial);
  migrateLegacyStorage(storage);
  storage.setItem("debateai:theme", "later customization");
  const afterFirst = { ...storage };
  migrateLegacyStorage(storage);
  assert.deepEqual({ ...storage }, afterFirst);
  for (const [legacy, value] of Object.entries(initial)) assert.equal(storage.getItem(legacy), value);
  assert.equal(storage.getItem("debateai:theme"), "later customization");
});

test("unknown legacy keys and unrelated data remain untouched", () => {
  const initial = { "backchannel:unknown": "preserve", "other-app:theme": "blue", "debateai:custom": "custom" };
  const storage = memoryStorage(initial);
  migrateLegacyStorage(storage);
  assert.deepEqual({ ...storage }, initial);
});

test("an empty installation gains no invented preferences", () => {
  const storage = memoryStorage();
  migrateLegacyStorage(storage);
  assert.deepEqual(Object.keys(storage), []);
});

test("partial quota failure retains every source and permits a safe retry", () => {
  let fail = true;
  const storage = memoryStorage({
    "backchannel:audio-devices": "device-original",
    "backchannel:call-bar-mode": "mode-original",
    "backchannel:meeting-chat:session-2": "chat-original",
  }, (key) => {
    if (fail && key === "debateai:call-bar-mode") throw new DOMException("Full", "QuotaExceededError");
  });
  assert.throws(() => migrateLegacyStorage(storage), { name: "QuotaExceededError" });
  assert.equal(storage.getItem("backchannel:audio-devices"), "device-original");
  assert.equal(storage.getItem("backchannel:call-bar-mode"), "mode-original");
  assert.equal(storage.getItem("backchannel:meeting-chat:session-2"), "chat-original");
  assert.equal(storage.getItem("debateai:audio-devices"), "device-original");
  assert.equal(storage.getItem("debateai:call-bar-mode"), null);
  fail = false;
  storage.setItem("debateai:audio-devices", "customized-after-failure");
  migrateLegacyStorage(storage);
  assert.equal(storage.getItem("debateai:audio-devices"), "customized-after-failure");
  assert.equal(storage.getItem("debateai:call-bar-mode"), "mode-original");
  assert.equal(storage.getItem("debateai:meeting-chat:session-2"), "chat-original");
  assert.equal(storage.getItem("backchannel:meeting-chat:session-2"), "chat-original");
});

test("multiple conversation suffixes are copied without merging identities", () => {
  const storage = memoryStorage({
    "backchannel:meeting-chat:session-1": "first",
    "backchannel:meeting-chat:session-1:reply": "reply",
    "backchannel:ask-model:session-1": "model",
  });
  migrateLegacyStorage(storage);
  assert.equal(storage.getItem("debateai:meeting-chat:session-1"), "first");
  assert.equal(storage.getItem("debateai:meeting-chat:session-1:reply"), "reply");
  assert.equal(storage.getItem("debateai:ask-model:session-1"), "model");
  assert.equal(storage.length, 6);
});
