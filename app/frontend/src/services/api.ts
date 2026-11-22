import type {
  AgentConfig,
  AIConfiguration,
  AIPromptConfig,
  AppMeta,
  ArgumentGraph,
  AsrFitReport,
  CallSegment,
  CustomEndpoint,
  DebateRecommendation,
  DebateReview,
  DebateSettings,
  DiarizationBenchmarkResult,
  DiarizationDiagnostics,
  Directive,
  Document,
  EndpointProbeResult,
  EnhanceInsightsResult,
  KnowledgeRecord,
  KnowledgeSource,
  LocalFitReport,
  LocalFitSummary,
  MeetingType,
  ModelDownload,
  ModelDownloadsStatus,
  ModelInfo,
  ModelPricingResponse,
  Offering,
  PiiEgressEntry,
  PiiPreview,
  PiiSessionSummary,
  PiiShieldSettings,
  PiiShieldStatus,
  PrivacyConfig,
  Question,
  ReleaseNote,
  Session,
  SessionGroup,
  SessionSynthesis,
  Speaker,
  TokenUsageSummary,
  TranscriptionConfig,
  TranscriptionJob,
  TranscriptEntry,
} from "../types";

const BASE = "/api";
const INSTANCE_HEADER = "X-DebateAI-Instance";
import { createDesktopSession } from "../../public/calibration/session.mjs";
const desktopSession = createDesktopSession(
  (input, init) => fetch(input, init),
  typeof window !== "undefined",
);

export const getDesktopInstanceToken = () => desktopSession.getToken();

function desktopHeaders(headers?: HeadersInit): Headers {
  const value = new Headers(headers);
  if (desktopSession.getToken())
    value.set(INSTANCE_HEADER, desktopSession.getToken());
  return value;
}

async function desktopFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  return desktopSession.fetch(input, {
    ...init,
    headers: desktopHeaders(init?.headers),
  });
}

export interface NativeAudioStatus {
  available: boolean;
  active: boolean;
  session_id: string | null;
  system_audio_active: boolean;
  last_error: string;
  microphone?: NativeAudioDevice | null;
  system_audio?: NativeAudioDevice | null;
}

export interface NativeAudioDevice {
  index: number;
  name: string;
  channels: number;
  sample_rate: number;
  loopback: boolean;
  endpoint_id: string;
  is_default: boolean;
}

export interface DebateOverlaySnapshot {
  active: boolean;
  session_id: string;
  recommendation: DebateRecommendation | null;
}

export interface GeminiWebStatus {
  available: boolean;
  configured: boolean;
  ready: boolean;
  pro_available: boolean;
  models: string[];
  model: string;
  thinking: string;
  login_available: boolean;
  login_state: "idle" | "pending" | "complete" | "error";
  message: string;
}

export const getGeminiWebStatus = () =>
  request<GeminiWebStatus>("/gemini-web/status");

export const startGeminiWebLogin = () =>
  request<GeminiWebStatus>("/gemini-web/login", { method: "POST" });

export const pollGeminiWebLogin = () =>
  request<GeminiWebStatus>("/gemini-web/login");

export const importGeminiWebCookie = async (
  file: File,
): Promise<GeminiWebStatus> => {
  const form = new FormData();
  form.append("file", file);
  const res = await desktopFetch(`${BASE}/gemini-web/cookie`, {
    method: "PUT",
    body: form,
    headers: desktopHeaders(),
  });
  if (!res.ok) {
    const text = await res.text();
    try {
      const parsed = JSON.parse(text);
      throw new Error(parsed.detail || `Import fehlgeschlagen (${res.status})`);
    } catch (error) {
      if (error instanceof Error && !error.message.startsWith("Unexpected"))
        throw error;
      throw new Error(`Import fehlgeschlagen (${res.status})`);
    }
  }
  return res.json();
};

export const deleteGeminiWebCookie = () =>
  request<void>("/gemini-web/cookie", { method: "DELETE" });

export interface ChatGPTWebStatus {
  available: boolean;
  configured: boolean;
  ready: boolean;
  model: string;
  thinking: string;
  latency_ms: number | null;
  verified_at: string;
  verification: string;
  login_available: boolean;
  login_state: "idle" | "pending" | "complete" | "error";
  message: string;
}

export const getChatGPTWebStatus = () =>
  request<ChatGPTWebStatus>("/chatgpt-web/status");

export const startChatGPTWebLogin = () =>
  request<ChatGPTWebStatus>("/chatgpt-web/login", { method: "POST" });

export const pollChatGPTWebLogin = (signal?: AbortSignal) =>
  request<ChatGPTWebStatus>("/chatgpt-web/login", { signal });

export const disconnectChatGPTWeb = () =>
  request<ChatGPTWebStatus>("/chatgpt-web/account/disconnect", {
    method: "POST",
  });

export const switchChatGPTWebAccount = () =>
  request<ChatGPTWebStatus>("/chatgpt-web/account/switch", { method: "POST" });

export type SubscriptionProvider = "gemini-cli" | "codex";

export interface SubscriptionAccountsStatus {
  available: boolean;
  models: string[];
  gemini: {
    provider: "gemini-cli";
    model: string;
    thinking: "high";
    ready: boolean;
  };
  openai: {
    provider: "codex";
    ready: boolean;
  };
  login_state: "idle" | "pending" | "complete" | "error";
  message: string;
  provider?: SubscriptionProvider;
  auth_url?: string;
  state?: string;
  verification?: { model: string; thinking: "high"; answer: string };
}

export const getSubscriptionAccountsStatus = () =>
  request<SubscriptionAccountsStatus>("/subscription-accounts/status");

export const startSubscriptionLogin = (provider: SubscriptionProvider) =>
  request<SubscriptionAccountsStatus>(
    `/subscription-accounts/login/${provider}`,
    { method: "POST" },
  );

export const pollSubscriptionLogin = (
  provider: SubscriptionProvider,
  state: string,
) =>
  request<SubscriptionAccountsStatus>(
    `/subscription-accounts/login/${provider}?state=${encodeURIComponent(state)}`,
  );

export const verifyGeminiCliHigh = () =>
  request<SubscriptionAccountsStatus>(
    "/subscription-accounts/verify/gemini-cli",
    { method: "POST" },
  );

export const getDebateOverlaySnapshot = () =>
  request<DebateOverlaySnapshot>("/sessions/live/debate-overlay");

export async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const headers = desktopHeaders(options?.headers);
  if (!headers.has("Content-Type") && !(options?.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const res = await desktopFetch(`${BASE}${path}`, {
    ...options,
    headers,
  });
  if (!res.ok) {
    const text = await res.text();
    let detail = text;
    try {
      const parsed = JSON.parse(text);
      if (parsed && typeof parsed.detail === "string") detail = parsed.detail;
    } catch {
      // Non-JSON error body (e.g. a bare proxy error page); show it as-is.
    }
    throw new Error(`API-Fehler ${res.status}: ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

/**
 * A page returned by one of the cursor-based collection endpoints.
 *
 * The collection helpers below intentionally keep returning arrays to their
 * existing callers.  They follow the opaque response cursor until the full
 * collection has been read, so screens do not accidentally render only the
 * first page when a collection grows beyond the API page size.
 */
export interface CursorPage<T> {
  items: T[];
  nextCursor: string | null;
}

const CURSOR_PAGE_LIMIT = 200;
const KNOWLEDGE_RECORD_PAGE_LIMIT = 500;
const MAX_CURSOR_PAGES = 10_000;

function withCursorQuery(
  path: string,
  limit: number,
  cursor: string | null,
): string {
  const params = new URLSearchParams({ limit: String(limit) });
  if (cursor) params.set("cursor", cursor);
  return `${path}${path.includes("?") ? "&" : "?"}${params.toString()}`;
}

async function requestCursorPage<T>(path: string): Promise<CursorPage<T>> {
  const res = await desktopFetch(`${BASE}${path}`, {
    headers: desktopHeaders(),
  });
  if (!res.ok) {
    const text = await res.text();
    let detail = text;
    try {
      const parsed = JSON.parse(text);
      if (parsed && typeof parsed.detail === "string") detail = parsed.detail;
    } catch {
      // Non-JSON error body (e.g. a bare proxy error page); show it as-is.
    }
    throw new Error(`API-Fehler ${res.status}: ${detail}`);
  }
  const items = (await res.json()) as T[];
  const nextCursor = res.headers?.get("X-Next-Cursor")?.trim() || null;
  return { items, nextCursor };
}

async function requestAllCursorPages<T>(
  path: string,
  limit = CURSOR_PAGE_LIMIT,
): Promise<T[]> {
  const items: T[] = [];
  const seenCursors = new Set<string>();
  let cursor: string | null = null;

  for (let page = 0; page < MAX_CURSOR_PAGES; page += 1) {
    const result: CursorPage<T> = await requestCursorPage<T>(
      withCursorQuery(path, limit, cursor),
    );
    items.push(...result.items);
    if (!result.nextCursor) return items;
    if (seenCursors.has(result.nextCursor)) {
      throw new Error("API-Seitenfolge enthält einen wiederholten Cursor");
    }
    seenCursors.add(result.nextCursor);
    cursor = result.nextCursor;
  }

  throw new Error("API-Seitenlimit überschritten");
}

// Sessions
export const createSession = (
  name: string,
  data?: { meeting_type?: MeetingType; meeting_context?: string },
) =>
  request<Session>("/sessions", {
    method: "POST",
    body: JSON.stringify({ name, ...data }),
  });

export const listSessions = () =>
  requestAllCursorPages<Session>("/sessions");

export const getSession = (id: string) => request<Session>(`/sessions/${id}`);

export const updateSession = (id: string, data: Partial<Session>) =>
  request<Session>(`/sessions/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export const deleteSession = (id: string) =>
  request<void>(`/sessions/${id}`, { method: "DELETE" });

export const getNativeAudioStatus = () =>
  request<NativeAudioStatus>("/native-audio/status");

export const getNativeAudioDevices = () =>
  request<{ available: boolean; devices: NativeAudioDevice[] }>(
    "/native-audio/devices",
  );

export const startNativeAudio = (
  sessionId: string,
  systemAudio = true,
  devices?: {
    microphone_id?: string;
    loopback_id?: string;
    microphone_mode?: "fixed" | "follow_default";
    loopback_mode?: "fixed" | "follow_default";
  },
) =>
  request<NativeAudioStatus>("/native-audio/start", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      system_audio: systemAudio,
      ...devices,
    }),
  });

export const stopNativeAudio = () =>
  request<NativeAudioStatus>("/native-audio/stop", { method: "POST" });

export const probeNativeMicrophone = (microphoneIndex: number) =>
  request<{ level: number }>("/native-audio/probe", {
    method: "POST",
    body: JSON.stringify({ microphone_index: microphoneIndex }),
  });

export const enhanceInsights = (id: string, signal?: AbortSignal) =>
  request<EnhanceInsightsResult>(`/sessions/${id}/enhance-insights`, {
    method: "POST",
    signal,
  });

export const getEnhancementStatus = (
  id: string,
  runId: string,
  signal?: AbortSignal,
) =>
  request<EnhanceInsightsResult>(`/sessions/${id}/enhance-insights/${runId}`, {
    signal,
  });

export const getLatestEnhancement = (id: string) =>
  request<EnhanceInsightsResult | null>(
    `/sessions/${id}/enhance-insights/latest`,
  );

function abortReason(signal?: AbortSignal): Error {
  const reason = signal?.reason;
  return reason instanceof Error
    ? reason
    : new DOMException("The operation was aborted", "AbortError");
}

function throwIfAborted(signal?: AbortSignal): void {
  if (signal?.aborted) throw abortReason(signal);
}

function waitForPoll(pollMs: number, signal?: AbortSignal): Promise<void> {
  throwIfAborted(signal);
  return new Promise((resolve, reject) => {
    let timer: ReturnType<typeof setTimeout>;
    const onAbort = () => {
      clearTimeout(timer);
      signal?.removeEventListener("abort", onAbort);
      reject(abortReason(signal));
    };
    timer = setTimeout(() => {
      signal?.removeEventListener("abort", onAbort);
      resolve();
    }, pollMs);
    signal?.addEventListener("abort", onAbort, { once: true });
    if (signal?.aborted) onAbort();
  });
}

export async function waitForEnhancement(
  id: string,
  initial: EnhanceInsightsResult,
  onProgress: (result: EnhanceInsightsResult) => void,
  signal?: AbortSignal,
): Promise<EnhanceInsightsResult> {
  let result = initial;
  while (result.status === "running" && result.run_id) {
    throwIfAborted(signal);
    onProgress(result);
    await waitForPoll(1000, signal);
    result = await getEnhancementStatus(id, result.run_id, signal);
  }
  throwIfAborted(signal);
  return result;
}

export const getSynthesis = (
  id: string,
  mode = "post_call",
  includeHistory = false,
) =>
  request<SessionSynthesis | null>(
    `/sessions/${id}/synthesis?mode=${encodeURIComponent(mode)}&include_history=${includeHistory}`,
  );

export const refreshSynthesis = (id: string, mode = "post_call") =>
  request<SessionSynthesis>(
    `/sessions/${id}/synthesis/refresh?mode=${encodeURIComponent(mode)}`,
    { method: "POST" },
  );

export const analyzeSession = (id: string) =>
  request<{ analyzed: number; session_id: string }>(`/sessions/${id}/analyze`, {
    method: "POST",
  });

export const getTokenUsage = (id: string) =>
  request<TokenUsageSummary>(`/sessions/${id}/token-usage`);

// Directives
export const createDirective = (sessionId: string, text: string) =>
  request<Directive>(`/sessions/${sessionId}/directives`, {
    method: "POST",
    body: JSON.stringify({ text }),
  });

export const listDirectives = (sessionId: string) =>
  requestAllCursorPages<Directive>(`/sessions/${sessionId}/directives`);

export const updateDirective = (
  sessionId: string,
  id: string,
  data: Partial<Directive>,
) =>
  request<Directive>(`/sessions/${sessionId}/directives/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export const deleteDirective = (sessionId: string, id: string) =>
  request<void>(`/sessions/${sessionId}/directives/${id}`, {
    method: "DELETE",
  });

// Documents
export const uploadDocument = async (
  sessionId: string,
  file: File,
): Promise<Document> => {
  const form = new FormData();
  form.append("file", file);
  const res = await desktopFetch(`${BASE}/sessions/${sessionId}/documents`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    let detail = "";
    try {
      detail = (await res.json()).detail ?? "";
    } catch {
      // non-JSON error body
    }
    throw new Error(detail || `Hochladen fehlgeschlagen: ${res.status}`);
  }
  return res.json();
};

export const listDocuments = (sessionId: string) =>
  requestAllCursorPages<Document>(`/sessions/${sessionId}/documents`);

export const deleteDocument = (sessionId: string, id: string) =>
  request<void>(`/sessions/${sessionId}/documents/${id}`, { method: "DELETE" });

export interface DossierEntry {
  id: string;
  title: string;
  body: string;
  kind: "document" | "thesis" | "term" | "counterposition";
  origin: string;
  page_reference: string;
  independent_evidence: boolean;
}

export const getDossier = (sessionId: string) =>
  request<{ source_id: string; entries: DossierEntry[] }>(
    `/sessions/${sessionId}/dossier`,
  );

export const addDossierEntry = (
  sessionId: string,
  entry: Omit<DossierEntry, "id" | "independent_evidence">,
) =>
  request<DossierEntry>(`/sessions/${sessionId}/dossier/entries`, {
    method: "POST",
    body: JSON.stringify(entry),
  });

export const uploadDossierFile = async (
  sessionId: string,
  file: File,
  pageReference = "",
) => {
  const form = new FormData();
  form.append("file", file);
  const response = await desktopFetch(
    `${BASE}/sessions/${sessionId}/dossier/files?page_reference=${encodeURIComponent(pageReference)}`,
    {
      method: "POST",
      body: form,
    },
  );
  if (!response.ok)
    throw new Error(`Dossier-Import fehlgeschlagen (${response.status})`);
  return response.json() as Promise<DossierEntry>;
};

export const deleteDossierEntry = (sessionId: string, entryId: string) =>
  request<void>(`/sessions/${sessionId}/dossier/entries/${entryId}`, {
    method: "DELETE",
  });

export const deleteDossier = (sessionId: string) =>
  request<void>(`/sessions/${sessionId}/dossier`, { method: "DELETE" });

// Questions
export const listQuestions = (sessionId: string) =>
  requestAllCursorPages<Question>(`/sessions/${sessionId}/questions`);

export const updateQuestion = (
  sessionId: string,
  id: string,
  data: Partial<Question>,
) =>
  request<Question>(`/sessions/${sessionId}/questions/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

// Speakers
export const createSpeaker = (
  sessionId: string,
  data: {
    name: string;
    role?: string;
    color?: string;
    is_user?: boolean;
    speaker_type?: "team" | "external";
  },
) =>
  request<Speaker>(`/sessions/${sessionId}/speakers`, {
    method: "POST",
    body: JSON.stringify(data),
  });

export const listSpeakers = (sessionId: string) =>
  request<Speaker[]>(`/sessions/${sessionId}/speakers`);

export const updateSpeaker = (
  sessionId: string,
  id: string,
  data: Partial<Speaker>,
) =>
  request<Speaker>(`/sessions/${sessionId}/speakers/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export const mergeSpeaker = (
  sessionId: string,
  sourceId: string,
  targetId: string,
) =>
  request<{
    source_speaker_id: string;
    target_speaker_id: string;
    transcript_entries_updated: number;
    questions_updated: number;
  }>(`/sessions/${sessionId}/speakers/${sourceId}/merge`, {
    method: "POST",
    body: JSON.stringify({ target_speaker_id: targetId }),
  });

export const deleteSpeaker = (sessionId: string, id: string) =>
  request<void>(`/sessions/${sessionId}/speakers/${id}`, { method: "DELETE" });

export const updateTranscriptText = (
  sessionId: string,
  transcriptId: string,
  text: string,
  correctionReason = "Manuelle Korrektur",
) =>
  request<TranscriptEntry>(
    `/sessions/${sessionId}/transcripts/${transcriptId}`,
    {
      method: "PATCH",
      body: JSON.stringify({ text, correction_reason: correctionReason }),
    },
  );

export const listTranscripts = (sessionId: string) =>
  requestAllCursorPages<TranscriptEntry>(`/sessions/${sessionId}/transcripts`, 500);

// Call Segments
export const listSegments = (sessionId: string) =>
  requestAllCursorPages<CallSegment>(`/sessions/${sessionId}/segments`, 500);

// Import transcript/audio
export const importTranscript = async (
  sessionId: string,
  file: File,
): Promise<{ imported: number; filename: string }> => {
  const form = new FormData();
  form.append("file", file);
  const res = await desktopFetch(
    `${BASE}/sessions/${sessionId}/import/transcript`,
    {
      method: "POST",
      body: form,
    },
  );
  if (!res.ok) throw new Error(`Import fehlgeschlagen: ${res.status}`);
  return res.json();
};

export const importAudio = async (
  sessionId: string,
  file: File,
  signal?: AbortSignal,
): Promise<TranscriptionJob> => {
  const form = new FormData();
  form.append("file", file);
  const res = await desktopFetch(`${BASE}/sessions/${sessionId}/import/audio`, {
    method: "POST",
    body: form,
    signal,
  });
  if (!res.ok) throw new Error(`Import fehlgeschlagen: ${res.status}`);
  return res.json();
};

// Models
export const listModels = () => request<ModelInfo[]>("/models");

export const getModelPricing = () =>
  request<ModelPricingResponse>("/models/pricing");

// App metadata (version + release notes)
export const getAppMeta = () => request<AppMeta>("/meta");

export const listReleaseNotes = () =>
  request<ReleaseNote[]>("/meta/release-notes");

export const segmentAudioUrl = (sessionId: string, segmentNumber: number) =>
  `${BASE}/sessions/${sessionId}/segments/${segmentNumber}/audio`;

export const retranscribeSession = (
  sessionId: string,
  modelId: string,
  signal?: AbortSignal,
) =>
  request<TranscriptionJob>(`/sessions/${sessionId}/retranscribe`, {
    method: "POST",
    body: JSON.stringify({ model_id: modelId }),
    signal,
  });

const transcriptionJobPath = (
  sessionId: string,
  kind: TranscriptionJob["kind"],
) =>
  kind === "audio_import"
    ? `/sessions/${sessionId}/import/audio`
    : `/sessions/${sessionId}/retranscribe`;

export const transcriptionJobActive = (job: TranscriptionJob) =>
  job.status === "queued" ||
  job.status === "running" ||
  job.status === "canceling";

export const getTranscriptionJob = (
  sessionId: string,
  kind: TranscriptionJob["kind"],
  signal?: AbortSignal,
) =>
  request<TranscriptionJob>(
    `${transcriptionJobPath(sessionId, kind)}${kind === "audio_import" ? "/status" : ""}`,
    { signal },
  );

export const cancelTranscriptionJob = (
  sessionId: string,
  kind: TranscriptionJob["kind"],
) =>
  request<TranscriptionJob>(transcriptionJobPath(sessionId, kind), {
    method: "DELETE",
  });

export async function waitForTranscriptionJob(
  sessionId: string,
  initial: TranscriptionJob,
  onProgress: (job: TranscriptionJob) => void,
  pollMs = 1000,
  signal?: AbortSignal,
): Promise<TranscriptionJob> {
  let job = initial;
  while (transcriptionJobActive(job)) {
    throwIfAborted(signal);
    onProgress(job);
    await waitForPoll(pollMs, signal);
    job = await getTranscriptionJob(sessionId, job.kind, signal);
  }
  throwIfAborted(signal);
  onProgress(job);
  return job;
}

export const chat = (
  modelId: string,
  sessionIds: string[],
  messages: { role: string; content: string }[],
) =>
  request<{ reply: string }>("/chat", {
    method: "POST",
    body: JSON.stringify({
      model_id: modelId,
      session_ids: sessionIds,
      messages,
    }),
  });

// A self-hosted endpoint can hang for LLM_SELF_HOSTED_TIMEOUT_SECONDS (900s)
// and the cloud path has no explicit timeout either; the live ask bar's
// target is 4 seconds, so a client-side abort keeps a stuck request from
// blocking every later ask for minutes (ALP-178). request() already forwards
// any RequestInit field, including signal, so no change there is needed.
const ASK_TIMEOUT_MS = 60_000;

export const askSession = (
  sessionId: string,
  modelId: string,
  question: string,
) =>
  request<Question>(`/sessions/${sessionId}/ask`, {
    method: "POST",
    body: JSON.stringify({ model_id: modelId, question }),
    signal: AbortSignal.timeout(ASK_TIMEOUT_MS),
  });

// Credentials (workspace API keys)
export interface CredentialInfo {
  provider: string;
  configured: boolean;
  env_fallback: boolean;
  masked: string;
  connected: boolean;
}

export const listCredentials = () => request<CredentialInfo[]>("/credentials");

export const saveCredential = (provider: string, apiKey: string) =>
  request<CredentialInfo & { message?: string }>(`/credentials/${provider}`, {
    method: "PUT",
    body: JSON.stringify({ api_key: apiKey }),
  });

export const deleteCredential = (provider: string) =>
  request<void>(`/credentials/${provider}`, { method: "DELETE" });

export const testCredential = (provider: string) =>
  request<{ ok: boolean; message: string }>(`/credentials/${provider}/test`, {
    method: "POST",
  });

// Self-hosted OpenAI-compatible endpoints (LM Studio, Ollama, vLLM, LiteLLM).
// Each endpoint's models become named entries in the model list, so they are
// managed here rather than as a single provider credential.
export const OPENAI_COMPATIBLE_PROVIDER = "openai-compatible";

export interface EndpointPayload {
  name?: string;
  base_url?: string;
  /** Omit to keep the stored key; empty string clears it. */
  api_key?: string;
  models?: { id: string; label?: string }[];
  enabled?: boolean;
  confirm_off_prem?: boolean;
}

export const listEndpoints = () => request<CustomEndpoint[]>("/endpoints");

export const createEndpoint = (data: EndpointPayload) =>
  request<CustomEndpoint>("/endpoints", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const updateEndpoint = (id: string, data: EndpointPayload) =>
  request<CustomEndpoint>(`/endpoints/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });

export const deleteEndpoint = (id: string) =>
  request<void>(`/endpoints/${id}`, { method: "DELETE" });

export const testEndpoint = (id: string) =>
  request<EndpointProbeResult & { endpoint: CustomEndpoint }>(
    `/endpoints/${id}/test`,
    {
      method: "POST",
    },
  );

/** Check a base URL before saving it, and list the models it serves. */
export const probeEndpoint = (baseUrl: string, apiKey = "") =>
  request<EndpointProbeResult>("/endpoints/probe", {
    method: "POST",
    body: JSON.stringify({ base_url: baseUrl, api_key: apiKey }),
  });

// Diagnostics
export const getDiarizationDiagnostics = () =>
  request<DiarizationDiagnostics>("/diagnostics/diarization");

export const updateDiarizationConfig = (data: {
  selected_live_diarizer?: "lightweight" | "sortformer";
  speaker_similarity_threshold?: number;
}) =>
  request<DiarizationDiagnostics>("/diagnostics/diarization/config", {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export interface VoiceProfileStatus {
  enrolled: boolean;
}

export const getVoiceProfileStatus = () =>
  request<VoiceProfileStatus>("/diagnostics/diarization/voice-profile");

export const replaceVoiceProfile = async (
  file: File,
): Promise<VoiceProfileStatus> => {
  const form = new FormData();
  form.append("file", file);
  const response = await desktopFetch(
    `${BASE}/diagnostics/diarization/voice-profile`,
    {
      method: "PUT",
      body: form,
    },
  );
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
};

export const deleteVoiceProfile = () =>
  request<void>("/diagnostics/diarization/voice-profile", { method: "DELETE" });

// Local Model Fit Test
export const getLocalFitSummary = () =>
  request<LocalFitSummary>("/diagnostics/local-fit");

export const runLocalFit = () =>
  request<LocalFitReport>("/diagnostics/local-fit/run", { method: "POST" });

export const applyLocalFitIntervals = (
  modelId: string,
  updates: { slug: string; interval_seconds: number }[],
) =>
  request<{ applied: Record<string, number> }>("/diagnostics/local-fit/apply", {
    method: "POST",
    body: JSON.stringify({ model_id: modelId, updates }),
  });

export const runAsrFit = async (file: File): Promise<AsrFitReport> => {
  const form = new FormData();
  form.append("file", file);
  const res = await desktopFetch(`${BASE}/diagnostics/local-fit/asr`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const text = await res.text();
    let detail = text;
    try {
      const parsed = JSON.parse(text);
      if (parsed && typeof parsed.detail === "string") detail = parsed.detail;
    } catch {
      // Non-JSON error body; show it as-is.
    }
    throw new Error(detail);
  }
  return res.json();
};

export const getPrivacyConfig = () => request<PrivacyConfig>("/privacy");

export const updatePrivacyConfig = (localOnly: boolean) =>
  request<PrivacyConfig>("/privacy", {
    method: "PUT",
    body: JSON.stringify({ local_only: localOnly }),
  });

export const getDebateSettings = () =>
  request<DebateSettings>("/debate-settings");

export const getDebateProfiles = () =>
  request<import("../types").DebateProfile[]>("/debate-settings/profiles");

export const applyDebateProfile = (profileId: string) =>
  request<DebateSettings>(
    `/debate-settings/profiles/${encodeURIComponent(profileId)}`,
    { method: "POST" },
  );

export const updateDebateSettings = (
  update: Partial<
    Pick<
      DebateSettings,
      | "mode"
      | "research_enabled"
      | "research_frequency"
      | "always_analogy"
      | "style_focus"
      | "voice_commands_enabled"
      | "argument_memory_enabled"
      | "transcript_retention_enabled"
      | "audio_archive_enabled"
      | "session_retrieval_enabled"
      | "learning_examples_enabled"
      | "graph_recording_enabled"
      | "memory_similarity_threshold"
      | "performance_profile"
      | "simple_1to1_audio_mode"
      | "pipeline_mode"
    >
  >,
) =>
  request<DebateSettings>("/debate-settings", {
    method: "PATCH",
    body: JSON.stringify(update),
  });

export const getDebateReview = (sessionId: string) =>
  request<DebateReview | null>(`/sessions/${sessionId}/debate-review`);

export const getArgumentGraph = (sessionId: string) =>
  request<ArgumentGraph>(`/sessions/${sessionId}/debate-review/argument-graph`);

export const generateDebateReview = (sessionId: string) =>
  request<DebateReview>(`/sessions/${sessionId}/debate-review/generate`, {
    method: "POST",
    body: JSON.stringify({ confirmed: true }),
  });

export const applyDebateReview = (sessionId: string) =>
  request<DebateReview>(`/sessions/${sessionId}/debate-review/apply`, {
    method: "POST",
    body: JSON.stringify({ confirmed: true }),
  });

export const correctDebateSource = (
  sessionId: string,
  correction: {
    claim_id: string;
    source_url: string;
    relation: "supports" | "contradicts" | "unclear";
    affected_claim_ids: string[];
  },
) =>
  request<import("../types").DebateSource>(
    `/sessions/${sessionId}/debate-review/source`,
    {
      method: "PUT",
      body: JSON.stringify(correction),
    },
  );

export const getPiiShield = () => request<PiiShieldStatus>("/pii-shield");

export const updatePiiShield = (update: Partial<PiiShieldSettings>) =>
  request<PiiShieldStatus>("/pii-shield", {
    method: "PUT",
    body: JSON.stringify(update),
  });

export const previewPiiShield = (text: string, sessionId?: string) =>
  request<PiiPreview>("/pii-shield/preview", {
    method: "POST",
    body: JSON.stringify({ text, session_id: sessionId ?? null }),
  });

export const getPiiEgress = (limit = 50) =>
  request<{ enabled: boolean; entries: PiiEgressEntry[] }>(
    `/pii-shield/egress?limit=${limit}`,
  );

export const clearPiiEgress = () =>
  request<void>("/pii-shield/egress", { method: "DELETE" });

export const installPiiNer = () =>
  request<ModelDownload>("/pii-shield/ner/install", { method: "POST" });

// Model downloads
export const getModelDownloads = () =>
  request<ModelDownloadsStatus>("/model-downloads");

export const retryModelDownload = (key: string) =>
  request<ModelDownload>(`/model-downloads/${encodeURIComponent(key)}/retry`, {
    method: "POST",
  });

export const dismissModelDownload = (key: string) =>
  request<void>(`/model-downloads/${encodeURIComponent(key)}`, {
    method: "DELETE",
  });

export const getSessionPiiSummary = (sessionId: string) =>
  request<PiiSessionSummary>(`/sessions/${sessionId}/pii/summary`);

export const getTranscriptionConfig = () =>
  request<TranscriptionConfig>("/diagnostics/transcription");

export interface TranscriptionReadiness {
  ready: boolean;
  model_id: string;
  provider: string;
  reason: string;
}

export const getTranscriptionReadiness = () =>
  request<TranscriptionReadiness>("/diagnostics/transcription/readiness");

export const updateTranscriptionConfig = (data: {
  batch_model_id?: string;
  live_preview_model_id?: string;
  language?: string;
}) =>
  request<TranscriptionConfig>("/diagnostics/transcription/config", {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export const runSortformerBenchmark = async (
  file: File,
): Promise<DiarizationBenchmarkResult> => {
  const form = new FormData();
  form.append("file", file);
  const res = await desktopFetch(
    `${BASE}/diagnostics/diarization/sortformer/benchmark`,
    {
      method: "POST",
      body: form,
    },
  );
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Benchmark fehlgeschlagen (${res.status}): ${text}`);
  }
  return res.json();
};

// Offerings
export const listOfferings = (vendor?: string, category?: string) => {
  const params = new URLSearchParams();
  if (vendor) params.set("vendor", vendor);
  if (category) params.set("category", category);
  params.set("active_only", "false");
  const qs = params.toString();
  return request<Offering[]>(`/offerings${qs ? `?${qs}` : ""}`);
};

export const createOffering = (
  data: Omit<Offering, "id" | "created_at" | "updated_at">,
) =>
  request<Offering>("/offerings", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const updateOffering = (id: string, data: Partial<Offering>) =>
  request<Offering>(`/offerings/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export const deleteOffering = (id: string) =>
  request<void>(`/offerings/${id}`, { method: "DELETE" });

export const importOfferings = async (
  file: File,
): Promise<{ created: number; skipped: number; total_rows: number }> => {
  const form = new FormData();
  form.append("file", file);
  const res = await desktopFetch(`${BASE}/offerings/import`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(`Import fehlgeschlagen: ${res.status}`);
  return res.json();
};

export const seedOfferings = (replace = false) =>
  request<{ created?: number; replaced?: boolean; message?: string }>(
    `/offerings/seed${replace ? "?replace=true" : ""}`,
    { method: "POST" },
  );

export const listOfferingVendors = () =>
  request<string[]>("/offerings/vendors");
export const listOfferingCategories = () =>
  request<string[]>("/offerings/categories");
export const listOfferingTags = () => request<string[]>("/offerings/tags");

// Knowledge Sources
export const listKnowledgeSources = () =>
  requestAllCursorPages<KnowledgeSource>("/knowledge");

export const createKnowledgeSource = (data: {
  name: string;
  source_type: string;
  description?: string;
}) =>
  request<KnowledgeSource>("/knowledge", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const updateKnowledgeSource = (
  id: string,
  data: Partial<KnowledgeSource>,
) =>
  request<KnowledgeSource>(`/knowledge/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export const deleteKnowledgeSource = (id: string) =>
  request<{ ok: boolean }>(`/knowledge/${id}`, { method: "DELETE" });

export const listKnowledgeRecords = (sourceId: string) =>
  requestAllCursorPages<KnowledgeRecord>(
    `/knowledge/${sourceId}/records`,
    KNOWLEDGE_RECORD_PAGE_LIMIT,
  );

export const createKnowledgeRecord = (
  sourceId: string,
  data: { title: string; body: string },
) =>
  request<KnowledgeRecord>(`/knowledge/${sourceId}/records`, {
    method: "POST",
    body: JSON.stringify(data),
  });

export const updateKnowledgeRecord = (
  recordId: string,
  data: Partial<KnowledgeRecord>,
) =>
  request<KnowledgeRecord>(`/knowledge/records/${recordId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export const deleteKnowledgeRecord = (recordId: string) =>
  request<{ ok: boolean }>(`/knowledge/records/${recordId}`, {
    method: "DELETE",
  });

export const importKnowledgeRecords = async (
  sourceId: string,
  file: File,
): Promise<{ created: number; skipped: number; total_rows: number }> => {
  const form = new FormData();
  form.append("file", file);
  const res = await desktopFetch(
    `${BASE}/knowledge/${sourceId}/records/import`,
    { method: "POST", body: form },
  );
  if (!res.ok) throw new Error(`Import fehlgeschlagen: ${res.status}`);
  return res.json();
};

export const uploadKnowledgeFile = async (
  sourceId: string,
  file: File,
): Promise<{ record_id: string; title: string; chars: number }> => {
  const form = new FormData();
  form.append("file", file);
  const res = await desktopFetch(`${BASE}/knowledge/${sourceId}/files`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(`Hochladen fehlgeschlagen: ${res.status}`);
  return res.json();
};

// Agents
export const listAgents = () => request<AgentConfig[]>("/agents");
export const updateAgent = (slug: string, data: Partial<AgentConfig>) =>
  request<AgentConfig>(`/agents/${slug}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
export const resetAgentPrompt = (slug: string) =>
  request<AgentConfig>(`/agents/reset/${slug}`, { method: "POST" });

export const getAIConfiguration = () => request<AIConfiguration>("/ai-config");
export const updateAIProviders = (providers: AIConfiguration["providers"]) =>
  request<AIConfiguration["providers"]>("/ai-config/providers", {
    method: "PUT",
    body: JSON.stringify(providers),
  });
export const resetAIProviders = () =>
  request<AIConfiguration["providers"]>("/ai-config/providers/reset", {
    method: "POST",
  });
export const updateAIPrompt = (name: string, content: string) =>
  request<AIPromptConfig>(`/ai-config/prompts/${encodeURIComponent(name)}`, {
    method: "PUT",
    body: JSON.stringify({ content }),
  });
export const resetAIPrompt = (name: string) =>
  request<AIPromptConfig>(
    `/ai-config/prompts/${encodeURIComponent(name)}/reset`,
    { method: "POST" },
  );
export const restoreAIPrompt = (name: string, version: string) =>
  request<AIPromptConfig>(
    `/ai-config/prompts/${encodeURIComponent(name)}/restore/${encodeURIComponent(version)}`,
    { method: "POST" },
  );
export const openAIConfigurationFolder = () =>
  request<{ opened: boolean; directory: string }>("/ai-config/open-folder", {
    method: "POST",
  });

// Session Groups
export const listGroups = () => request<SessionGroup[]>("/groups");
export const createGroup = (name: string) =>
  request<SessionGroup>("/groups", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
export const deleteGroup = (id: string) =>
  request<void>(`/groups/${id}`, { method: "DELETE" });

// Quality / prompt laboratory ------------------------------------------------
// The backend may be supplied by a later integration branch. These typed
// calls deliberately surface an unavailable provider as an error instead of
// presenting a mocked success to the operator.
export interface QualityLabCandidate {
  variant_id: string;
  model_id: string;
  model_name?: string;
  prompt_version: string;
  prompt_hash: string;
  answer: string;
  latency_ms: number;
  cost_usd: number | null;
  source_status?: string | null;
  available: boolean;
}

export interface QualityLabRun {
  run_id: string;
  dataset_id: string;
  holdout: boolean;
  holdout_verified: boolean;
  can_apply: boolean;
  can_rollback: boolean;
  created_at: string;
  input: { claim: string; context: string; allowed_sources: string[] };
  candidates: QualityLabCandidate[];
  blind_order: ("A" | "B")[];
}

export interface QualityLabRunRequest {
  claim: string;
  context: string;
  allowed_sources: string[];
  dataset_id?: string;
  holdout?: boolean;
  model_ids: string[];
  prompt_variants?: string[];
}

export const runQualityLab = (payload: QualityLabRunRequest) =>
  request<QualityLabRun>("/quality-lab/runs", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const submitQualityLabRating = (
  runId: string,
  payload: Record<string, unknown>,
) =>
  request<{ saved: boolean; agreement: number | null }>(
    `/quality-lab/runs/${encodeURIComponent(runId)}/ratings`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );

export const applyQualityLabVariant = (runId: string, variantId: string) =>
  request<{ applied: boolean; run_id: string; variant_id: string }>(
    `/quality-lab/runs/${encodeURIComponent(runId)}/apply`,
    {
      method: "POST",
      body: JSON.stringify({ variant_id: variantId }),
    },
  );

export const rollbackQualityLab = (runId: string) =>
  request<{ rolled_back: boolean; run_id: string }>(
    `/quality-lab/runs/${encodeURIComponent(runId)}/rollback`,
    { method: "POST" },
  );

// Video-evaluation UI contract. A backend can implement these routes without
// coupling the desktop UI to its worker or evidence persistence details.
export type VideoEvalJobStatus =
  | "queued"
  | "processing"
  | "awaiting_consent"
  | "completed"
  | "failed"
  | "cancelled";
export interface VideoEvalJob {
  id: string;
  url: string;
  status: VideoEvalJobStatus;
  progress?: number;
  step?: string;
  error?: string | null;
  has_subtitles?: boolean;
  consent_required?: boolean;
  artifact_available?: boolean;
}

export const createVideoEvalJob = (url: string) =>
  request<VideoEvalJob>("/video-eval/jobs", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
export const getVideoEvalJob = (id: string) =>
  request<VideoEvalJob>(`/video-eval/jobs/${encodeURIComponent(id)}`);
export const consentVideoEvalJob = (id: string, approved: boolean) =>
  request<VideoEvalJob>(`/video-eval/jobs/${encodeURIComponent(id)}/consent`, {
    method: "POST",
    body: JSON.stringify({ approved }),
  });
export const cancelVideoEvalJob = (id: string) =>
  request<VideoEvalJob>(`/video-eval/jobs/${encodeURIComponent(id)}/cancel`, {
    method: "POST",
  });
export const getVideoEvalArtifact = (id: string) =>
  request<Record<string, unknown>>(
    `/video-eval/jobs/${encodeURIComponent(id)}/artifact`,
  );
