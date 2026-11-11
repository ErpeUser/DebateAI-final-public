import type { DesktopUpdateStatus } from "../types";
import { request } from "./api";

const BASE = "/api";
const INSTANCE_HEADER = "X-DebateAI-Instance";

export const getDesktopUpdate = () => request<DesktopUpdateStatus>("/updates");

export async function getDesktopInstanceToken(): Promise<string> {
  const response = await fetch(`${BASE}/health`, { cache: "no-store" });
  if (!response.ok) throw new Error("Die Desktop-Berechtigung ist nicht verfügbar.");
  const body: unknown = await response.json();
  if (
    typeof body !== "object"
    || body === null
    || Object.keys(body).length !== 1
    || (body as { status?: unknown }).status !== "ok"
  ) {
    throw new Error("Die Desktop-Berechtigung ist nicht verfügbar.");
  }
  const token = response.headers.get(INSTANCE_HEADER)
    ?? "";
  if (!/^[A-Za-z0-9_-]{43}$/.test(token)) {
    throw new Error("Die Desktop-Berechtigung ist nicht verfügbar.");
  }
  return token;
}

const mutation = (
  path: string,
  method: "POST" | "DELETE",
  token: string,
  body?: unknown,
) => request<DesktopUpdateStatus>(path, {
  method,
  headers: {
    "Content-Type": "application/json",
    [INSTANCE_HEADER]: token,
  },
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const checkDesktopUpdate = (token: string) =>
  mutation("/updates/check", "POST", token);

export const startDesktopUpdateDownload = (token: string) =>
  mutation("/updates/download", "POST", token);

export const cancelDesktopUpdate = (token: string) =>
  mutation("/updates/download", "DELETE", token);

export const applyDesktopUpdate = (token: string) =>
  mutation("/updates/apply", "POST", token);
