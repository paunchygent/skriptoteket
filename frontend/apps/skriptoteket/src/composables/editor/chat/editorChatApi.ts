/**
 * Editor chat API transport.
 *
 * Purpose:
 *   Centralize editor chat history and streaming calls so protected chat
 *   endpoints share the same HuleEdu Gateway production edge as the main API
 *   client.
 *
 * Relationships:
 *   - `api/client.ts` owns protected API base resolution and CSRF-aware
 *     non-streaming helpers.
 *   - `useEditorChat.ts` owns chat UI state and stream consumption.
 */

import { apiFetch, apiGet, resolveProtectedApiUrl } from "../../../api/client";
import type { EditorChatHistoryResponse, EditorChatRequest } from "./editorChatTypes";

type ApiErrorEnvelope = {
  error?: { code?: string; message?: string };
  detail?: unknown;
};

type ChatStreamRequestParams = {
  toolId: string;
  body: EditorChatRequest;
  correlationId: string;
  csrfToken?: string | null;
  signal: AbortSignal;
};

export async function fetchChatHistory(
  toolId: string,
  limit = 60,
): Promise<EditorChatHistoryResponse> {
  return await apiGet<EditorChatHistoryResponse>(
    `/api/v1/editor/tools/${encodeURIComponent(toolId)}/chat?limit=${limit}`,
  );
}

export async function clearChatHistory(toolId: string): Promise<void> {
  await apiFetch<void>(`/api/v1/editor/tools/${encodeURIComponent(toolId)}/chat`, {
    method: "DELETE",
  });
}

export async function postChatStream({
  toolId,
  body,
  correlationId,
  csrfToken,
  signal,
}: ChatStreamRequestParams): Promise<Response> {
  const headers = new Headers({
    Accept: "text/event-stream",
    "Content-Type": "application/json",
  });
  if (csrfToken) {
    headers.set("X-CSRF-Token", csrfToken);
  }
  headers.set("X-Correlation-ID", correlationId);

  const path = `/api/v1/editor/tools/${encodeURIComponent(toolId)}/chat`;

  return await fetch(resolveProtectedApiUrl(path), {
    method: "POST",
    headers,
    body: JSON.stringify(body),
    credentials: "include",
    signal,
  });
}

export async function readChatErrorMessage(response: Response): Promise<string> {
  const contentType = response.headers.get("content-type") ?? "";
  const fallback = response.statusText || `Request failed (${response.status})`;

  if (!contentType.includes("application/json")) {
    return fallback;
  }

  const payload = (await response.json().catch(() => null)) as ApiErrorEnvelope | null;
  if (!payload || typeof payload !== "object") {
    return fallback;
  }

  if (payload.error?.message) {
    return payload.error.message;
  }

  if (payload.detail) {
    return "Validation error";
  }

  return fallback;
}
