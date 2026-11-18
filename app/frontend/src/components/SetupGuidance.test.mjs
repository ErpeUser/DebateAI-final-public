import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const read = (name) =>
  readFileSync(new URL(name, import.meta.url), "utf8");

test("first-run guidance is German and explains local setup without demanding Gemini", () => {
  const copy = read("./WelcomeView.tsx") + read("./ProviderOnboardingCard.tsx");

  assert.doesNotMatch(copy, /free Google \(Gemini\) key covers/i);
  assert.doesNotMatch(copy, /one of these and you are done/i);
  assert.match(copy, /lokale Transkription/i);
  assert.match(copy, /Empfohlen/);
  assert.match(copy, /ändert deine Modellauswahl nicht/i);
  assert.match(copy, /Debate AI/);
  assert.match(copy, /Live-Debatten-Copilot/);
  assert.doesNotMatch(copy, /Live Debate Copilot/);
});
