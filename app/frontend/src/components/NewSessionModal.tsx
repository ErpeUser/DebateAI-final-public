import { useEffect, useRef, useState } from "react";
import type { MeetingType } from "../types";
import { MEETING_TYPES } from "./PreCall/MeetingContextSetup";

interface Props {
  open: boolean;
  onClose: () => void;
  onCreate: (name: string, meetingType: MeetingType) => Promise<void>;
}

function suggestedName(): string {
  const now = new Date();
  const date = now.toLocaleDateString("de-DE", {
    month: "short",
    day: "numeric",
  });
  const time = now.toLocaleTimeString("de-DE", {
    hour: "2-digit",
    minute: "2-digit",
  });
  return `Debatte ${date}, ${time}`;
}

export default function NewSessionModal({ open, onClose, onCreate }: Props) {
  const [name, setName] = useState("");
  const [meetingType, setMeetingType] =
    useState<MeetingType>("debate_persuasive");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const placeholder = useRef(suggestedName());

  // Reset state each time the modal opens, then focus the name field
  useEffect(() => {
    if (!open) return;
    setName("");
    setMeetingType("debate_persuasive");
    setCreating(false);
    setError(null);
    placeholder.current = suggestedName();
    const id = window.setTimeout(() => inputRef.current?.focus(), 50);
    return () => window.clearTimeout(id);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  const trimmed = name.trim();
  const finalName = trimmed || placeholder.current;
  const handleCreate = async () => {
    if (creating) return;
    setCreating(true);
    setError(null);
    try {
      await onCreate(finalName, meetingType);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Sitzung konnte nicht erstellt werden.",
      );
      setCreating(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-brand-dark-gray/40 p-4 backdrop-blur-sm"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget && !creating) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="new-session-title"
        className="w-full max-w-lg rounded-xl bg-surface shadow-2xl ring-1 ring-brand-light-gray-1 animate-slide-in-right"
      >
        <div className="flex items-start justify-between border-b border-brand-light-gray-1 px-6 py-4">
          <div>
            <h2
              id="new-session-title"
              className="font-display text-lg font-semibold text-brand-dark-gray"
            >
              Neue Debatte
            </h2>
            <p className="mt-0.5 font-body text-xs text-brand-mid-gray">
              Deutsch, Auto-Recherche, Analogien und alle Debattenassistenten
              sind fertig eingestellt.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={creating}
            className="inline-flex h-11 w-11 items-center justify-center rounded-lg text-brand-mid-gray transition-colors hover:bg-brand-light-gray-2 hover:text-brand-dark-gray disabled:opacity-50"
            aria-label="Schließen"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18 18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div className="px-6 py-5">
          <label
            htmlFor="new-session-name"
            className="mb-1.5 block font-body text-xs font-semibold uppercase tracking-wide text-brand-mid-gray"
          >
            Name der Debatte
          </label>
          <input
            id="new-session-name"
            ref={inputRef}
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void handleCreate();
            }}
            placeholder={placeholder.current}
            disabled={creating}
            maxLength={120}
            className="w-full rounded-lg border border-brand-light-gray-1 bg-surface px-3 py-2.5 font-body text-sm text-brand-dark-gray placeholder:text-brand-mid-gray/70 transition-colors focus:border-brand-teal focus:ring-2 focus:ring-brand-teal-light/40 disabled:bg-brand-light-gray-2"
          />
          <p className="mt-1.5 font-body text-[11px] text-brand-mid-gray">
            Leer lassen, um den vorgeschlagenen Namen zu verwenden.
          </p>

          <div
            className="mt-5 grid gap-2 sm:grid-cols-2"
            aria-label="Debattenmodus"
          >
            {MEETING_TYPES.slice(0, 2).map((type) => {
              const active = type.value === meetingType;
              return (
                <button
                  key={type.value}
                  type="button"
                  aria-pressed={active}
                  onClick={() => setMeetingType(type.value)}
                  disabled={creating}
                  className={`rounded-lg border px-3 py-3 text-left transition-colors ${
                    active
                      ? "border-brand-dark-gray bg-brand-light-gray-2"
                      : "border-brand-light-gray-1 bg-surface hover:bg-brand-light-gray-2/60"
                  }`}
                >
                  <span className="block font-body text-xs font-semibold text-brand-dark-gray">
                    {type.label}
                  </span>
                  <span className="mt-1 block font-body text-[11px] leading-relaxed text-brand-mid-gray">
                    {type.hint}
                  </span>
                </button>
              );
            })}
          </div>

          {error && (
            <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 font-body text-xs text-red-600">
              {error}
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 rounded-b-xl border-t border-brand-light-gray-1 bg-brand-light-gray-2/60 px-6 py-4">
          <button
            type="button"
            onClick={onClose}
            disabled={creating}
            className="min-h-11 rounded-lg px-4 py-2 font-body text-sm font-medium text-brand-gray transition-colors hover:bg-brand-light-gray-2 hover:text-brand-dark-gray disabled:opacity-50"
          >
            Abbrechen
          </button>
          <button
            type="button"
            onClick={() => void handleCreate()}
            disabled={creating}
            className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-brand-teal px-4 py-2 font-display text-sm font-semibold text-white shadow-sm transition-colors hover:bg-brand-teal-dark disabled:cursor-not-allowed disabled:opacity-60"
          >
            {creating && (
              <svg
                className="h-3.5 w-3.5 animate-spin"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4z"
                />
              </svg>
            )}
            {creating ? "Wird erstellt..." : "Erstellen"}
          </button>
        </div>
      </div>
    </div>
  );
}
