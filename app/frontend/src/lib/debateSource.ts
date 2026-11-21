import type { DebateSource } from "../types";

export function sourceStatusLabel(
  status: DebateSource["verification_status"] | undefined,
): string {
  switch (status) {
    case "read":
      return "Gelesen zu";
    case "supports":
      return "Stuetzt";
    case "contradicts":
      return "Widerspricht";
    case "unclear":
      return "Unklar zu";
    default:
      return "Gefunden zu";
  }
}
