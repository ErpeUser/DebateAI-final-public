import assert from "node:assert/strict";
import test from "node:test";
import * as core from "../site/admin/admin-core.js";

const credential = {
  email: "person@example.com",
  password: "one-time-fixture",
  password_expires_at: "2026-11-20T12:00:00Z",
};
function format(value) {
  assert.equal(
    typeof core.formatAccessCredential,
    "function",
    "Shared credential formatter is missing",
  );
  return core.formatAccessCredential(value);
}

test("credential export uses the configured absolute HTTPS portal", () => {
  for (const host of [
    "downloads.operator.example",
    "releases.another.example",
  ]) {
    const text = format({ ...credential, login_url: `https://${host}/` });
    assert.ok(text.includes(`Sign in: https://${host}/`));
    assert.ok(text.includes("Temporary password: one-time-fixture"));
    assert.equal(text.split("\n").length, 5);
  }
});

test("unconfigured or unsafe portal is explicit, not an invented relative link", () => {
  for (const login_url of [
    undefined,
    null,
    "",
    "/downloads/",
    "//host.example/",
    "http://host.example/",
    "javascript:alert(1)",
    "https://user:secret@host.example/",
    "https://host.example/?token=private",
    "https://host.example/#secret",
    "https://host.example/other",
    "https://host.example/\nInjected",
  ]) {
    const text = format({ ...credential, login_url });
    assert.ok(text.includes("Sign in: [not configured]"), String(login_url));
    assert.ok(text.includes("Temporary password: one-time-fixture"));
    assert.equal(text.split("\n").length, 5);
  }
});

// Semantic cases retained from the saved pre-integration draft; canonical API unchanged.
test("non-string and backslash-confused portals preserve the issued credential without exporting a URL", () => {
  for (const login_url of [
    42,
    {},
    [],
    "https://host.example\\@other.example/",
  ]) {
    const text = format({ ...credential, login_url });
    assert.ok(text.includes("Sign in: [not configured]"));
    assert.ok(text.includes("Temporary password: one-time-fixture"));
    assert.doesNotMatch(text, /https?:|host\.example|other\.example/);
    assert.equal(text.split("\n").length, 5);
  }
});
