import React, { useState, useRef, useEffect } from "react";
import type { Speaker, TranscriptEntry } from "../../types";

interface TranscriptReviewProps {
  transcripts: TranscriptEntry[];
  speakers: Speaker[];
  onRenameSpeaker?: (speakerId: string, newName: string) => void;
  onCorrectTranscript?: (transcriptId: string, text: string, reason: string) => Promise<void> | void;
}

function formatTimestamp(ts: string): string {
  try {
    return new Date(ts).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return ts;
  }
}

function InlineSpeakerLabel({
  speaker,
  onRename,
}: {
  speaker: Speaker;
  onRename?: (speakerId: string, newName: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState(speaker.name);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [editing]);

  const handleCommit = () => {
    const trimmed = editName.trim();
    if (trimmed && trimmed !== speaker.name && onRename) {
      onRename(speaker.id, trimmed);
    }
    setEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleCommit();
    } else if (e.key === "Escape") {
      setEditName(speaker.name);
      setEditing(false);
    }
  };

  if (editing) {
    return (
      <input
        ref={inputRef}
        type="text"
        value={editName}
        onChange={(e) => setEditName(e.target.value)}
        onBlur={handleCommit}
        onKeyDown={handleKeyDown}
        className="mr-1.5 inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold text-white border-0"
        style={{ backgroundColor: speaker.color, width: `${Math.max(editName.length + 2, 4)}ch` }}
      />
    );
  }

  return (
    <span
      className={`mr-1.5 inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold text-white ${onRename ? "cursor-pointer hover:opacity-80" : ""}`}
      style={{ backgroundColor: speaker.color }}
      onClick={() => {
        if (onRename) {
          setEditName(speaker.name);
          setEditing(true);
        }
      }}
      title={onRename ? "Click to rename" : undefined}
    >
      {speaker.display_name && speaker.display_name_enabled ? speaker.display_name : speaker.name}
    </span>
  );
}

function EditableTranscriptText({
  entry,
  onCorrect,
}: {
  entry: TranscriptEntry;
  onCorrect?: (transcriptId: string, text: string, reason: string) => Promise<void> | void;
}) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(entry.text);
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!editing) setText(entry.text);
  }, [editing, entry.text]);

  if (!editing || !onCorrect || !entry.id || entry.provisional) {
    return (
      <span className="text-sm leading-relaxed text-brand-dark-gray">
        {entry.text}
        {onCorrect && entry.id && !entry.provisional && (
          <button
            type="button"
            onClick={() => setEditing(true)}
            className="ml-2 rounded px-1.5 py-0.5 text-[10px] font-semibold text-brand-teal hover:bg-brand-teal/10"
          >
            Text korrigieren
          </button>
        )}
        {entry.manual_corrected_at && (
          <span className="ml-2 text-[10px] text-brand-mid-gray">Manuell korrigiert</span>
        )}
      </span>
    );
  }

  const save = async () => {
    const corrected = text.trim();
    if (!corrected || corrected === entry.text) {
      setEditing(false);
      return;
    }
    setSaving(true);
    try {
      await onCorrect(entry.id!, corrected, reason.trim() || "Manuelle Korrektur");
      setEditing(false);
      setReason("");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mt-2 space-y-2">
      <textarea
        value={text}
        onChange={(event) => setText(event.target.value)}
        rows={3}
        aria-label="Transkripttext korrigieren"
        className="w-full rounded border border-brand-light-gray-1 bg-surface px-3 py-2 text-sm text-brand-dark-gray"
      />
      <input
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        placeholder="Korrekturgrund (optional)"
        className="w-full rounded border border-brand-light-gray-1 bg-surface px-3 py-1.5 text-xs text-brand-dark-gray"
      />
      <div className="flex gap-2">
        <button type="button" disabled={saving} onClick={() => void save()} className="rounded bg-brand-teal px-3 py-1 text-xs font-semibold text-white disabled:opacity-50">Speichern</button>
        <button type="button" disabled={saving} onClick={() => setEditing(false)} className="rounded border px-3 py-1 text-xs">Abbrechen</button>
      </div>
    </div>
  );
}

export default function TranscriptReview({ transcripts, speakers, onRenameSpeaker, onCorrectTranscript }: TranscriptReviewProps) {
  if (transcripts.length === 0) {
    return (
      <div className="rounded-xl bg-surface p-10 text-center shadow-sm">
        <p className="text-brand-mid-gray">Für diese Sitzung wurden keine Transkripteinträge aufgezeichnet.</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl bg-surface shadow-sm">
      <div className="border-b border-brand-light-gray-1 px-6 py-4">
        <h2 className="font-display text-lg font-semibold text-brand-dark-gray">
          Vollständiges Transkript
        </h2>
        <p className="mt-1 text-xs text-brand-mid-gray">
          {transcripts.length} {transcripts.length === 1 ? "entry" : "entries"}
          {onRenameSpeaker && " \u00b7 Zum Umbenennen auf einen Sprechernamen klicken"}
        </p>
      </div>

      <div className="max-h-[600px] overflow-y-auto">
        <ul className="divide-y divide-brand-light-gray-1">
          {transcripts.map((entry, idx) => {
            const speaker = entry.speaker_id ? speakers.find((s) => s.id === entry.speaker_id) : null;
            return (
              <li key={entry.id ?? entry.utterance_id ?? `sequence-${entry.sequence ?? idx}`} className="flex gap-4 px-6 py-4">
                <span className="shrink-0 pt-0.5 font-mono text-xs text-brand-mid-gray">
                  {formatTimestamp(entry.timestamp)}
                </span>
                <div className="flex-1">
                  {speaker && (
                    <InlineSpeakerLabel speaker={speaker} onRename={onRenameSpeaker} />
                  )}
                  <EditableTranscriptText entry={entry} onCorrect={onCorrectTranscript} />
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
