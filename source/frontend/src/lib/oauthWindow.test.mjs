import assert from "node:assert/strict";
import { test } from "node:test";
import {
  closeOAuthWindow,
  navigateOAuthWindow,
  reserveOAuthWindow,
} from "./oauthWindow.ts";

test("OpenAI login reserves the browser from the click and navigates it later", () => {
  const calls = [];
  const popup = {
    opener: {},
    location: { replace: (url) => calls.push(["replace", url]) },
    focus: () => calls.push(["focus"]),
    close: () => calls.push(["close"]),
  };
  const reserved = reserveOAuthWindow((...args) => {
    calls.push(["open", ...args]);
    return popup;
  });

  assert.equal(reserved, popup);
  assert.equal(navigateOAuthWindow(reserved, "https://auth.example/authorize"), true);
  assert.equal(popup.opener, null);
  assert.deepEqual(calls, [
    ["open", "about:blank", "_blank", "popup,width=760,height=820"],
    ["replace", "https://auth.example/authorize"],
    ["focus"],
  ]);
});

test("blocked or failed OAuth windows retain the manual fallback safely", () => {
  assert.equal(reserveOAuthWindow(() => null), null);
  assert.equal(navigateOAuthWindow(null, "https://auth.example/authorize"), false);

  let closed = false;
  closeOAuthWindow({
    opener: null,
    location: { replace: () => {} },
    focus: () => {},
    close: () => { closed = true; },
  });
  assert.equal(closed, true);
});
