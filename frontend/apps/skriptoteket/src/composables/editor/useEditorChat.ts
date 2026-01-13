import { ref, watch, type Ref } from "vue";

import { createCorrelationId } from "../../api/correlation";
import { isApiError } from "../../api/client";
import { useAuthStore } from "../../stores/auth";
import {
  clearChatHistory,
  fetchChatHistory,
  postChatStream,
  readChatErrorMessage,
} from "./chat/editorChatApi";
import { consumeChatStream } from "./chat/editorChatStreamClient";
import {
  appendMessage,
  createUserMessage,
  ensureAssistantMessage,
  finalizeAssistant,
  finalizeTurn,
  mapHistoryMessage,
} from "./chat/editorChatReducer";
import type {
  EditorChatMessage,
  EditorChatRequest,
  EditorVirtualFiles,
  NoticeVariant,
  VirtualFileId,
} from "./chat/editorChatTypes";

type UseEditorChatOptions = {
  toolId: Readonly<Ref<string>>;
  baseVersionId: Readonly<Ref<string | null>>;
  allowRemoteFallback: Readonly<Ref<boolean>>;
  activeFile?: Readonly<Ref<VirtualFileId | null>>;
  virtualFiles?: Readonly<Ref<EditorVirtualFiles | null>>;
};

const STREAM_ERROR_MESSAGE = "Det gick inte att läsa AI-svaret.";
const STREAM_PARTIAL_ERROR_MESSAGE = "Svaret kan vara ofullständigt. Skicka igen om något saknas.";
const SEND_ERROR_MESSAGE = "Det gick inte att skicka meddelandet.";
const HISTORY_ERROR_MESSAGE = "Det gick inte att hamta chatthistorik.";
const CLEAR_ERROR_MESSAGE = "Det gick inte att rensa chatten.";
const EMPTY_MESSAGE_ERROR = "Skriv ett meddelande forst.";

export function useEditorChat({
  toolId,
  baseVersionId,
  allowRemoteFallback,
  activeFile,
  virtualFiles,
}: UseEditorChatOptions) {
  const auth = useAuthStore();
  const messages = ref<EditorChatMessage[]>([]);
  const streaming = ref(false);
  const disabledMessage = ref<string | null>(null);
  const error = ref<string | null>(null);
  const noticeMessage = ref<string | null>(null);
  const noticeVariant = ref<NoticeVariant>("info");

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
    noticeMessage.value = null;
    noticeVariant.value = "info";
  }

  function clearError(): void {
    error.value = null;
  }

  function clearDisabledMessage(): void {
    disabledMessage.value = null;
  }

  function clearNoticeMessage(): void {
    noticeMessage.value = null;
    noticeVariant.value = "info";
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
    clearNoticeMessage();

    try {
      const response = await fetchChatHistory(toolId.value, 60);
      messages.value = (response.messages ?? []).map(mapHistoryMessage);
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
    clearNoticeMessage();

    const userMessage = createUserMessage(trimmed);
    messages.value = appendMessage(messages.value, userMessage);

    activeAssistantMessage = null;
    streaming.value = true;

    const streamToken = ++activeStreamToken;
    const controller = new AbortController();
    activeController = controller;
    const correlationId = createCorrelationId();

    const body: EditorChatRequest = {
      message: trimmed,
      allow_remote_fallback: allowRemoteFallback.value,
    };
    if (baseVersionId.value) {
      body.base_version_id = baseVersionId.value;
    }
    if (virtualFiles?.value) {
      body.virtual_files = virtualFiles.value;
      if (activeFile?.value) {
        body.active_file = activeFile.value;
      }
    }

    let sawDone = false;
    let sawDelta = false;

    try {
      await auth.ensureCsrfToken();
      const response = await postChatStream({
        toolId: toolId.value,
        body,
        correlationId,
        csrfToken: auth.csrfToken ?? undefined,
        signal: controller.signal,
      });

      if (response.status === 401) {
        auth.clear();
      }

      if (!response.ok || !response.body) {
        const messageText = await readChatErrorMessage(response);
        error.value = messageText || SEND_ERROR_MESSAGE;
        messages.value = messages.value.filter((item) => item.id !== userMessage.id);
        return;
      }

      const streamResult = await consumeChatStream({
        response,
        signal: controller.signal,
        onEvent: (event) => {
          if (streamToken !== activeStreamToken || controller.signal.aborted) {
            return;
          }

          switch (event.kind) {
            case "delta": {
              const result = ensureAssistantMessage({
                messages: messages.value,
                activeAssistantMessage,
                correlationId,
              });
              messages.value = result.messages;
              activeAssistantMessage = result.activeAssistantMessage;
              activeAssistantMessage.content += event.text;
              sawDelta = true;
              break;
            }
            case "meta": {
              const result = ensureAssistantMessage({
                messages: messages.value,
                activeAssistantMessage,
                correlationId: event.correlationId ?? correlationId,
                messageId: event.assistantMessageId ?? null,
                turnId: event.turnId ?? null,
              });
              messages.value = result.messages;
              activeAssistantMessage = result.activeAssistantMessage;
              if (event.turnId) {
                userMessage.turnId = event.turnId;
                activeAssistantMessage.turnId = event.turnId;
              }
              if (event.correlationId) {
                activeAssistantMessage.correlationId = event.correlationId;
              }
              break;
            }
            case "notice": {
              noticeMessage.value = event.message;
              noticeVariant.value = event.variant ?? "info";
              break;
            }
            case "done": {
              if (typeof event.enabled === "boolean" && !event.enabled) {
                const messageText = String(event.message ?? "").trim();
                disabledMessage.value = messageText || null;
                const code = String(event.code ?? "").trim();
                if (!activeAssistantMessage) {
                  const result = ensureAssistantMessage({
                    messages: messages.value,
                    activeAssistantMessage,
                    correlationId,
                  });
                  messages.value = result.messages;
                  activeAssistantMessage = result.activeAssistantMessage;
                }
                finalizeTurn({
                  messages: messages.value,
                  userMessage,
                  activeAssistantMessage,
                  status: "failed",
                  failureOutcome: code || null,
                });
                if (activeAssistantMessage) {
                  activeAssistantMessage.isStreaming = false;
                }
              } else if (event.reason === "error") {
                if (!activeAssistantMessage) {
                  const result = ensureAssistantMessage({
                    messages: messages.value,
                    activeAssistantMessage,
                    correlationId,
                  });
                  messages.value = result.messages;
                  activeAssistantMessage = result.activeAssistantMessage;
                }
                finalizeTurn({
                  messages: messages.value,
                  userMessage,
                  activeAssistantMessage,
                  status: "failed",
                });
                error.value = sawDelta ? STREAM_PARTIAL_ERROR_MESSAGE : STREAM_ERROR_MESSAGE;
              } else if (event.reason === "cancelled") {
                if (!activeAssistantMessage) {
                  const result = ensureAssistantMessage({
                    messages: messages.value,
                    activeAssistantMessage,
                    correlationId,
                  });
                  messages.value = result.messages;
                  activeAssistantMessage = result.activeAssistantMessage;
                }
                finalizeTurn({
                  messages: messages.value,
                  userMessage,
                  activeAssistantMessage,
                  status: "cancelled",
                });
              } else {
                finalizeTurn({
                  messages: messages.value,
                  userMessage,
                  activeAssistantMessage,
                  status: "complete",
                });
              }
              sawDone = true;
              break;
            }
          }
        },
      });

      sawDelta = sawDelta || streamResult.sawDelta;
      sawDone = sawDone || streamResult.sawDone;

      if (!sawDone && !controller.signal.aborted && streamToken === activeStreamToken) {
        // Stream ended before done; treat as cancelled.
        if (activeAssistantMessage) {
          finalizeTurn({
            messages: messages.value,
            userMessage,
            activeAssistantMessage,
            status: "cancelled",
          });
        }
        finalizeAssistant(activeAssistantMessage);
        activeAssistantMessage = null;
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
        finalizeAssistant(activeAssistantMessage);
        activeAssistantMessage = null;
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
      activeAssistantMessage.status = "cancelled";
    }
    activeAssistantMessage = null;
  }

  async function clear(): Promise<void> {
    cancel();

    if (!toolId.value) {
      messages.value = [];
      disabledMessage.value = null;
      error.value = null;
      clearNoticeMessage();
      return;
    }

    error.value = null;
    disabledMessage.value = null;
    clearNoticeMessage();

    try {
      await clearChatHistory(toolId.value);
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
    noticeMessage,
    noticeVariant,
    loadHistory,
    sendMessage,
    cancel,
    clear,
    clearError,
    clearDisabledMessage,
    clearNoticeMessage,
  };
}
