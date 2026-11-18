const STATIC_KEYS: Array<[string, string]> = [
  ["backchannel:audio-devices", "debateai:audio-devices"],
  ["backchannel:call-bar-mode", "debateai:call-bar-mode"],
  ["backchannel.last_seen_version", "debateai.last_seen_version"],
  ["bc-sidebar-collapsed", "debateai:sidebar-collapsed"],
  ["bc-sidebar-collapsed-groups", "debateai:sidebar-collapsed-groups"],
  ["bc-theme", "debateai:theme"],
];

const PREFIXES: Array<[string, string]> = [
  ["backchannel:ask-model:", "debateai:ask-model:"],
  ["backchannel:meeting-chat:", "debateai:meeting-chat:"],
];

/** Copy missing canonical values without deleting the recoverable originals.
 * Existing canonical values, including empty strings, always take precedence.
 * A failed write may be retried; neither conflicts nor failures erase sources. */
export function migrateLegacyStorage(storage: Storage): void {
  for (const [legacy, canonical] of STATIC_KEYS) {
    if (storage.getItem(canonical) === null) {
      const value = storage.getItem(legacy);
      if (value !== null) storage.setItem(canonical, value);
    }
  }

  for (const key of Object.keys(storage)) {
    for (const [legacyPrefix, canonicalPrefix] of PREFIXES) {
      if (!key.startsWith(legacyPrefix)) continue;
      const canonical = canonicalPrefix + key.slice(legacyPrefix.length);
      if (storage.getItem(canonical) === null) {
        const value = storage.getItem(key);
        if (value !== null) storage.setItem(canonical, value);
      }
      break;
    }
  }
}
