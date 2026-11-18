export type InterimTranscriptMode = "append" | "replace";

const MAX_INTERIM_CHARACTERS = 500;

export function updateInterimText(
  previous: string,
  incoming: string,
  mode: InterimTranscriptMode = "append",
): string {
  const combined = mode === "replace" ? incoming : previous + incoming;
  return combined.length > MAX_INTERIM_CHARACTERS
    ? combined.slice(-MAX_INTERIM_CHARACTERS)
    : combined;
}
