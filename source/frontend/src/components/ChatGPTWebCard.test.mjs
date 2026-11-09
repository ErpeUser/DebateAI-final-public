import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";

const component = await readFile(new URL("./ChatGPTWebCard.tsx", import.meta.url), "utf8");
const api = await readFile(new URL("../services/api.ts", import.meta.url), "utf8");

test("offers refresh, disconnect, re-login, and account switching", () => {
  assert.match(component, /Status aktualisieren/);
  assert.match(component, /Erneut anmelden/);
  assert.match(component, /Verbindung trennen/);
  assert.match(component, /Konto wechseln/);
  assert.match(component, /useConfirm/);
  assert.match(api, /disconnectChatGPTWeb/);
  assert.match(api, /switchChatGPTWebAccount/);
});
