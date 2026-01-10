import { ref, watch, type Ref } from "vue";

import { apiFetch, apiGet, isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import { useAuthStore } from "../../stores/auth";
import { createSseParser } from "./sseParser";

type EditorChatHistoryResponse = components["schemas"]["EditorChatHistoryResponse"];
type EditorChatHistoryMessage = components["schemas"]["EditorChatHistoryMessage"];
type EditorChatRequest = components["schemas"]["EditorChatRequest"];

type ChatRole = "user" | "assistant";

type UseEditorChatOptions = {
  toolId: Readonly<Ref<string>>;
  baseVersionId: Readonly<Ref<string | null>>;
};

export type EditorChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: string;
  isStreaming?: boolean;
};

type ApiErrorEnvelope = {
  error?: { code?: string; message?: string };
  detail?: unknown;
};

const STREAM_ERROR_MESSAGE = "Det gick inte att läsa AI-svaret.";
const STREAM_PARTIAL_ERROR_MESSAGE = "Svaret kan vara ofullständigt. Skicka igen om något saknas.";
const SEND_ERROR_MESSAGE = "Det gick inte att skicka meddelandet.";
const HISTORY_ERROR_MESSAGE = "Det gick inte att hamta chatthistorik.";
const CLEAR_ERROR_MESSAGE = "Det gick inte att rensa chatten.";
const EMPTY_MESSAGE_ERROR = "Skriv ett meddelande forst.";

function createLocalMessageId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `chat-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function mapHistoryMessage(message: EditorChatHistoryMessage): EditorChatMessage {
  return {
    id: message.message_id,
    role: message.role,
    content: message.content,
    createdAt: message.created_at,
    isStreaming: false,
  };
}

async function readErrorMessage(response: Response): Promise<string> {
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

export function useEditorChat({ toolId, baseVersionId }: UseEditorChatOptions) {
  const auth = useAuthStore();
  const messages = ref<EditorChatMessage[]>([]);
  const streaming = ref(false);
  const disabledMessage = ref<string | null>(null);
  const error = ref<string | null>(null);

  let activeController: AbortController | null = null;
  let activeStreamToken = 0;
  let activeAssistantMessage: EditorChatMessage | null = null;

  function resetLocal(): void {
    if (activeController) {
      activeController.abort();
    }
    activeController = null;
    activeStreamToken += 1;
    streaming.value = false;
    activeAssistantMessage = null;
    messages.value = [];
    disabledMessage.value = null;
    error.value = null;
  }

  function clearError(): void {
    error.value = null;
  }

  function clearDisabledMessage(): void {
    disabledMessage.value = null;
  }

  watch(
    () => toolId.value,
    () => resetLocal(),
  );

  async function loadHistory(): Promise<void> {
    if (!toolId.value || streaming.value) {
      return;
    }

    error.value = null;
    disabledMessage.value = null;

    try {
      const response = await apiGet<EditorChatHistoryResponse>(
        `/api/v1/editor/tools/${encodeURIComponent(toolId.value)}/chat?limit=60`,
      );
      messages.value = response.messages.map(mapHistoryMessage);
    } catch (err: unknown) {
      if (isApiError(err)) {
        error.value = err.message;
      } else {
        error.value = HISTORY_ERROR_MESSAGE;
      }
    }
  }

  async function sendMessage(message: string): Promise<void> {
    if (streaming.value) {
      return;
    }

    const trimmed = message.trim();
    if (!trimmed) {
      error.value = EMPTY_MESSAGE_ERROR;
      return;
    }

    if (!toolId.value) {
      error.value = SEND_ERROR_MESSAGE;
      return;
    }

    error.value = null;
    disabledMessage.value = null;

    const userMessage: EditorChatMessage = {
      id: createLocalMessageId(),
      role: "user",
      content: trimmed,
      createdAt: new Date().toISOString(),
    };
    messages.value = [...messages.value, userMessage];

    activeAssistantMessage = null;
    streaming.value = true;

    const streamToken = ++activeStreamToken;
    const controller = new AbortController();
    activeController = controller;

    const body: EditorChatRequest = { message: trimmed };
    if (baseVersionId.value) {
      body.base_version_id = baseVersionId.value;
    }

    let sawDone = false;
    let sawDelta = false;

    function ensureAssistantMessage(): EditorChatMessage {
      if (activeAssistantMessage) {
        return activeAssistantMessage;
      }
      const assistantMessage: EditorChatMessage = {
        id: createLocalMessageId(),
        role: "assistant",
        content: "",
        createdAt: new Date().toISOString(),
        isStreaming: true,
      };
      activeAssistantMessage = assistantMessage;
      messages.value = [...messages.value, assistantMessage];
      return assistantMessage;
    }

    function finalizeAssistant(): void {
      if (activeAssistantMessage) {
        activeAssistantMessage.isStreaming = false;
      }
      activeAssistantMessage = null;
    }

    try {
      await auth.ensureCsrfToken();
      const headers = new Headers({
        Accept: "text/event-stream",
        "Content-Type": "application/json",
      });
      if (auth.csrfToken) {
        headers.set("X-CSRF-Token", auth.csrfToken);
      }

      const response = await fetch(`/api/v1/editor/tools/${encodeURIComponent(toolId.value)}/chat`, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
        credentials: "include",
        signal: controller.signal,
      });

      if (response.status === 401) {
        auth.clear();
      }

      if (!response.ok || !response.body) {
        const messageText = await readErrorMessage(response);
        error.value = messageText || SEND_ERROR_MESSAGE;
        messages.value = messages.value.filter((item) => item.id !== userMessage.id);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      const parser = createSseParser();

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          break;
        }
        if (streamToken !== activeStreamToken || controller.signal.aborted) {
          continue;
        }
        const chunk = decoder.decode(value, { stream: true });
        const events = parser.push(chunk);
        for (const event of events) {
          if (streamToken !== activeStreamToken || controller.signal.aborted) {
            break;
          }

          let payload: unknown;
          try {
            payload = JSON.parse(event.data);
          } catch {
            continue;
          }

          if (event.event === "delta") {
            if (payload && typeof payload === "object" && "text" in payload) {
              const text = String((payload as { text?: string }).text ?? "");
              if (text) {
                const assistant = ensureAssistantMessage();
                assistant.content += text;
                sawDelta = true;
              }
            }
          }

          if (event.event === "done") {
            if (payload && typeof payload === "object" && "enabled" in payload) {
              const enabled = Boolean((payload as { enabled?: boolean }).enabled);
              if (!enabled) {
                const messageText = String(
                  (payload as { message?: string }).message ?? "",
                ).trim();
                disabledMessage.value = messageText || null;
              } else if ((payload as { reason?: string }).reason === "error") {
                error.value = sawDelta ? STREAM_PARTIAL_ERROR_MESSAGE : STREAM_ERROR_MESSAGE;
              }
            }
            sawDone = true;
          }
        }
      }

      if (!sawDone && !controller.signal.aborted && streamToken === activeStreamToken) {
        // Stream ended before done; treat as cancelled.
        finalizeAssistant();
      }
    } catch (err: unknown) {
      const isAbort =
        controller.signal.aborted ||
        (err instanceof DOMException && err.name === "AbortError");
      if (!isAbort) {
        if (isApiError(err)) {
          error.value = err.message;
        } else {
          error.value = SEND_ERROR_MESSAGE;
        }
        if (!sawDelta && !sawDone) {
          messages.value = messages.value.filter((item) => item.id !== userMessage.id);
        }
      }
    } finally {
      if (streamToken === activeStreamToken) {
        streaming.value = false;
        activeController = null;
        finalizeAssistant();
      }
    }
  }

  function cancel(): void {
    if (activeController) {
      activeStreamToken += 1;
      activeController.abort();
    }
    activeController = null;
    streaming.value = false;
    if (activeAssistantMessage) {
      activeAssistantMessage.isStreaming = false;
    }
    activeAssistantMessage = null;
  }

  async function clear(): Promise<void> {
    cancel();

    if (!toolId.value) {
      messages.value = [];
      disabledMessage.value = null;
      error.value = null;
      return;
    }

    error.value = null;
    disabledMessage.value = null;

    try {
      await apiFetch<void>(`/api/v1/editor/tools/${encodeURIComponent(toolId.value)}/chat`, {
        method: "DELETE",
      });
      messages.value = [];
    } catch (err: unknown) {
      if (isApiError(err)) {
        error.value = err.message;
      } else {
        error.value = CLEAR_ERROR_MESSAGE;
      }
    }
  }

  return {
    messages,
    streaming,
    disabledMessage,
    error,
    loadHistory,
    sendMessage,
    cancel,
    clear,
    clearError,
    clearDisabledMessage,
  };
}
