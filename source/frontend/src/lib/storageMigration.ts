const STATIC_KEYS: Array<[string, string]> = [
  ["backchannel:audio-devices", "debateai:audio-devices"],
  ["backchannel:call-bar-mode", "debateai:call-bar-mode"],
  ["backchannel.last_seen_version", "debateai.last_seen_version"],
];

const PREFIXES: Array<[string, string]> = [
  ["backchannel:ask-model:", "debateai:ask-model:"],
  ["backchannel:meeting-chat:", "debateai:meeting-chat:"],
];

export function migrateLegacyStorage(storage: Storage): void {
  for (const [legacy, canonical] of STATIC_KEYS) {
    if (storage.getItem(canonical) === null) {
      const value = storage.getItem(legacy);
      if (value !== null) storage.setItem(canonical, value);
    }
    storage.removeItem(legacy);
  }

  for (const key of Object.keys(storage)) {
    for (const [legacyPrefix, canonicalPrefix] of PREFIXES) {
      if (!key.startsWith(legacyPrefix)) continue;
      const canonical = canonicalPrefix + key.slice(legacyPrefix.length);
      if (storage.getItem(canonical) === null) {
        const value = storage.getItem(key);
        if (value !== null) storage.setItem(canonical, value);
      }
      storage.removeItem(key);
      break;
    }
  }
}
