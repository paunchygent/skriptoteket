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

import { apiFetch, apiGet, bindProtectedSession, resolveProtectedApiUrl } from "../../../api/client";
import type { AuthSession } from "../../../stores/auth";
import type { EditorChatHistoryResponse, EditorChatRequest } from "./editorChatTypes";

type ChatStreamRequestParams = {
  toolId: string;
  body: EditorChatRequest;
  correlationId: string;
  session?: AuthSession;
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
  session,
  signal,
}: ChatStreamRequestParams): Promise<Response> {
  const headers = new Headers({
    Accept: "text/event-stream",
    "Content-Type": "application/json",
  });
  headers.set("X-Correlation-ID", correlationId);

  const path = `/api/v1/editor/tools/${encodeURIComponent(toolId)}/chat`;

  const binding = bindProtectedSession(session);
  const serializedBody = JSON.stringify(body);
  return binding.requestWithCsrf((csrfToken) => {
    const attemptHeaders = new Headers(headers);
    if (csrfToken) attemptHeaders.set("X-CSRF-Token", csrfToken);
    return fetch(resolveProtectedApiUrl(path), {
      method: "POST", headers: attemptHeaders, body: serializedBody,
      credentials: "include", signal,
    });
  });
}
