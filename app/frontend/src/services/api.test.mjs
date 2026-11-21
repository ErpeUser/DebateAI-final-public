import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { after, test } from "node:test";
import { build } from "esbuild";

const sourcePath = fileURLToPath(new URL("./api.ts", import.meta.url));
const outputDir = await mkdtemp(join(tmpdir(), "api-test-"));
const outputPath = join(outputDir, "bundle.cjs");

await build({
  entryPoints: [sourcePath],
  bundle: true,
  format: "cjs",
  platform: "node",
  outfile: outputPath,
});

const {
  cancelTranscriptionJob,
  getDebateSettings,
  getSynthesis,
  importAudio,
  retranscribeSession,
  enhanceInsights,
  pollChatGPTWebLogin,
  getTranscriptionJob,
  updateDebateSettings,
  waitForTranscriptionJob,
} = createRequire(import.meta.url)(outputPath);

after(async () => {
  await rm(outputDir, { recursive: true, force: true });
});

// The client passes the opt-in through verbatim. The live call view gets its
// signals as insight rows instead (ALP-308); the post-call history panel is
// what asks for the raw rows.
test("the synthesis request carries the history opt-in it was given", async () => {
  const urls = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url) => {
    urls.push(url);
    return { ok: true, status: 200, json: async () => null };
  };

  try {
    await getSynthesis("session-1", "live");
    await getSynthesis("session-1", "live", true);
  } finally {
    globalThis.fetch = originalFetch;
  }

  assert.deepEqual(urls, [
    "/api/sessions/session-1/synthesis?mode=live&include_history=false",
    "/api/sessions/session-1/synthesis?mode=live&include_history=true",
  ]);
});

test("ChatGPT login polling forwards the caller abort signal", async () => {
  const controller = new AbortController();
  const originalFetch = globalThis.fetch;
  let observedSignal;
  globalThis.fetch = async (_url, options) => {
    observedSignal = options?.signal;
    return { ok: true, status: 200, json: async () => ({}) };
  };
  try {
    await pollChatGPTWebLogin(controller.signal);
  } finally {
    globalThis.fetch = originalFetch;
  }
  assert.equal(observedSignal, controller.signal);
});

test("long-running client starts forward abort signals to their POST requests", async () => {
  const controller = new AbortController();
  const originalFetch = globalThis.fetch;
  const signals = [];
  globalThis.fetch = async (_url, options) => {
    signals.push(options?.signal);
    return {
      ok: true,
      status: 200,
      json: async () => ({
        job_id: "job-1",
        kind: "audio_import",
        status: "queued",
        model_id: null,
        segments_done: 0,
        total_segments: 1,
        entries: 0,
        progress: 0,
        filename: "x.wav",
        error: "",
      }),
    };
  };
  try {
    await importAudio(
      "session-1",
      new File(["audio"], "x.wav"),
      controller.signal,
    );
    await retranscribeSession("session-1", "model-1", controller.signal);
    await enhanceInsights("session-1", controller.signal);
  } finally {
    globalThis.fetch = originalFetch;
  }
  assert.deepEqual(signals, [
    controller.signal,
    controller.signal,
    controller.signal,
  ]);
});

test("transcription jobs poll by kind until the terminal result", async () => {
  const urls = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url) => {
    urls.push(url);
    return {
      ok: true,
      status: 200,
      json: async () => ({
        job_id: "job-1",
        kind: "retranscription",
        status: urls.length === 1 ? "running" : "completed",
        model_id: "model-1",
        segments_done: urls.length,
        total_segments: 2,
        entries: 12,
        progress: urls.length * 50,
        filename: null,
        error: "",
      }),
    };
  };

  try {
    const result = await waitForTranscriptionJob(
      "session-1",
      {
        job_id: "job-1",
        kind: "retranscription",
        status: "queued",
        model_id: "model-1",
        segments_done: 0,
        total_segments: 2,
        entries: 0,
        progress: 0,
        filename: null,
        error: "",
      },
      () => {},
      0,
    );
    assert.equal(result.status, "completed");
  } finally {
    globalThis.fetch = originalFetch;
  }

  assert.deepEqual(urls, [
    "/api/sessions/session-1/retranscribe",
    "/api/sessions/session-1/retranscribe",
  ]);
});

test("transcription polling aborts before the next request when its owner unmounts", async () => {
  const controller = new AbortController();
  const calls = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url) => {
    calls.push(url);
    return {
      ok: true,
      status: 200,
      json: async () => ({
        job_id: "job-1",
        kind: "retranscription",
        status: "completed",
        model_id: "model-1",
        segments_done: 1,
        total_segments: 1,
        entries: 1,
        progress: 100,
        filename: null,
        error: "",
      }),
    };
  };

  try {
    const pending = waitForTranscriptionJob(
      "session-1",
      {
        job_id: "job-1",
        kind: "retranscription",
        status: "queued",
        model_id: "model-1",
        segments_done: 0,
        total_segments: 1,
        entries: 0,
        progress: 0,
        filename: null,
        error: "",
      },
      () => {},
      25,
      controller.signal,
    );
    const reason = new Error("component unmounted");
    controller.abort(reason);
    await assert.rejects(pending, reason);
  } finally {
    globalThis.fetch = originalFetch;
  }

  assert.deepEqual(calls, []);
});

test("transcription status requests carry the caller abort signal", async () => {
  const controller = new AbortController();
  const originalFetch = globalThis.fetch;
  let observedSignal;
  globalThis.fetch = async (_url, options) => {
    observedSignal = options?.signal;
    return {
      ok: true,
      status: 200,
      json: async () => ({
        job_id: "job-1",
        kind: "retranscription",
        status: "completed",
        model_id: "model-1",
        segments_done: 1,
        total_segments: 1,
        entries: 1,
        progress: 100,
        filename: null,
        error: "",
      }),
    };
  };

  try {
    await getTranscriptionJob(
      "session-1",
      "retranscription",
      controller.signal,
    );
  } finally {
    globalThis.fetch = originalFetch;
  }

  assert.equal(observedSignal, controller.signal);
});

test("audio import cancellation uses the import job endpoint", async () => {
  const calls = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, options) => {
    calls.push([url, options?.method]);
    return {
      ok: true,
      status: 200,
      json: async () => ({ status: "canceling" }),
    };
  };

  try {
    await cancelTranscriptionJob("session-1", "audio_import");
  } finally {
    globalThis.fetch = originalFetch;
  }

  assert.deepEqual(calls, [["/api/sessions/session-1/import/audio", "DELETE"]]);
});

test("debate settings use GET and a narrow PATCH payload", async () => {
  const calls = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, options) => {
    calls.push([url, options?.method ?? "GET", options?.body ?? null]);
    return { ok: true, status: 200, json: async () => ({}) };
  };

  try {
    await getDebateSettings();
    await updateDebateSettings({ research_frequency: "often" });
  } finally {
    globalThis.fetch = originalFetch;
  }

  assert.deepEqual(calls, [
    ["/api/debate-settings", "GET", null],
    [
      "/api/debate-settings",
      "PATCH",
      JSON.stringify({ research_frequency: "often" }),
    ],
  ]);
});
