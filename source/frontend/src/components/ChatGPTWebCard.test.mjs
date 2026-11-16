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

test("does not claim an unverified ChatGPT Pro entitlement", () => {
  assert.match(component, /ChatGPT Web über normalen Zugang/);
  assert.doesNotMatch(component, /ChatGPT Pro/);
});

test("login polling is abortable and stops after an API error", () => {
  assert.match(component, /new AbortController\(\)/);
  assert.match(component, /pollChatGPTWebLogin\([^)]*signal/);
  assert.doesNotMatch(component, /window\.setInterval\(/);
  assert.match(component, /login_state: "error"/);
});
