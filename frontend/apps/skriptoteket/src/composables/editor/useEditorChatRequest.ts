import type { Ref } from "vue";

import { createCorrelationId } from "../../api/correlation";
import { isApiError } from "../../api/client";
import { useAuthStore } from "../../stores/auth";
import { postChatStream, readChatErrorMessage } from "./chat/editorChatApi";
import { consumeChatStream } from "./chat/editorChatStreamClient";
import {
  appendMessage,
  createUserMessage,
  ensureAssistantMessage,
  finalizeAssistant,
  finalizeTurn,
} from "./chat/editorChatReducer";
import type {
  EditorChatMessage,
  EditorChatRequest,
  EditorVirtualFiles,
  NoticeVariant,
  VirtualFileId,
} from "./chat/editorChatTypes";

export type UseEditorChatOptions = {
  toolId: Readonly<Ref<string>>;
  baseVersionId: Readonly<Ref<string | null>>;
  activeFile?: Readonly<Ref<VirtualFileId | null>>;
  virtualFiles?: Readonly<Ref<EditorVirtualFiles | null>>;
};

const STREAM_ERROR_MESSAGE = "Det gick inte att läsa AI-svaret.";
const STREAM_PARTIAL_ERROR_MESSAGE = "Svaret kan vara ofullständigt. Skicka igen om något saknas.";
const SEND_ERROR_MESSAGE = "Det gick inte att skicka meddelandet.";
const EMPTY_MESSAGE_ERROR = "Skriv ett meddelande forst.";

type EditorChatRequestState = {
  messages: Ref<EditorChatMessage[]>;
  streaming: Ref<boolean>;
  disabledMessage: Ref<string | null>;
  error: Ref<string | null>;
  noticeMessage: Ref<string | null>;
  noticeVariant: Ref<NoticeVariant>;
  clearNoticeMessage: () => void;
  scheduleRevealTick: () => void;
};

/** Owns a chat turn from session capture through cancellation and finalization. */
export function useEditorChatRequest(
  { toolId, baseVersionId, activeFile, virtualFiles }: UseEditorChatOptions,
  {
    messages,
    streaming,
    disabledMessage,
    error,
    noticeMessage,
    noticeVariant,
    clearNoticeMessage,
    scheduleRevealTick,
  }: EditorChatRequestState,
) {
  const auth = useAuthStore();
  let activeController: AbortController | null = null;
  let activeStreamToken = 0;
  let activeAssistantMessage: EditorChatMessage | null = null;

  function resetRequest(): void {
    if (activeController) {
      activeController.abort();
    }
    activeController = null;
    activeStreamToken += 1;
    streaming.value = false;
    activeAssistantMessage = null;
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

    const requestSession = auth.captureSession();
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
      auth.requireCurrentSession(requestSession);
      const response = await postChatStream({
        toolId: toolId.value,
        body,
        correlationId,
        session: requestSession,
        signal: controller.signal,
      });

      if (!auth.isCurrentSession(requestSession)) return;
      if (!response.ok || !response.body) {
        const messageText = await readChatErrorMessage(response);
        if (!auth.isCurrentSession(requestSession)) return;
        if (response.status === 401) auth.clear(requestSession);
        const result = ensureAssistantMessage({
          messages: messages.value,
          activeAssistantMessage,
          correlationId,
        });
        messages.value = result.messages;
        activeAssistantMessage = result.activeAssistantMessage;
        activeAssistantMessage.content = messageText || SEND_ERROR_MESSAGE;
        activeAssistantMessage.visibleContent = "";
        finalizeTurn({
          messages: messages.value,
          userMessage,
          activeAssistantMessage,
          status: "failed",
        });
        return;
      }

      const streamResult = await consumeChatStream({
        response,
        signal: controller.signal,
        onEvent: (event) => {
          if (
            !auth.isCurrentSession(requestSession) ||
            streamToken !== activeStreamToken || controller.signal.aborted
          ) {
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
              scheduleRevealTick();
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
              scheduleRevealTick();
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
                if (activeAssistantMessage) {
                  activeAssistantMessage.content = messageText || SEND_ERROR_MESSAGE;
                  activeAssistantMessage.visibleContent = "";
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
                const failureText = sawDelta ? STREAM_PARTIAL_ERROR_MESSAGE : STREAM_ERROR_MESSAGE;
                if (activeAssistantMessage) {
                  const hadContent = activeAssistantMessage.content.trim().length > 0;
                  if (sawDelta && hadContent) {
                    activeAssistantMessage.content = `${activeAssistantMessage.content}\n\n${failureText}`;
                  } else {
                    activeAssistantMessage.content = failureText;
                  }
                  if (!sawDelta || !hadContent) {
                    activeAssistantMessage.visibleContent = "";
                  }
                }
                finalizeTurn({
                  messages: messages.value,
                  userMessage,
                  activeAssistantMessage,
                  status: "failed",
                });
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
              scheduleRevealTick();
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
      if (!auth.isCurrentSession(requestSession)) return;
      const isAbort =
        controller.signal.aborted ||
        (err instanceof DOMException && err.name === "AbortError");
      if (!isAbort) {
        const failureText = isApiError(err) ? err.message : SEND_ERROR_MESSAGE;
        if (!activeAssistantMessage) {
          const result = ensureAssistantMessage({
            messages: messages.value,
            activeAssistantMessage,
            correlationId,
          });
          messages.value = result.messages;
          activeAssistantMessage = result.activeAssistantMessage;
        }
        if (activeAssistantMessage) {
          const hadContent = activeAssistantMessage.content.trim().length > 0;
          if (sawDelta && hadContent) {
            activeAssistantMessage.content = `${activeAssistantMessage.content}\n\n${failureText}`;
          } else {
            activeAssistantMessage.content = failureText;
          }
          if (!sawDelta || !hadContent) {
            activeAssistantMessage.visibleContent = "";
          }
        }
        finalizeTurn({
          messages: messages.value,
          userMessage,
          activeAssistantMessage,
          status: "failed",
        });
        sawDone = true;
      }
    } finally {
      if (streamToken === activeStreamToken) {
        streaming.value = false;
        activeController = null;
        finalizeAssistant(activeAssistantMessage);
        scheduleRevealTick();
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

  return { sendMessage, cancel, resetRequest };
}
