export type SocketEvent = {
  type: string;
  data?: Record<string, any>;
  event_id?: number;
  session_sequence?: number;
};

type SnapshotPayload = {
  type: "session_snapshot";
  data: {
    events: SocketEvent[];
  };
};

export type StagedSocketPayload = {
  events: SocketEvent[];
  needsResync: boolean;
};

export function shouldResetMessageCursor(
  activeMessageSessionId: string,
  bufferedMessageSessionId: string,
): boolean {
  return Boolean(
    activeMessageSessionId
    && activeMessageSessionId !== bufferedMessageSessionId
  );
}

export function shouldResetForServerEpoch(
  currentEpoch: string,
  incomingEpoch: string,
): boolean {
  return Boolean(
    currentEpoch
    && incomingEpoch
    && currentEpoch !== incomingEpoch
  );
}

export function shouldReconnectVisibleSession(
  visibilityState: string,
  sessionId: string,
  shouldReconnect: boolean,
  readyState: number | null,
): boolean {
  return Boolean(
    visibilityState === "visible"
    && sessionId
    && shouldReconnect
    && readyState !== WebSocket.CONNECTING
    && readyState !== WebSocket.OPEN
  );
}

function transientKey(event: SocketEvent) {
  if (event.type === "interim_transcript") {
    return `interim:${event.data?.track_id || "default"}:${event.data?.segment_id || "legacy"}`;
  }
  if (event.type === "audio_level") {
    return `audio_level:${event.data?.track ?? 0}`;
  }
  return "";
}

export function socketPayloadEvents(payload: SocketEvent | SnapshotPayload): SocketEvent[] {
  if (payload.type === "session_snapshot") {
    return Array.isArray(payload.data?.events) ? payload.data.events : [];
  }
  return [payload];
}

export function stageSocketPayload(
  previous: SocketEvent[],
  payload: SocketEvent | SnapshotPayload,
  renderedSequence: number,
  maxMessages = 1000,
): StagedSocketPayload {
  const accepted = socketPayloadEvents(payload).filter((event) => (
    typeof event.session_sequence !== "number"
    || event.session_sequence > renderedSequence
  ));
  const events = mergeSocketEvents(previous, accepted, Number.MAX_SAFE_INTEGER, renderedSequence);

  while (events.length > maxMessages) {
    const transientIndex = events.findIndex((event) => Boolean(transientKey(event)));
    if (transientIndex >= 0) {
      events.splice(transientIndex, 1);
      continue;
    }

    const renderedIndex = events.findIndex((event) => (
      typeof event.session_sequence === "number"
      && event.session_sequence <= renderedSequence
    ));
    if (renderedIndex >= 0) {
      events.splice(renderedIndex, 1);
      continue;
    }

    return { events: previous, needsResync: true };
  }

  return { events, needsResync: false };
}

export function processedSocketSequence(events: SocketEvent[], previous = 0): number {
  return events.reduce(
    (highest, event) => Math.max(highest, event.session_sequence || 0),
    previous,
  );
}

export function mergeSocketEvents<T extends SocketEvent>(
  previous: T[],
  incoming: T[],
  maxMessages = 1000,
  renderedSequence = Number.MAX_SAFE_INTEGER,
): T[] {
  const result = [...previous];
  const sequences = new Set(
    result
      .map((event) => event.session_sequence)
      .filter((sequence): sequence is number => typeof sequence === "number"),
  );

  for (const incomingEvent of incoming) {
    let event = incomingEvent;
    if (typeof event.session_sequence === "number" && sequences.has(event.session_sequence)) {
      continue;
    }
    const key = transientKey(event);
    if (key) {
      const staleIndex = result.findIndex((candidate) => transientKey(candidate) === key);
      if (staleIndex >= 0) {
        const stale = result[staleIndex];
        const staleUnrendered = (
          typeof stale.session_sequence === "number"
          && stale.session_sequence > renderedSequence
        );
        if (
          event.type === "interim_transcript"
          && event.data?.mode === "append"
          && staleUnrendered
        ) {
          event = {
            ...event,
            data: {
              ...event.data,
              text: String(stale.data?.text || "") + String(event.data?.text || ""),
            },
          } as T;
        }
        result.splice(staleIndex, 1);
      }
    }
    result.push(event);
    if (typeof event.session_sequence === "number") sequences.add(event.session_sequence);
  }

  while (result.length > maxMessages) {
    const transientIndex = result.findIndex((event) => Boolean(transientKey(event)));
    if (transientIndex < 0) break;
    result.splice(transientIndex, 1);
  }
  return result;
}
