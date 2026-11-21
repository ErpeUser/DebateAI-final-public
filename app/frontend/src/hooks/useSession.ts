import { useCallback, useEffect, useRef, useState } from "react";
import type {
  CallSegment,
  Directive,
  Document,
  Question,
  Session,
  SessionSynthesis,
  Speaker,
  TranscriptEntry,
} from "../types";
import {
  getSynthesis,
  getSession,
  listDirectives,
  listDocuments,
  listQuestions,
  listSegments,
  listSpeakers,
  listTranscripts,
} from "../services/api";
import { isCurrentSessionResponse } from "../lib/sessionRefresh";

export { reconcileRefusedSession } from "../lib/callRefusal";

export function useSession(sessionId: string | null) {
  const currentSessionIdRef = useRef(sessionId);
  currentSessionIdRef.current = sessionId;
  const [session, setSession] = useState<Session | null>(null);
  const [directives, setDirectives] = useState<Directive[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [segments, setSegments] = useState<CallSegment[]>([]);
  const [speakers, setSpeakers] = useState<Speaker[]>([]);
  const [transcripts, setTranscripts] = useState<TranscriptEntry[]>([]);
  const [synthesis, setSynthesis] = useState<SessionSynthesis | null>(null);
  const [liveSynthesis, setLiveSynthesis] = useState<SessionSynthesis | null>(
    null,
  );
  const [loading, setLoading] = useState(false);

  const refreshSession = useCallback(async () => {
    if (!sessionId) return;
    const requestedSessionId = sessionId;
    const data = await getSession(sessionId);
    if (
      isCurrentSessionResponse(requestedSessionId, currentSessionIdRef.current)
    )
      setSession(data);
  }, [sessionId]);

  const refreshDirectives = useCallback(async () => {
    if (!sessionId) return;
    const requestedSessionId = sessionId;
    const data = await listDirectives(sessionId);
    if (
      isCurrentSessionResponse(requestedSessionId, currentSessionIdRef.current)
    )
      setDirectives(data);
  }, [sessionId]);

  const refreshDocuments = useCallback(async () => {
    if (!sessionId) return;
    const requestedSessionId = sessionId;
    const data = await listDocuments(sessionId);
    if (
      isCurrentSessionResponse(requestedSessionId, currentSessionIdRef.current)
    )
      setDocuments(data);
  }, [sessionId]);

  const refreshQuestions = useCallback(async () => {
    if (!sessionId) return;
    const requestedSessionId = sessionId;
    const data = await listQuestions(sessionId);
    if (
      isCurrentSessionResponse(requestedSessionId, currentSessionIdRef.current)
    )
      setQuestions(data);
  }, [sessionId]);

  const refreshSegments = useCallback(async () => {
    if (!sessionId) return;
    const requestedSessionId = sessionId;
    const data = await listSegments(sessionId);
    if (
      isCurrentSessionResponse(requestedSessionId, currentSessionIdRef.current)
    )
      setSegments(data);
  }, [sessionId]);

  const refreshSpeakers = useCallback(async () => {
    if (!sessionId) return;
    const requestedSessionId = sessionId;
    const data = await listSpeakers(sessionId);
    if (
      isCurrentSessionResponse(requestedSessionId, currentSessionIdRef.current)
    )
      setSpeakers(data);
  }, [sessionId]);

  const refreshTranscripts = useCallback(async () => {
    if (!sessionId) return;
    const requestedSessionId = sessionId;
    const data = await listTranscripts(sessionId);
    if (
      isCurrentSessionResponse(requestedSessionId, currentSessionIdRef.current)
    )
      setTranscripts(data);
  }, [sessionId]);

  const refreshSynthesis = useCallback(
    async (mode = "post_call") => {
      if (!sessionId) return;
      const requestedSessionId = sessionId;
      const data = await getSynthesis(sessionId, mode);
      if (
        !isCurrentSessionResponse(
          requestedSessionId,
          currentSessionIdRef.current,
        )
      )
        return data;
      if (mode === "live") {
        setLiveSynthesis(data);
      } else {
        setSynthesis(data);
      }
      return data;
    },
    [sessionId],
  );

  useEffect(() => {
    if (!sessionId) {
      setSession(null);
      setDirectives([]);
      setDocuments([]);
      setQuestions([]);
      setSegments([]);
      setSpeakers([]);
      setTranscripts([]);
      setSynthesis(null);
      setLiveSynthesis(null);
      return;
    }

    let cancelled = false;
    setSession(null);
    setDirectives([]);
    setDocuments([]);
    setQuestions([]);
    setSegments([]);
    setSpeakers([]);
    setTranscripts([]);
    setSynthesis(null);
    setLiveSynthesis(null);

    const loadAll = async () => {
      setLoading(true);
      try {
        const results = await Promise.allSettled([
          getSession(sessionId),
          listDirectives(sessionId),
          listDocuments(sessionId),
          listQuestions(sessionId),
          listSegments(sessionId),
          listSpeakers(sessionId),
          listTranscripts(sessionId),
          getSynthesis(sessionId),
          getSynthesis(sessionId, "live"),
        ]);
        if (cancelled) return;
        const [sess, dirs, docs, qs, segs, spkrs, txs, synth, liveSynth] =
          results;
        if (sess.status === "fulfilled") setSession(sess.value);
        if (dirs.status === "fulfilled") setDirectives(dirs.value);
        if (docs.status === "fulfilled") setDocuments(docs.value);
        if (qs.status === "fulfilled") setQuestions(qs.value);
        if (segs.status === "fulfilled") setSegments(segs.value);
        if (spkrs.status === "fulfilled") setSpeakers(spkrs.value);
        if (txs.status === "fulfilled") setTranscripts(txs.value);
        if (synth.status === "fulfilled") setSynthesis(synth.value);
        if (liveSynth.status === "fulfilled") setLiveSynthesis(liveSynth.value);
        const failures = results.filter(
          (result) => result.status === "rejected",
        );
        if (failures.length)
          console.warn("Some session resources failed to load", failures);
      } catch (err) {
        console.error("Failed to load session data", err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    loadAll();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  return {
    session,
    directives,
    documents,
    questions,
    segments,
    speakers,
    transcripts,
    synthesis,
    liveSynthesis,
    loading,
    refreshSession,
    refreshDirectives,
    refreshDocuments,
    refreshQuestions,
    refreshSegments,
    refreshSpeakers,
    refreshTranscripts,
    refreshSynthesis,
  };
}
