import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const here = new URL(".", import.meta.url);
const migrationSource = fs.readFileSync(new URL("storageMigration.ts", here), "utf8");
const mainSource = fs.readFileSync(new URL("../main.tsx", here), "utf8");

test("legacy storage migration remains the single pre-render startup boundary", () => {
  assert.match(migrationSource, /backchannel:audio-devices/);
  assert.match(migrationSource, /backchannel\.last_seen_version/);
  assert.match(migrationSource, /storage\.removeItem\(legacy\)/);
  assert.match(mainSource, /migrateLegacyStorage\(window\.localStorage\)/);
  assert.ok(
    mainSource.indexOf("migrateLegacyStorage(window.localStorage)") <
      mainSource.indexOf("ReactDOM.createRoot"),
    "migration must run before React mounts",
  );
});

test("migration keeps canonical storage values authoritative", () => {
  assert.match(
    migrationSource,
    /storage\.getItem\(canonical\) === null/,
    "legacy keys must never overwrite an existing canonical value",
  );
  assert.match(migrationSource, /storage\.removeItem\(key\)/);
});
