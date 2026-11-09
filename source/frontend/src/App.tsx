import { lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import Layout from "./components/Layout";
import AppOverlays from "./components/AppOverlays";
import DebateOverlay from "./components/DebateOverlay";
import type { AdminTab } from "./components/ManagementView";
import WelcomeView from "./components/WelcomeView";
import PreCallView from "./components/PreCall/PreCallView";
import ActiveCallView from "./components/ActiveCall/ActiveCallView";
import { SILENT_AUDIO_LEVEL, startSingleFlight, useAudioCapture } from "./hooks/useAudioCapture";
import { useWebSocket } from "./hooks/useWebSocket";
import { reconcileRefusedSession, useSession } from "./hooks/useSession";
import { useSpeechRecognition } from "./hooks/useSpeechRecognition";
import { useAppUpdates } from "./hooks/useAppUpdates";
import { useModelDownloads } from "./hooks/useModelDownloads";
import { useConfirm } from "./components/ConfirmProvider";
import * as api from "./services/api";
import { parseSavedDrainSummary } from "./lib/postProcessingSummary";
import { resolveStoredAskModel } from "./lib/askModelSelection";
import { updateInterimText } from "./lib/interimTranscript";
import { shouldResetMessageCursor } from "./lib/wsEventStream";
import { hideActiveProvisionalRevisions, shouldRecoverTranscriptsFromStatus } from "./lib/sessionRefresh";
import { webProviderStartupNeedsAttention } from "./lib/providerOnboarding";
import { DE } from "./i18n/de";
import {
  emptyDebateState,
  reduceDebateUpdate,
} from "./lib/debateRecommendation";
import type { AgentActivitySnapshot, DebateSettings, ModelInfo, PostProcessingProgress, Question, Session, SessionGroup, SessionSynthesis, StopDrainMode, TranscriptEntry, WSStatusData } from "./types";

const embeddedDesktop = new URLSearchParams(window.location.search).get("desktop") === "1";
const ManagementView = lazy(() => import("./components/ManagementView"));
const PostCallView = lazy(() => import("./components/PostCall/PostCallView"));

function idlePostProcessing(): PostProcessingProgress {
  return {
    active: false,
    state: "idle",
    stage: "",
    message: "",
    currentStep: 0,
    totalSteps: 5,
    progress: 0,
    startedAt: null,
    completedAt: null,
    confirmed: false,
  };
}

function startPostProcessing(): PostProcessingProgress {
  return {
    active: true,
    state: "running",
    stage: "stopping_audio",
    message: "Audioaufnahme wird beendet ...",
    currentStep: 0,
    totalSteps: 5,
    progress: 5,
    startedAt: new Date().toISOString(),
    completedAt: null,
    confirmed: false,
  };
}

function progressFromStatus(prev: PostProcessingProgress, data: WSStatusData): PostProcessingProgress {
  return {
    active: true,
    state: "running",
    stage: data.stage ?? prev.stage,
    message: data.message || prev.message,
    currentStep: data.current_step ?? prev.currentStep,
    totalSteps: data.total_steps ?? prev.totalSteps,
    progress: data.progress ?? prev.progress,
    startedAt: prev.startedAt ?? new Date().toISOString(),
    completedAt: null,
    confirmed: false,
    steps: data.steps ?? prev.steps,
    details: data.details ?? prev.details,
  };
}

function completePostProcessing(
  prev: PostProcessingProgress,
  message = "Nachbereitung abgeschlossen",
  details?: Record<string, unknown>,
): PostProcessingProgress {
  return {
    ...prev,
    active: false,
    state: "completed",
    stage: "complete",
    message,
    currentStep: prev.totalSteps,
    progress: 100,
    completedAt: new Date().toISOString(),
    confirmed: true,
    details: details ?? prev.details,
  };
}

function backgroundPostProcessing(prev: PostProcessingProgress): PostProcessingProgress {
  // The backend went quiet but never hung up, so the call is most likely still
  // finishing. Say that, rather than implying the recording was lost and
  // offering to resume a call the user just ended (ALP-171).
  return {
    ...prev,
    active: false,
    state: "background",
    message:
      "Die Nachbereitung läuft im Hintergrund weiter. Du kannst diese Seite verlassen; "
      + DE.live.backgroundCompletion,
    progress: Math.max(prev.progress, 90),
    completedAt: null,
    confirmed: false,
  };
}

// A drain that outlived the client's patience is still bounded work, so poll
// briefly rather than forever, and stop the moment it lands.
const BACKGROUND_POLL_INTERVAL_MS = 5000;
const BACKGROUND_POLL_ATTEMPTS = 60;

function unconfirmedPostProcessing(prev: PostProcessingProgress): PostProcessingProgress {
  return {
    ...prev,
    active: false,
    state: "timeout",
    message: "Der Abschluss der Nachbearbeitung wurde nicht bestätigt. Beende das Gespräch erneut oder aktualisiere die Ansicht.",
    progress: Math.max(prev.progress, 90),
    completedAt: null,
    confirmed: false,
  };
}

function transcriptKey(entry: TranscriptEntry): string {
  if (entry.id) return `id:${entry.id}`;
  if (entry.sequence !== undefined) return `seq:${entry.session_id || ""}:${entry.sequence}`;
  return `raw:${entry.timestamp}:${entry.speaker_id || ""}:${entry.text}`;
}

function mergeTranscripts(...groups: TranscriptEntry[][]): TranscriptEntry[] {
  const seen = new Set<string>();
  const merged: TranscriptEntry[] = [];
  for (const group of groups) {
    for (const entry of group) {
      const key = transcriptKey(entry);
      if (seen.has(key)) continue;
      seen.add(key);
      merged.push(entry);
    }
  }
  return merged.sort((a, b) => {
    if (a.sequence !== undefined && b.sequence !== undefined) return a.sequence - b.sequence;
    return new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
  });
}

function mergeQuestions(primary: Question[], secondary: Question[]): Question[] {
  const seen = new Set<string>();
  const merged: Question[] = [];
  for (const group of [primary, secondary]) {
    for (const question of group) {
      if (seen.has(question.id)) continue;
      seen.add(question.id);
      merged.push(question);
    }
  }
  return merged;
}

function synthesisTime(synthesis: SessionSynthesis | null): number {
  if (!synthesis) return 0;
  return new Date(synthesis.updated_at || synthesis.created_at).getTime();
}

function newestSynthesis(
  mode: "live" | "post_call",
  ...items: (SessionSynthesis | null)[]
): SessionSynthesis | null {
  return items
    .filter((item): item is SessionSynthesis => item?.mode === mode)
    .sort((a, b) => synthesisTime(b) - synthesisTime(a))[0] || null;
}

function errorMessage(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}

function delay(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function MainApp() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [groups, setGroups] = useState<SessionGroup[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [runtimeSessionId, setRuntimeSessionId] = useState<string | null>(null);
  const [liveSessionId, setLiveSessionId] = useState<string | null>(null);
  const [showOfferings, setShowOfferings] = useState(false);
  const [showKnowledge, setShowKnowledge] = useState(false);
  const modelDownloads = useModelDownloads();
  const [showAdmin, setShowAdmin] = useState(false);
  const [adminTab, setAdminTab] = useState<AdminTab>("agents");
  // True only while Admin was opened from the welcome checklist's "Add API
  // key" action; gates the contextual first-run setup card on the keys tab.
  const [adminOnboarding, setAdminOnboarding] = useState(false);
  const [showNewSession, setShowNewSession] = useState(false);
  const {
    whatsNew,
    bannerOpen,
    acknowledge: acknowledgeWhatsNew,
    desktopUpdate,
  } = useAppUpdates();
  const { confirm, notice } = useConfirm();

  const {
    session,
    directives,
    documents,
    questions: savedQuestions,
    segments,
    speakers,
    transcripts: savedTranscripts,
    synthesis: savedSynthesis,
    liveSynthesis: savedLiveSynthesis,
    refreshSession,
    refreshDirectives,
    refreshDocuments,
    refreshQuestions,
    refreshSegments,
    refreshSpeakers,
    refreshTranscripts,
    refreshSynthesis,
  } = useSession(activeSessionId);

  const { startCapture, stopCapture, isCapturing, audioLevelRef, systemAudioLevelRef, systemAudioActive, systemAudioWarning } = useAudioCapture();
  const [nativeAudioActive, setNativeAudioActive] = useState(false);
  const [nativeSystemAudioActive, setNativeSystemAudioActive] = useState(false);
  const nativeMicLevelRef = useRef(0);
  const nativeSystemAudioLevelRef = useRef(0);
  const [captureSystemAudio, setCaptureSystemAudio] = useState(true);
  const { connect, disconnect, sendAudio, sendDirective, sendDebateResearch, sendDebateResearchControl, sendDebateAnalysisCancel, sendDebateUpdateAck, sendDebateAnswerGood, sendTrackState, sendStop, acknowledgeMessages, status, messages, audioStats } =
    useWebSocket();
  const { stopListening } = useSpeechRecognition();

  const [liveQuestions, setLiveQuestions] = useState<Question[]>([]);
  const [liveTranscripts, setLiveTranscripts] = useState<TranscriptEntry[]>([]);
  // Rewrites from the transcript refiner, by entry id. Applied over both the
  // saved and the live lists, because the saved copy of a row would
  // otherwise shadow the refined live one in mergeTranscripts.
  const [refinedEntries, setRefinedEntries] = useState<Record<string, TranscriptEntry>>({});
  const [interimText, setInterimText] = useState("");
  const interimSegmentRevisionsRef = useRef<Record<string, number>>({});
  const [runtimeSynthesis, setRuntimeSynthesis] = useState<SessionSynthesis | null>(null);
  const [runtimeActivity, setRuntimeActivity] = useState<AgentActivitySnapshot | null>(null);
  const [debateState, setDebateState] = useState(() => emptyDebateState());

  useEffect(() => {
    const visible = debateState.recommendation;
    if (!visible?.claim_id || !visible.recommendation_revision) return;
    const frame = window.requestAnimationFrame(() => {
      sendDebateUpdateAck(visible.claim_id, visible.recommendation_revision);
    });
    return () => window.cancelAnimationFrame(frame);
  }, [
    debateState.recommendation?.claim_id,
    debateState.recommendation?.recommendation_revision,
    sendDebateUpdateAck,
  ]);
  const [processingTranscript, setProcessingTranscript] = useState(false);
  const [processingError, setProcessingError] = useState<string | null>(null);
  const [backendAudioStatus, setBackendAudioStatus] = useState<string | null>(null);
  const [captureError, setCaptureError] = useState<string | null>(null);
  const [startError, setStartError] = useState<string | null>(null);
  const [audioStarting, setAudioStarting] = useState(false);
  const [callStarting, setCallStarting] = useState(false);
  // Track when the current call segment started (resets on each start/resume)
  const [callSegmentStart, setCallSegmentStart] = useState<string | null>(null);
  const [postProcessing, setPostProcessing] = useState<PostProcessingProgress>(() => idlePostProcessing());
  // True from the moment End Call is pressed until the post-call data has
  // landed. The socket closes early in that window, and without this the
  // still-mounted active view reads that as a lost connection (ALP-171).
  const [endingCall, setEndingCall] = useState(false);
  // In-call chat ("ask this call anything"): the question text stays visible
  // once asked, even on failure, so it never disappears without explanation;
  // pendingAsk only clears on a successful answer (see handleAsk below).
  const [pendingAsk, setPendingAsk] = useState<string | null>(null);
  const [askError, setAskError] = useState<string | null>(null);
  const [askModels, setAskModels] = useState<ModelInfo[]>([]);
  const [askModelId, setAskModelId] = useState("");
  const [localOnly, setLocalOnly] = useState(false);
  const [debateSettings, setDebateSettings] = useState<DebateSettings | null>(null);
  const runtimeSessionIdRef = useRef(runtimeSessionId);
  const liveSessionIdRef = useRef(liveSessionId);
  const audioStartPromiseRef = useRef<Promise<void> | null>(null);
  const audioStartGenerationRef = useRef(0);
  const beginCallPromiseRef = useRef<Promise<void> | null>(null);
  const beginCallGenerationRef = useRef(0);
  runtimeSessionIdRef.current = runtimeSessionId;
  liveSessionIdRef.current = liveSessionId;

  useEffect(() => {
    api.listSessions().then(setSessions).catch(console.error);
    api.listGroups().then(setGroups).catch(console.error);
    api.getDebateSettings().then(setDebateSettings).catch(console.error);
    let cancelled = false;
    Promise.allSettled([
      api.getChatGPTWebStatus(),
      api.getGeminiWebStatus(),
    ]).then((results) => {
      if (cancelled || liveSessionIdRef.current) return;
      const providers = results.flatMap((result) => (
        result.status === "fulfilled" ? [result.value] : []
      ));
      if (!webProviderStartupNeedsAttention(providers)) return;
      // Open only Backchannel's in-app connection page. External login pages
      // remain behind the explicit provider buttons.
      setAdminTab("keys");
      setAdminOnboarding(false);
      setShowAdmin(true);
      setShowOfferings(false);
      setShowKnowledge(false);
      setActiveSessionId(null);
    });
    return () => { cancelled = true; };
  }, []);

  const handleDebateResearchControl = useCallback(async (enabled: boolean) => {
    const previous = debateSettings;
    if (previous) setDebateSettings({ ...previous, research_enabled: enabled });
    sendDebateResearchControl(enabled);
    try {
      setDebateSettings(await api.updateDebateSettings({ research_enabled: enabled }));
    } catch (error) {
      if (previous) setDebateSettings(previous);
      sendDebateResearchControl(previous?.research_enabled ?? false);
      console.error(error);
    }
  }, [debateSettings, sendDebateResearchControl]);

  // Process incoming WebSocket messages — questions and transcripts
  const processedSequenceRef = useRef(0);
  const processedLegacyCountRef = useRef(0);
  const processedMessageSessionRef = useRef("");
  const transcriptRefreshInFlightRef = useRef<Promise<void> | null>(null);
  const recoverCurrentTranscripts = useCallback(() => {
    if (transcriptRefreshInFlightRef.current) return;
    const pending = refreshTranscripts();
    transcriptRefreshInFlightRef.current = pending;
    void pending.finally(() => {
      if (transcriptRefreshInFlightRef.current === pending) {
        transcriptRefreshInFlightRef.current = null;
      }
    });
  }, [refreshTranscripts]);
  useEffect(() => {
    const messageSessionId = liveSessionIdRef.current ?? runtimeSessionIdRef.current ?? "";
    // A stopped call keeps useWebSocket's acknowledged buffer for Resume.
    // Do not erase its session identity during the no-runtime render between
    // End/Disconnect and Resume; reset only when a different real session is active.
    if (shouldResetMessageCursor(messageSessionId, processedMessageSessionRef.current)) {
      processedMessageSessionRef.current = messageSessionId;
      processedSequenceRef.current = 0;
      processedLegacyCountRef.current = 0;
    }
    const sequencedMessages = messages.filter((message) => (
      typeof message.session_sequence === "number"
      && message.session_sequence > processedSequenceRef.current
    ));
    const legacyMessages = messages
      .filter((message) => typeof message.session_sequence !== "number")
      .slice(processedLegacyCountRef.current);
    const newMessages = [...sequencedMessages, ...legacyMessages];
    for (const msg of newMessages) {
      if (msg.type === "question") {
        const q: Question = {
          id: msg.data.id,
          session_id: messageSessionId,
          item_type: (msg.data.item_type as any) || "question",
          lens_label: msg.data.lens_label || "",
          question: msg.data.question,
          rationale: msg.data.rationale,
          source_context: msg.data.source_context,
          speaker_id: msg.data.speaker_id ?? null,
          directive_id: msg.data.directive_id,
          starred: false,
          dismissed: false,
          created_at: msg.data.timestamp,
          answered: false,
          answer_summary: "",
          needs_followup: false,
          followup_question: "",
          is_followup: msg.data.is_followup || false,
          agent_source: msg.data.agent_source,
          offering_match: msg.data.offering_match || "",
          vote: msg.data.vote ?? 0,
          enhanced: msg.data.enhanced ?? false,
        };
        setLiveQuestions((prev) => [q, ...prev]);
      } else if (msg.type === "question_answered") {
        setLiveQuestions((prev) =>
          prev.map((q) =>
            q.id === msg.data.id
              ? {
                  ...q,
                  answered: true,
                  answer_summary: msg.data.answer_summary,
                  needs_followup: msg.data.needs_followup,
                  followup_question: msg.data.followup_question,
                }
              : q
          )
        );
      } else if (msg.type === "transcript") {
        // Diarized transcript arrived from backend — clear interim text since this replaces it
        setInterimText("");
        interimSegmentRevisionsRef.current = {};
        setLiveTranscripts((prev) => [...prev, msg.data]);
        if (messageSessionId === activeSessionId) recoverCurrentTranscripts();
        if (
          messageSessionId === activeSessionId &&
          msg.data.speaker_id &&
          !speakers.some((s) => s.id === msg.data.speaker_id)
        ) {
          void refreshSpeakers();
        }
      } else if (msg.type === "transcript_updated") {
        if (msg.data.id) {
          const refined = msg.data;
          setRefinedEntries((prev) => ({ ...prev, [refined.id as string]: refined }));
          // Recover the durable base row if this update arrived in a compact
          // reconnect snapshot before the current view had loaded it.
          if (messageSessionId === activeSessionId) recoverCurrentTranscripts();
        }
      } else if (msg.type === "interim_transcript") {
        const segmentId = msg.data.segment_id || "legacy";
        const segmentRevision = msg.data.segment_revision || 0;
        const previousRevision = interimSegmentRevisionsRef.current[segmentId] ?? -1;
        if (segmentRevision <= previousRevision) continue;
        interimSegmentRevisionsRef.current[segmentId] = segmentRevision;
        // Live API real-time transcription — show instantly as interim preview
        // Append new text, but cap length to avoid unbounded growth between batches
        setInterimText((prev) => updateInterimText(prev, msg.data.text, msg.data.mode));
      } else if (msg.type === "audio_level") {
        const level = Math.max(0, Math.min(1, Number(msg.data.level) || 0));
        if (msg.data.track === 1) nativeSystemAudioLevelRef.current = level;
        else nativeMicLevelRef.current = level;
      } else if (msg.type === "agent_activity") {
        setRuntimeActivity(msg.data);
      } else if (msg.type === "debate_update") {
        setDebateState((current) =>
          reduceDebateUpdate(current, messageSessionId, msg.data),
        );
      } else if (msg.type === "status") {
        if (shouldRecoverTranscriptsFromStatus(
          msg.data.state,
          messageSessionId === activeSessionId,
        )) {
          recoverCurrentTranscripts();
        }
        if (msg.data.state === "post_processing" || msg.data.state === "finalizing") {
          setPostProcessing((prev) => progressFromStatus(prev, msg.data));
        } else if (msg.data.state === "completed") {
          setPostProcessing((prev) => completePostProcessing(prev, msg.data.message, msg.data.details));
        } else if (msg.data.state === "error") {
          setPostProcessing((prev) => ({
            ...prev,
            active: false,
            state: "error",
            message: msg.data.message || "Nachbereitung fehlgeschlagen.",
            completedAt: null,
            confirmed: false,
          }));
        } else if (msg.data.state === "transcription_unready") {
          // Backend refused the call and closed the socket. Undo the
          // optimistic start so the session is not stranded active with no
          // call segment, and surface the reason in both views.
          setStartError(msg.data.message);
          setCaptureError(msg.data.message);
          stopCapture();
          disconnect();
          liveSessionIdRef.current = null;
          setLiveSessionId(null);
          setInterimText("");
          const refusedSessionId = messageSessionId || activeSessionId;
          const refusalMessage = msg.data.message;
          if (refusedSessionId) {
            void (async () => {
              const problem = await reconcileRefusedSession(
                refusedSessionId,
                savedTranscripts.length,
                { getSession: api.getSession, updateSession: api.updateSession },
              );
              if (problem) {
                setStartError(
                  `${refusalMessage} (Die Sitzung konnte nicht automatisch zurückgesetzt werden: ` +
                    `${problem} — ${DE.live.reloadIfActive})`,
                );
              }
              await refreshSession().catch((err) =>
                console.error("Session refresh after refused call failed", err),
              );
              await api
                .listSessions()
                .then(setSessions)
                .catch((err) =>
                  console.error("Session list refresh after refused call failed", err),
                );
            })();
          }
        } else if (msg.data.state === "transcription_error") {
          setCaptureError(msg.data.message);
        } else if (
          msg.data.state === "audio_received" ||
          msg.data.state === "audio_segment" ||
          msg.data.state === "transcript_saved"
        ) {
          setBackendAudioStatus(msg.data.message);
        }
      } else if (msg.type === "insight_updated" || msg.type === "insight_elevated") {
        const d = msg.data;
        setLiveQuestions((prev) => {
          const exists = prev.some((q) => q.id === d.id);
          if (exists) {
            return prev.map((q) =>
              q.id === d.id
                ? {
                    ...q,
                    item_type: d.item_type || q.item_type,
                    lens_label: d.lens_label ?? q.lens_label,
                    question: d.question || q.question,
                    rationale: d.rationale || q.rationale,
                    source_context: d.source_context || q.source_context,
                    speaker_id: d.speaker_id ?? q.speaker_id,
                    answered: d.answered ?? q.answered,
                    answer_summary: d.answer_summary || q.answer_summary,
                    needs_followup: d.needs_followup ?? q.needs_followup,
                    followup_question: d.followup_question || q.followup_question,
                    dismissed: d.dismissed ?? q.dismissed,
                    enrichment_notes: d.enrichment_notes || q.enrichment_notes,
                    revision_count: d.revision_count ?? q.revision_count,
                    updated_at: d.updated_at || new Date().toISOString(),
                    agent_source: d.agent_source || q.agent_source,
                    offering_match: d.offering_match || q.offering_match,
                    vote: d.vote ?? q.vote,
                    enhanced: d.enhanced ?? q.enhanced,
                  }
                : q
            );
          }
          return prev;
        });
      } else if (msg.type === "synthesis_updated") {
        setRuntimeSynthesis(msg.data);
      }
    }
    if (sequencedMessages.length) {
      processedSequenceRef.current = Math.max(
        processedSequenceRef.current,
        ...sequencedMessages.map((message) => message.session_sequence || 0),
      );
    }
    processedLegacyCountRef.current += legacyMessages.length;
    acknowledgeMessages(newMessages);
  }, [messages, activeSessionId, speakers, refreshSpeakers, recoverCurrentTranscripts, stopCapture, disconnect, savedTranscripts.length, refreshSession, acknowledgeMessages]);

  // Live Ask is its own explicit choice. Preserve a valid per-session choice,
  // but never borrow an agent row or silently pick the first text model.
  useEffect(() => {
    if (!session) return;
    const storageKey = `backchannel:ask-model:${session.id}`;
    api.listModels()
      .then((allModels) => {
        const textModels = allModels.filter((m) => m.supports_text);
        setAskModels(textModels);
        const stored = window.localStorage.getItem(storageKey);
        setAskModelId(resolveStoredAskModel(stored, textModels));
      })
      .catch(() => {});
  }, [session?.id, showAdmin]);

  // Fetched once at mount: a stale value only affects which rows the model
  // chip greys out, since the backend enforces Privacy First regardless.
  useEffect(() => {
    api.getPrivacyConfig().then((cfg) => setLocalOnly(cfg.local_only)).catch(() => {});
  }, []);

  const runtimeMatchesView = Boolean(activeSessionId && activeSessionId === runtimeSessionId);
  const viewLiveQuestions = runtimeMatchesView ? liveQuestions : [];
  const viewLiveTranscripts = runtimeMatchesView ? liveTranscripts : [];
  const viewRuntimeSynthesis = runtimeMatchesView ? runtimeSynthesis : null;
  const viewRuntimeActivity = runtimeMatchesView ? runtimeActivity : null;
  const viewDebateRecommendation =
    runtimeMatchesView && debateState.sessionId === runtimeSessionId
      ? debateState.recommendation
      : null;

  const allQuestions = runtimeMatchesView
    ? session?.state === "completed"
      ? mergeQuestions(savedQuestions, viewLiveQuestions)
      : mergeQuestions(viewLiveQuestions, savedQuestions)
    : savedQuestions;

  const visibleSavedTranscripts = hideActiveProvisionalRevisions(
    savedTranscripts,
    new Set(Object.keys(interimSegmentRevisionsRef.current)),
  );
  const persistedAndLiveTranscripts = mergeTranscripts(visibleSavedTranscripts, viewLiveTranscripts).map((entry) =>
    entry.id && refinedEntries[entry.id] ? { ...entry, ...refinedEntries[entry.id] } : entry,
  );

  // Combine final transcripts + current interim for display
  const displayTranscripts: TranscriptEntry[] = [
    ...persistedAndLiveTranscripts,
    ...(runtimeMatchesView && interimText
      ? [{ text: interimText, timestamp: new Date().toISOString() }]
      : []),
  ];
  const reviewTranscripts = persistedAndLiveTranscripts;
  const liveSynthesis = newestSynthesis("live", savedLiveSynthesis, viewRuntimeSynthesis);
  const postCallSynthesis = newestSynthesis("post_call", savedSynthesis, viewRuntimeSynthesis);
  const openSegmentStart = [...segments]
    .reverse()
    .find((segment) => !segment.ended_at)?.started_at ?? null;
  const viewedCallSegmentStart = runtimeMatchesView
    ? callSegmentStart ?? openSegmentStart ?? session?.started_at ?? null
    : openSegmentStart ?? session?.started_at ?? null;

  const refreshSessions = useCallback(async () => {
    const s = await api.listSessions();
    setSessions(s);
  }, []);

  const refreshGroups = useCallback(async () => {
    const g = await api.listGroups();
    setGroups(g);
  }, []);

  const resetSessionRuntimeState = useCallback(() => {
    runtimeSessionIdRef.current = null;
    liveSessionIdRef.current = null;
    setRuntimeSessionId(null);
    setLiveSessionId(null);
    setLiveQuestions([]);
    setLiveTranscripts([]);
    setInterimText("");
    setRuntimeSynthesis(null);
    setRuntimeActivity(null);
    setDebateState(emptyDebateState());
    setProcessingTranscript(false);
    setProcessingError(null);
    setBackendAudioStatus(null);
    setCaptureError(null);
    setCallSegmentStart(null);
    setPostProcessing(idlePostProcessing());
    setPendingAsk(null);
    setAskError(null);
    processedSequenceRef.current = Math.max(
      0,
      ...messages.map((message) => message.session_sequence || 0),
    );
    processedLegacyCountRef.current = messages.filter(
      (message) => typeof message.session_sequence !== "number",
    ).length;
  }, [messages]);

  const handleNewSession = useCallback(() => {
    setShowNewSession(true);
  }, []);

  const handleCreateSession = useCallback(async (name: string, meetingType: Session["meeting_type"]) => {
    const s = await api.createSession(name, { meeting_type: meetingType });
    await refreshSessions();
    if (!liveSessionIdRef.current) resetSessionRuntimeState();
    setActiveSessionId(s.id);
    setShowNewSession(false);
    setShowOfferings(false);
    setShowKnowledge(false);
    setShowAdmin(false);
  }, [refreshSessions, resetSessionRuntimeState]);

  const handleSelectSession = useCallback((id: string) => {
    if (!liveSessionIdRef.current) resetSessionRuntimeState();
    setActiveSessionId(id);
    setShowOfferings(false);
    setShowKnowledge(false);
    setShowAdmin(false);
  }, [resetSessionRuntimeState]);

  const handleOpenOfferings = useCallback(() => {
    if (!liveSessionIdRef.current) resetSessionRuntimeState();
    setShowOfferings(true);
    setShowKnowledge(false);
    setShowAdmin(false);
    setActiveSessionId(null);
  }, [resetSessionRuntimeState]);

  const handleOpenKnowledge = useCallback(() => {
    if (!liveSessionIdRef.current) resetSessionRuntimeState();
    setShowKnowledge(true);
    setShowOfferings(false);
    setShowAdmin(false);
    setActiveSessionId(null);
  }, [resetSessionRuntimeState]);

  const openAdmin = useCallback((tab: AdminTab = "agents", onboarding = false, preserveSession = false) => {
    if (!liveSessionIdRef.current) resetSessionRuntimeState();
    setAdminTab(tab);
    setAdminOnboarding(onboarding);
    setShowAdmin(true);
    setShowOfferings(false);
    setShowKnowledge(false);
    if (!preserveSession) setActiveSessionId(null);
  }, [resetSessionRuntimeState]);

  const handleOpenAdmin = useCallback(() => openAdmin(), [openAdmin]);

  const handleOpenEnhancementAgents = useCallback(
    () => openAdmin("agents", false, true),
    [openAdmin],
  );

  const handleOpenApiKeys = useCallback(() => openAdmin("keys", true), [openAdmin]);

  // "Continue to first session" from the onboarding setup card: leave Admin
  // and drop straight into the new-session flow.
  const handleOnboardingContinue = useCallback(() => {
    setShowAdmin(false);
    setAdminOnboarding(false);
    setShowNewSession(true);
  }, []);

  const handleOpenVoiceSettings = useCallback(
    () => openAdmin("transcription"),
    [openAdmin],
  );

  const handleRenameSession = useCallback(async (name: string) => {
    if (!activeSessionId) return;
    await api.updateSession(activeSessionId, { name });
    await refreshSession();
    await refreshSessions();
  }, [activeSessionId, refreshSession, refreshSessions]);

  const handleUpdateSessionContext = useCallback(async (data: { meeting_type?: Session["meeting_type"]; meeting_context?: string }) => {
    if (!activeSessionId) return;
    await api.updateSession(activeSessionId, data);
    await refreshSession();
    await refreshSessions();
  }, [activeSessionId, refreshSession, refreshSessions]);

  const handleDeleteSession = useCallback(async () => {
    if (!activeSessionId) return;
    if (activeSessionId === liveSessionIdRef.current) {
      await notice({
        title: "Gespräch läuft",
        message: "Beende das aktive Gespräch, bevor du diese Sitzung löschst.",
      });
      return;
    }
    const ok = await confirm({
      title: "Gespräch löschen",
      message: "Dieses Gespräch und alle zugehörigen Daten unwiderruflich löschen?",
      confirmLabel: "Löschen",
      tone: "danger",
    });
    if (!ok) return;
    await api.deleteSession(activeSessionId);
    setActiveSessionId(null);
    if (!liveSessionIdRef.current) resetSessionRuntimeState();
    await refreshSessions();
  }, [activeSessionId, confirm, notice, refreshSessions, resetSessionRuntimeState]);

  const handleDeleteSessionById = useCallback(async (sessionId: string) => {
    if (sessionId === liveSessionIdRef.current) {
      await notice({
        title: "Gespräch läuft",
        message: "Beende das aktive Gespräch, bevor du diese Sitzung löschst.",
      });
      return;
    }
    await api.deleteSession(sessionId);
    if (sessionId === activeSessionId) {
      setActiveSessionId(null);
      if (!liveSessionIdRef.current) resetSessionRuntimeState();
    }
    await refreshSessions();
  }, [activeSessionId, notice, refreshSessions, resetSessionRuntimeState]);

  const startAudioFeed = useCallback((
    sessionId: string,
    reconnect = false,
  ) => startSingleFlight(audioStartPromiseRef, async () => {
    const generation = ++audioStartGenerationRef.current;
    setAudioStarting(true);
    setCaptureError(null);

    try {
      if (
        generation !== audioStartGenerationRef.current
        || liveSessionIdRef.current !== sessionId
      ) return;
      if (reconnect || status !== "connected") {
        connect(sessionId);
        await delay(500);
      }
      if (
        generation !== audioStartGenerationRef.current
        || liveSessionIdRef.current !== sessionId
      ) return;

      // The desktop build captures both tracks through Windows WASAPI. Keep
      // browser capture only as the web-development fallback.
      const nativeAvailability = await api.getNativeAudioStatus().catch(() => null);
      if (nativeAvailability?.available) {
        nativeMicLevelRef.current = 0;
        nativeSystemAudioLevelRef.current = 0;
        let nativeStatus = null;
        let nativeError: unknown = null;
        for (let attempt = 0; attempt < 3; attempt++) {
          try {
            let storedDevices = {};
            try {
              storedDevices = JSON.parse(window.localStorage.getItem("backchannel:audio-devices") || "{}");
            } catch {
              window.localStorage.removeItem("backchannel:audio-devices");
            }
            nativeStatus = await api.startNativeAudio(sessionId, captureSystemAudio, storedDevices);
            break;
          } catch (err) {
            nativeError = err;
            if (attempt < 2) await delay(250);
          }
        }
        if (!nativeStatus?.active) throw nativeError ?? new Error("Native Audioaufnahme konnte nicht gestartet werden.");
        setNativeAudioActive(true);
        setNativeSystemAudioActive(nativeStatus.system_audio_active);
        return;
      }
      if (embeddedDesktop) {
        throw new Error("Die native Windows-Audioaufnahme ist nicht verfügbar. Browser-Audio wird in der Desktop-App nicht verwendet.");
      }
      setNativeAudioActive(false);
      setNativeSystemAudioActive(false);
      await startCapture((chunk, track) => {
        sendAudio(chunk, track);
      }, undefined, {
        systemAudio: captureSystemAudio,
        onSystemAudioStateChange: (active) => sendTrackState(1, active),
      });
    } catch (err) {
      if (generation !== audioStartGenerationRef.current) return;
      const message = errorMessage(err, "Die Audioaufnahme ist fehlgeschlagen.");
      setCaptureError(message);
      console.error("Failed to start audio capture", err);
      throw err;
    } finally {
      if (generation === audioStartGenerationRef.current) {
        setAudioStarting(false);
      }
      return true;
    }
  }), [connect, sendAudio, sendTrackState, startCapture, status, captureSystemAudio]);

  const beginCall = useCallback(() => {
    if (!activeSessionId) return Promise.resolve();
    const sessionId = activeSessionId;
    if (liveSessionIdRef.current && liveSessionIdRef.current !== sessionId) {
      return notice({
        title: "Gespräch läuft",
        message: "Beende das aktuelle Gespräch, bevor du eine andere Sitzung startest.",
      });
    }

    return startSingleFlight(beginCallPromiseRef, async () => {
      const generation = ++beginCallGenerationRef.current;
      const isCurrent = () => generation === beginCallGenerationRef.current;
      setCallStarting(true);
      setStartError(null);

      try {
        // A call without a usable batch transcriber saves zero transcript
        // rows; block Start/Resume up front with the actionable reason. If
        // the check itself fails the websocket-level gate still refuses.
        const readiness = await api.getTranscriptionReadiness().catch(() => null);
        if (!isCurrent()) return;
        if (readiness && !readiness.ready) {
          setStartError(readiness.reason);
          return;
        }

        // Create defaults before publishing the active view, and only once.
        if (speakers.length === 0) {
          await api.createSpeaker(sessionId, { name: "Ich / Teammitglied", role: "", color: "#0d9488", is_user: true, speaker_type: "team" });
          if (!isCurrent()) return;
          await api.createSpeaker(sessionId, { name: "Teilnehmer 1", role: "", color: "#f59e0b", is_user: false, speaker_type: "external" });
          if (!isCurrent()) return;
          await refreshSpeakers();
        }
        if (!isCurrent()) return;

        await api.updateSession(sessionId, { state: "active" });
        if (!isCurrent()) return;

        runtimeSessionIdRef.current = sessionId;
        liveSessionIdRef.current = sessionId;
        setRuntimeSessionId(sessionId);
        setLiveSessionId(sessionId);
        setLiveQuestions([]);
        setLiveTranscripts([]);
        setInterimText("");
        setRuntimeSynthesis(null);
        setRuntimeActivity(null);
        setDebateState(emptyDebateState(sessionId));
        setProcessingTranscript(false);
        setProcessingError(null);
        setBackendAudioStatus(null);
        setCaptureError(null);
        setCallSegmentStart(new Date().toISOString());
        setPostProcessing(idlePostProcessing());
        setPendingAsk(null);
        setAskError(null);
        const reusingBufferedMessages = processedMessageSessionRef.current === sessionId;
        processedMessageSessionRef.current = sessionId;
        if (!reusingBufferedMessages) {
          processedSequenceRef.current = 0;
          processedLegacyCountRef.current = 0;
        }

        // Start capture before the active view exposes Resume and End.
        await startAudioFeed(sessionId, true);
        if (!isCurrent()) return;
        await Promise.all([refreshSession(), refreshSessions()]);
      } catch (err) {
        if (!isCurrent()) return;
        await api.updateSession(sessionId, { state: "pre_call" }).catch(() => undefined);
        stopCapture();
        await api.stopNativeAudio().catch(() => undefined);
        disconnect();
        liveSessionIdRef.current = null;
        setLiveSessionId(null);
        setRuntimeSessionId(null);
        const message = errorMessage(err, "Das Gespräch konnte nicht gestartet werden.");
        setCaptureError(message);
        console.error("Failed to start call", err);
      } finally {
        if (isCurrent()) setCallStarting(false);
      }
    });
  }, [activeSessionId, disconnect, notice, refreshSession, refreshSessions, refreshSpeakers, speakers, startAudioFeed, stopCapture]);

  const handleStartCall = useCallback(() => beginCall(), [beginCall]);

  const handleResumeAudio = useCallback(async () => {
    if (!activeSessionId || audioStarting) return;
    const reconnecting = status !== "connected" || liveSessionIdRef.current !== activeSessionId;
    if (isCapturing) {
      stopCapture();
    }
    if (nativeAudioActive) {
      await api.stopNativeAudio().catch(() => undefined);
      setNativeAudioActive(false);
      setNativeSystemAudioActive(false);
      nativeMicLevelRef.current = 0;
      nativeSystemAudioLevelRef.current = 0;
    }
    if (runtimeSessionIdRef.current !== activeSessionId) {
      setLiveQuestions([]);
      setLiveTranscripts([]);
      setInterimText("");
      setRuntimeSynthesis(null);
      setRuntimeActivity(null);
      setDebateState(emptyDebateState(activeSessionId));
    }
    runtimeSessionIdRef.current = activeSessionId;
    liveSessionIdRef.current = activeSessionId;
    setRuntimeSessionId(activeSessionId);
    setLiveSessionId(activeSessionId);
    setCallSegmentStart((current) => reconnecting ? new Date().toISOString() : current ?? new Date().toISOString());
    processedMessageSessionRef.current = activeSessionId;
    processedSequenceRef.current = Math.max(
      0,
      ...messages.map((message) => message.session_sequence || 0),
    );
    processedLegacyCountRef.current = messages.filter(
      (message) => typeof message.session_sequence !== "number",
    ).length;
    await startAudioFeed(activeSessionId, reconnecting);
  }, [activeSessionId, audioStarting, isCapturing, messages, nativeAudioActive, startAudioFeed, status, stopCapture]);

  const handleProcessTranscript = useCallback(async () => {
    if (!activeSessionId) return;
    setProcessingTranscript(true);
    setProcessingError(null);
    try {
      await api.analyzeSession(activeSessionId);
      try {
        const synthesis = await api.refreshSynthesis(activeSessionId);
        setRuntimeSynthesis(synthesis);
      } catch (err) {
        setProcessingError(errorMessage(err, "Die Transkriptanalyse wurde abgeschlossen, aber die Zusammenfassung ist fehlgeschlagen."));
      }
    } catch (err) {
      setProcessingError(errorMessage(err, "Die Transkriptanalyse ist fehlgeschlagen."));
    } finally {
      await Promise.allSettled([
        refreshSession(),
        refreshQuestions(),
        refreshSegments(),
        refreshTranscripts(),
        refreshSynthesis(),
        refreshSessions(),
      ]);
      setProcessingTranscript(false);
    }
  }, [activeSessionId, refreshSession, refreshQuestions, refreshSegments, refreshTranscripts, refreshSynthesis, refreshSessions]);

  const handleResumeCall = useCallback(async () => {
    if (!activeSessionId) return;
    await Promise.all([
      refreshQuestions(),
      refreshTranscripts(),
      refreshSegments(),
      refreshSpeakers(),
    ]);
    await beginCall();
  }, [activeSessionId, refreshQuestions, refreshTranscripts, refreshSegments, refreshSpeakers, beginCall]);

  const pollSessionCompletion = useCallback(async (sessionId: string) => {
    for (let attempt = 0; attempt < BACKGROUND_POLL_ATTEMPTS; attempt++) {
      await new Promise((r) => setTimeout(r, BACKGROUND_POLL_INTERVAL_MS));
      try {
        const latest = await api.getSession(sessionId);
        if (latest.state === "completed" && latest.ended_at) {
          setPostProcessing((prev) =>
            completePostProcessing(
              prev,
              "Nachbereitung abgeschlossen",
              parseSavedDrainSummary(latest.drain_summary) ?? prev.details,
            ),
          );
          await Promise.all([
            refreshSession(),
            refreshQuestions(),
            refreshSegments(),
            refreshSpeakers(),
            refreshTranscripts(),
            refreshSynthesis(),
            refreshSessions(),
          ]);
          return;
        }
      } catch (err) {
        console.error("Background post-processing poll failed", err);
      }
    }
  }, [refreshSession, refreshQuestions, refreshSegments, refreshSpeakers, refreshTranscripts, refreshSynthesis, refreshSessions]);

  const handleEndCall = useCallback(async (drain: StopDrainMode = "full") => {
    setEndingCall(true);
    setPostProcessing(startPostProcessing());
    beginCallGenerationRef.current += 1;
    beginCallPromiseRef.current = null;
    audioStartGenerationRef.current += 1;
    audioStartPromiseRef.current = null;
    setCallStarting(false);
    setAudioStarting(false);
    stopCapture();
    await api.stopNativeAudio().catch(() => undefined);
    setNativeAudioActive(false);
    setNativeSystemAudioActive(false);
    nativeMicLevelRef.current = 0;
    nativeSystemAudioLevelRef.current = 0;
    stopListening();
    const stopOutcome = await sendStop(drain);
    disconnect();
    liveSessionIdRef.current = null;
    setLiveSessionId(null);
    setInterimText("");

    if (activeSessionId) {
      let completionConfirmed = stopOutcome === "completed";
      if (!completionConfirmed) {
        try {
          const latestSession = await api.getSession(activeSessionId);
          completionConfirmed = latestSession.state === "completed" && !!latestSession.ended_at;
        } catch (err) {
          console.error("Failed to confirm post-processing completion", err);
        }
      }

      if (completionConfirmed) {
        setPostProcessing((prev) => completePostProcessing(prev));
      } else if (stopOutcome === "still_processing") {
        // Silence is not failure. Hand off to the post-call view and let it
        // poll; a drain this long is usually still running.
        setPostProcessing((prev) => backgroundPostProcessing(prev));
        void pollSessionCompletion(activeSessionId);
      } else {
        setPostProcessing((prev) => unconfirmedPostProcessing(prev));
      }
      try {
        await refreshSession();
        await refreshQuestions();
        await refreshSegments();
        await refreshSpeakers();
        await refreshTranscripts();
        await refreshSynthesis();
        await refreshSessions();
      } finally {
        // Always release the ending state. A failed refresh should drop the
        // user back to a normal view, never strand them on "wrapping up".
        setEndingCall(false);
      }
    } else {
      setEndingCall(false);
    }
  }, [activeSessionId, sendStop, stopCapture, stopListening, disconnect, refreshSession, refreshQuestions, refreshSegments, refreshSpeakers, refreshTranscripts, refreshSynthesis, refreshSessions, pollSessionCompletion]);

  const handleStarQuestion = useCallback(
    async (questionId: string, starred: boolean) => {
      if (!activeSessionId) return;
      await api.updateQuestion(activeSessionId, questionId, { starred });
      setLiveQuestions((prev) =>
        prev.map((q) => (q.id === questionId ? { ...q, starred } : q))
      );
      await refreshQuestions();
    },
    [activeSessionId, refreshQuestions]
  );

  const handleVoteQuestion = useCallback(
    async (questionId: string, vote: number) => {
      if (!activeSessionId) return;
      await api.updateQuestion(activeSessionId, questionId, { vote } as any);
      setLiveQuestions((prev) =>
        prev.map((q) => (q.id === questionId ? { ...q, vote } : q))
      );
      await refreshQuestions();
    },
    [activeSessionId, refreshQuestions]
  );

  const handleDismissQuestion = useCallback(
    async (questionId: string) => {
      if (!activeSessionId) return;
      await api.updateQuestion(activeSessionId, questionId, { dismissed: true });
      setLiveQuestions((prev) =>
        prev.map((q) => (q.id === questionId ? { ...q, dismissed: true } : q))
      );
      await refreshQuestions();
    },
    [activeSessionId, refreshQuestions]
  );

  const handleAddDirective = useCallback(
    async (text: string) => {
      if (!activeSessionId) return;
      if (session?.state === "active") {
        sendDirective(text);
      }
      await refreshDirectives();
    },
    [activeSessionId, session?.state, sendDirective, refreshDirectives]
  );

  const handleAsk = useCallback(
    async (question: string) => {
      // "asking" mirrors the same derived value ActiveCallView passes to
      // DirectiveBar: pendingAsk survives a failure (deviation a) so it is
      // not on its own proof an ask is still in flight; askError is.
      const asking = Boolean(pendingAsk) && !askError;
      if (!session || asking) return;
      if (!askModelId) {
        setAskError("Wähle zuerst ein Modell für Live-Fragen aus.");
        return;
      }
      const sessionId = session.id;
      setPendingAsk(question);
      setAskError(null);
      try {
        const created = await api.askSession(sessionId, askModelId, question);
        // The runtime session moved on (End Call + a new session started,
        // or this tab never attached one at all - a refresh or a second tab
        // leaves runtimeSessionId null while session.state is still
        // "active"): this answer belongs to session `sessionId`, not
        // whatever session is live now. It is already saved there, so clear
        // pendingAsk rather than leaving it stuck forever and silently
        // eating every later question (ALP-178).
        if (runtimeSessionIdRef.current !== sessionId) {
          setPendingAsk(null);
          setAskError("Die Antwort wurde beim ursprünglichen Gespräch gespeichert.");
          return;
        }
        setLiveQuestions((prev) => [created, ...prev]);
        setPendingAsk(null);
        setAskError(null);
      } catch (err) {
        if (runtimeSessionIdRef.current !== sessionId) {
          setPendingAsk(null);
          setAskError("Die Antwort wurde beim ursprünglichen Gespräch gespeichert.");
          return;
        }
        // Keep the question visible next to the error: it must not vanish
        // silently, only a fresh ask (handleAsk) clears it.
        setAskError(errorMessage(err, "Frage fehlgeschlagen"));
      }
    },
    [session, askModelId, pendingAsk, askError]
  );

  const handleAskModelChange = useCallback((id: string) => {
    setAskModelId(id);
    if (session) window.localStorage.setItem(`backchannel:ask-model:${session.id}`, id);
  }, [session]);

  const handleMakeDirective = useCallback(
    (question: Question) => {
      void handleAddDirective(question.question);
    },
    [handleAddDirective]
  );

  const renderContent = () => {
    if (showAdmin || showOfferings || showKnowledge) {
      return (
        <ManagementView
          showAdmin={showAdmin}
          showOfferings={showOfferings}
          showKnowledge={showKnowledge}
          adminTab={adminTab}
          adminOnboarding={adminOnboarding}
          highlightSince={whatsNew?.since ?? null}
          desktopUpdate={desktopUpdate}
          onCloseAdmin={() => setShowAdmin(false)}
          onCloseOfferings={() => setShowOfferings(false)}
          onCloseKnowledge={() => setShowKnowledge(false)}
          onAdminOnboardingContinue={handleOnboardingContinue}
          onAdminTabChange={setAdminTab}
        />
      );
    }

    if (!session) {
      return (
        <WelcomeView
          hasSessions={sessions.length > 0}
          onNewSession={handleNewSession}
          onOpenApiKeys={handleOpenApiKeys}
        />
      );
    }

    switch (session.state) {
      case "pre_call":
        return (
          <PreCallView
            session={session}
            directives={directives}
            documents={documents}
            speakers={speakers}
            transcriptCount={savedTranscripts.length}
            processingTranscript={processingTranscript}
            processingError={processingError}
            startError={startError}
            isStarting={callStarting}
            onStartCall={handleStartCall}
            onOpenVoiceSettings={handleOpenVoiceSettings}
            captureSystemAudio={captureSystemAudio}
            onToggleSystemAudio={setCaptureSystemAudio}
            onProcessTranscript={handleProcessTranscript}
            onRefreshDirectives={refreshDirectives}
            onRefreshDocuments={refreshDocuments}
            onRefreshSpeakers={refreshSpeakers}
            onRefreshTranscripts={refreshTranscripts}
            onRenameSession={handleRenameSession}
            onUpdateSessionContext={handleUpdateSessionContext}
          />
        );
      case "active":
        return (
          <ActiveCallView
            ending={endingCall}
            session={session}
            questions={allQuestions}
            transcripts={displayTranscripts}
            onEndCall={handleEndCall}
            onResumeAudio={handleResumeAudio}
            onStarQuestion={handleStarQuestion}
            onDismissQuestion={handleDismissQuestion}
            onVoteQuestion={handleVoteQuestion}
            onAddDirective={handleAddDirective}
            onAsk={handleAsk}
            askModels={askModels}
            askModelId={askModelId}
            onAskModelChange={handleAskModelChange}
            localOnly={localOnly}
            pendingAsk={runtimeMatchesView ? pendingAsk : null}
            askError={runtimeMatchesView ? askError : null}
            askDisabled={!runtimeMatchesView}
            onMakeDirective={handleMakeDirective}
            audioLevel={nativeAudioActive ? nativeMicLevelRef : audioLevelRef}
            systemAudioLevel={liveSessionId === session.id ? (nativeAudioActive ? nativeSystemAudioLevelRef : systemAudioLevelRef) : SILENT_AUDIO_LEVEL}
            systemAudioActive={liveSessionId === session.id && (systemAudioActive || nativeSystemAudioActive)}
            systemAudioWarning={liveSessionId === session.id && !nativeAudioActive ? systemAudioWarning : null}
            isCapturing={liveSessionId === session.id && (isCapturing || nativeAudioActive)}
            isStarting={liveSessionId === session.id && audioStarting}
            audioStats={audioStats}
            backendAudioStatus={runtimeMatchesView ? backendAudioStatus : null}
            captureError={runtimeMatchesView ? captureError : null}
            status={liveSessionId === session.id ? status : "disconnected"}
            callSegmentStart={viewedCallSegmentStart}
            speakers={speakers}
            postProcessing={postProcessing}
            synthesis={liveSynthesis}
            activity={viewRuntimeActivity}
            debateRecommendation={viewDebateRecommendation}
            onDebateResearch={sendDebateResearch}
            onDebateAnalysisCancel={sendDebateAnalysisCancel}
            onDebateAnswerGood={sendDebateAnswerGood}
            debateResearchEnabled={debateSettings?.research_enabled ?? false}
            onDebateResearchEnabledChange={handleDebateResearchControl}
          />
        );
      case "completed":
        return (
          <PostCallView
            key={session.id}
            session={session}
            questions={allQuestions}
            transcripts={reviewTranscripts}
            directives={directives}
            documents={documents}
            segments={segments}
            speakers={speakers}
            synthesis={postCallSynthesis}
            signalHistoryCount={liveSynthesis?.signal_history_count ?? 0}
            onResumeCall={handleResumeCall}
            onDeleteSession={handleDeleteSession}
            onRefreshSpeakers={refreshSpeakers}
            onRefreshSession={refreshSession}
            onRefreshQuestions={refreshQuestions}
            onRefreshSynthesis={refreshSynthesis}
            onOpenAdminAgents={handleOpenEnhancementAgents}
            onRenameSession={handleRenameSession}
            onRetranscribed={async () => {
              setLiveTranscripts([]);
              await Promise.all([refreshTranscripts(), refreshSpeakers(), refreshSegments()]);
            }}
            postProcessing={postProcessing}
          />
        );
      default:
        return null;
    }
  };

  return (
    <Layout
      sessions={sessions}
      groups={groups}
      activeSessionId={activeSessionId}
      onSelectSession={handleSelectSession}
      onNewSession={handleNewSession}
      onOpenOfferings={handleOpenOfferings}
      onOpenKnowledge={handleOpenKnowledge}
      onOpenAdmin={handleOpenAdmin}
      showingOfferings={showOfferings}
      showingKnowledge={showKnowledge}
      showingAdmin={showAdmin}
      liveCallActive={session?.state === "active" && !showOfferings && !showKnowledge && !showAdmin}
      onDeleteSession={handleDeleteSessionById}
      onRefreshGroups={refreshGroups}
      onRefreshSessions={refreshSessions}
    >
      <Suspense fallback={<div role="status" className="p-6 font-body text-sm text-brand-gray">Ansicht wird geladen ...</div>}>
        {renderContent()}
      </Suspense>
      <AppOverlays
        update={desktopUpdate}
        newSessionOpen={showNewSession}
        onCloseNewSession={() => setShowNewSession(false)}
        onCreateSession={handleCreateSession}
        suppressDesktopUpdate={(showAdmin && adminTab === "about") || !!liveSessionId}
        whatsNew={bannerOpen ? whatsNew : null}
        onOpenUpdate={() => openAdmin("about")}
        onAcknowledgeUpdate={acknowledgeWhatsNew}
        downloads={modelDownloads}
        onOpenPrivacy={() => openAdmin("privacy")}
      />
    </Layout>
  );
}

export default function App() {
  if (new URLSearchParams(window.location.search).get("overlay") === "1") {
    return <DebateOverlay />;
  }
  return <MainApp />;
}
