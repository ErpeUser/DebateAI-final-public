import { useCallback, useEffect, useRef, useState } from "react";
import type { AudioSendStats, DebateResearchCategory, StopDrainMode, WSMessage, WSSessionSnapshot } from "../types";
import type { AudioTrack } from "./useAudioCapture";
import { getDesktopInstanceToken } from "../services/api";
import {
  processedSocketSequence,
  shouldReconnectVisibleSession,
  shouldResetForServerEpoch,
  socketPayloadEvents,
  stageSocketPayload,
} from "../lib/wsEventStream";

export type WSStatus = "disconnected" | "connecting" | "connected" | "error";

/**
 * How a stop wait ended.
 *
 * "still_processing" is the honest middle case the old boolean could not say:
 * the backend never answered, but it never hung up either, so the call is very
 * likely finishing without us. Reporting that as failure is what produced a
 * connection-lost banner and a resume prompt on a call the user just ended.
 */
export type StopOutcome = "completed" | "still_processing" | "disconnected";

// How long the client waits for ANY traffic before assuming silence. Rearmed by
// every message, so this bounds a gap between messages, not the whole drain.
export const STOP_SILENCE_TIMEOUT_MS = 180000;
// WebSocket.send() has no backpressure promise.  Keep a hysteresis window
// around the browser's internal send buffer so an overloaded connection drops
// only the current interim frame and exposes the count in the audio status.
export const AUDIO_SEND_HIGH_WATER_BYTES = 1_000_000;
export const AUDIO_SEND_LOW_WATER_BYTES = 250_000;

/**
 * Manages a WebSocket connection to the backend for a single call session.
 * Handles binary frames (audio) and JSON messages (questions, transcripts, status).
 */
export function useWebSocket() {
  const [status, setStatus] = useState<WSStatus>("disconnected");
  const [messages, setMessages] = useState<WSMessage[]>([]);
  const [audioStats, setAudioStats] = useState<AudioSendStats>({
    chunksSent: 0,
    bytesSent: 0,
    chunksDropped: 0,
    lastSentAt: null,
  });
  const wsRef = useRef<WebSocket | null>(null);
  const connectionTokenRef = useRef(0);
  const sessionIdRef = useRef("");
  const lastSequenceRef = useRef(0);
  const serverEpochRef = useRef("");
  const captureIdRef = useRef("");
  const shouldReconnectRef = useRef(false);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<number | null>(null);
  const connectRef = useRef<((sessionId: string) => void) | null>(null);
  const stopCompletionRef = useRef<((outcome: StopOutcome) => void) | null>(null);
  const stopTimeoutRef = useRef<number | null>(null);
  const audioStatsRef = useRef<AudioSendStats>({
    chunksSent: 0,
    bytesSent: 0,
    chunksDropped: 0,
    lastSentAt: null,
  });
  const lastAudioStatsPublishRef = useRef(0);
  const messagesRef = useRef<WSMessage[]>([]);
  const audioBackpressureRef = useRef(false);

  const acknowledgeMessages = useCallback((processedMessages: WSMessage[]) => {
    lastSequenceRef.current = processedSocketSequence(
      processedMessages,
      lastSequenceRef.current,
    );
  }, []);

  const resetAudioStats = useCallback(() => {
    const empty = {
      chunksSent: 0,
      bytesSent: 0,
      chunksDropped: 0,
      lastSentAt: null,
    };
    audioStatsRef.current = empty;
    lastAudioStatsPublishRef.current = 0;
    setAudioStats(empty);
  }, []);

  const publishAudioStats = useCallback((force = false) => {
    const now = Date.now();
    if (!force && now - lastAudioStatsPublishRef.current < 1000) return;
    lastAudioStatsPublishRef.current = now;
    setAudioStats({ ...audioStatsRef.current });
  }, []);

  const resolveStop = useCallback((outcome: StopOutcome) => {
    if (stopTimeoutRef.current !== null) {
      window.clearTimeout(stopTimeoutRef.current);
      stopTimeoutRef.current = null;
    }
    stopCompletionRef.current?.(outcome);
    stopCompletionRef.current = null;
  }, []);

  // Silence, not duration, is what says the backend is gone. The deadline is
  // rearmed by every message, so a drain that legitimately runs for minutes
  // keeps its wait alive as long as progress or heartbeats are arriving
  // (ALP-171: a fixed 180s timer abandoned a drain that took four twenty).
  const armStopDeadline = useCallback(() => {
    if (stopCompletionRef.current === null) return;
    if (stopTimeoutRef.current !== null) window.clearTimeout(stopTimeoutRef.current);
    stopTimeoutRef.current = window.setTimeout(
      () => resolveStop("still_processing"),
      STOP_SILENCE_TIMEOUT_MS,
    );
  }, [resolveStop]);

  const connect = useCallback((sessionId: string) => {
    if (reconnectTimerRef.current !== null) {
      window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    connectionTokenRef.current += 1;
    const token = connectionTokenRef.current;
    shouldReconnectRef.current = true;

    if (wsRef.current) {
      wsRef.current.close();
    }

    setStatus("connecting");
    if (sessionIdRef.current !== sessionId) {
      sessionIdRef.current = sessionId;
      captureIdRef.current = "";
      lastSequenceRef.current = 0;
      serverEpochRef.current = "";
      reconnectAttemptRef.current = 0;
      messagesRef.current = [];
      setMessages([]);
      resetAudioStats();
    }
    if (!captureIdRef.current) {
      captureIdRef.current = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`;
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const instanceToken = getDesktopInstanceToken();
    const query = new URLSearchParams();
    if (lastSequenceRef.current > 0) {
      query.set("after_sequence", String(lastSequenceRef.current));
    }
    if (serverEpochRef.current) {
      query.set("after_epoch", serverEpochRef.current);
    }
    query.set("capture_id", captureIdRef.current);
    const suffix = query.size ? `?${query.toString()}` : "";
    const wsUrl = `${protocol}//${window.location.host}/ws/${sessionId}${suffix}`;
    // Keep the instance token out of URLs, browser history, and proxy logs.
    const ws = instanceToken
      ? new WebSocket(wsUrl, [`backchannel.instance.${instanceToken}`])
      : new WebSocket(wsUrl);
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;

    ws.onopen = () => {
      if (connectionTokenRef.current !== token) return;
      reconnectAttemptRef.current = 0;
      setStatus("connected");
    };

    ws.onmessage = (event: MessageEvent) => {
      if (connectionTokenRef.current !== token) return;

      if (event.data instanceof ArrayBuffer) {
        // Binary frame = audio out; ignored here, handled by caller if needed
        return;
      }

      try {
        const payload = JSON.parse(event.data as string) as WSMessage | WSSessionSnapshot;
        if (payload.type === "session_snapshot") {
          const incomingEpoch = payload.data.server_epoch || "";
          if (shouldResetForServerEpoch(serverEpochRef.current, incomingEpoch)) {
            lastSequenceRef.current = 0;
            messagesRef.current = [];
            setMessages([]);
          }
          serverEpochRef.current = incomingEpoch;
        }
        const accepted = socketPayloadEvents(payload)
          .filter((message) => (
            typeof message.session_sequence !== "number"
            || message.session_sequence > lastSequenceRef.current
          )) as WSMessage[];
        if (accepted.length) {
          const staged = stageSocketPayload(
            messagesRef.current,
            payload,
            lastSequenceRef.current,
            1000,
          );
          if (staged.needsResync) {
            // The server journal compacts a full snapshot to current state.
            // Reconnect from the last processed sequence instead of dropping
            // an unrendered final event and falsely acknowledging the gap.
            armStopDeadline();
            connectRef.current?.(sessionId);
            return;
          }
          messagesRef.current = staged.events as WSMessage[];
          setMessages(messagesRef.current);
        }
        // Any traffic proves the backend is alive and working.
        armStopDeadline();
        const completed = accepted.find(
          (message) => message.type === "status" && message.data.state === "completed",
        );
        if (completed) {
          shouldReconnectRef.current = false;
          resolveStop("completed");
        }
      } catch {
        console.warn("Unparseable WS message", event.data);
      }
    };

    ws.onerror = () => {
      if (connectionTokenRef.current !== token) return;
      setStatus("error");
    };

    ws.onclose = () => {
      if (connectionTokenRef.current !== token) return;
      resolveStop("disconnected");
      wsRef.current = null;
      if (shouldReconnectRef.current && sessionIdRef.current === sessionId) {
        setStatus("connecting");
        const delay = Math.min(5000, 500 * (2 ** reconnectAttemptRef.current));
        reconnectAttemptRef.current += 1;
        reconnectTimerRef.current = window.setTimeout(
          () => connectRef.current?.(sessionId),
          delay,
        );
      } else {
        setStatus("disconnected");
      }
    };
  }, [armStopDeadline, resolveStop, resetAudioStats]);

  connectRef.current = connect;

  useEffect(() => {
    const synchronizeWhenVisible = () => {
      const sessionId = sessionIdRef.current;
      if (!shouldReconnectVisibleSession(
        document.visibilityState,
        sessionId,
        shouldReconnectRef.current,
        wsRef.current?.readyState ?? null,
      )) return;
      connectRef.current?.(sessionId);
    };

    document.addEventListener("visibilitychange", synchronizeWhenVisible);
    return () => {
      document.removeEventListener("visibilitychange", synchronizeWhenVisible);
      shouldReconnectRef.current = false;
      connectionTokenRef.current += 1;
      if (reconnectTimerRef.current !== null) {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      resolveStop("disconnected");
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [resolveStop]);

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;
    captureIdRef.current = "";
    if (reconnectTimerRef.current !== null) {
      window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    connectionTokenRef.current += 1;
    resolveStop("disconnected");
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setStatus("disconnected");
    publishAudioStats(true);
  }, [resolveStop, publishAudioStats]);

  const sendAudio = useCallback((data: ArrayBuffer, track: 0 | 1 = 0) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const bufferedAmount = wsRef.current.bufferedAmount || 0;
      if (audioBackpressureRef.current) {
        if (bufferedAmount > AUDIO_SEND_LOW_WATER_BYTES) {
          audioStatsRef.current = {
            ...audioStatsRef.current,
            chunksDropped: audioStatsRef.current.chunksDropped + 1,
          };
          publishAudioStats();
          return;
        }
        audioBackpressureRef.current = false;
      }
      if (bufferedAmount >= AUDIO_SEND_HIGH_WATER_BYTES) {
        audioBackpressureRef.current = true;
        audioStatsRef.current = {
          ...audioStatsRef.current,
          chunksDropped: audioStatsRef.current.chunksDropped + 1,
        };
        publishAudioStats();
        return;
      }
      // 1-byte track prefix: 0 = mic, 1 = system audio
      const framed = new Uint8Array(1 + data.byteLength);
      framed[0] = track;
      framed.set(new Uint8Array(data), 1);
      wsRef.current.send(framed.buffer);
      audioStatsRef.current = {
        ...audioStatsRef.current,
        chunksSent: audioStatsRef.current.chunksSent + 1,
        bytesSent: audioStatsRef.current.bytesSent + data.byteLength,
        lastSentAt: new Date().toISOString(),
      };
    } else {
      audioStatsRef.current = {
        ...audioStatsRef.current,
        chunksDropped: audioStatsRef.current.chunksDropped + 1,
      };
    }
    publishAudioStats();
  }, [publishAudioStats]);

  const sendDirective = useCallback((text: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "directive", text }));
    }
  }, []);

  const sendDebateResearch = useCallback((category: DebateResearchCategory) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "debate_research", category }));
    }
  }, []);

  const sendDebateResearchControl = useCallback((enabled: boolean) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: "debate_research_control",
        enabled,
      }));
    }
  }, []);

  const sendDebateAnalysisCancel = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "debate_analysis_cancel" }));
    }
  }, []);

  const sendDebateUpdateAck = useCallback((claimId: string, recommendationRevision: number) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: "debate_update_ack",
        claim_id: claimId,
        recommendation_revision: recommendationRevision,
      }));
    }
  }, []);

  const sendDebateAnswerGood = useCallback((claimId: string, recommendationRevision: number) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: "debate_answer_good",
        claim_id: claimId,
        recommendation_revision: recommendationRevision,
      }));
    }
  }, []);

  const sendTrackState = useCallback((track: AudioTrack, active: boolean) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "track_state", track, active }));
    }
  }, []);

  const sendStop = useCallback((drain: StopDrainMode = "full") => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) {
      return Promise.resolve<StopOutcome>("disconnected");
    }

    return new Promise<StopOutcome>((resolve) => {
      resolveStop("disconnected");
      stopCompletionRef.current = resolve;
      armStopDeadline();
      // A bare stop keeps the backend's full drain; only send the drain field
      // when requesting the shorter pipeline (backward compatible).
      const payload = drain === "full" ? { type: "stop" } : { type: "stop", drain };
      wsRef.current?.send(JSON.stringify(payload));
    });
  }, [resolveStop, armStopDeadline]);

  return { connect, disconnect, sendAudio, sendDirective, sendDebateResearch, sendDebateResearchControl, sendDebateAnalysisCancel, sendDebateUpdateAck, sendDebateAnswerGood, sendTrackState, sendStop, acknowledgeMessages, status, messages, audioStats };
}
