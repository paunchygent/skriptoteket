import { ref, watch } from "vue";

import { isApiError } from "../../api/client";
import { clearChatHistory, fetchChatHistory } from "./chat/editorChatApi";
import { mapHistoryMessage } from "./chat/editorChatReducer";
import type { EditorChatMessage, NoticeVariant } from "./chat/editorChatTypes";
import { useEditorChatRequest, type UseEditorChatOptions } from "./useEditorChatRequest";
import { useEditorChatReveal } from "./useEditorChatReveal";

const HISTORY_ERROR_MESSAGE = "Det gick inte att hamta chatthistorik.";
const CLEAR_ERROR_MESSAGE = "Det gick inte att rensa chatten.";

export function useEditorChat(options: UseEditorChatOptions) {
  const { toolId } = options;
  const messages = ref<EditorChatMessage[]>([]);
  const streaming = ref(false);
  const disabledMessage = ref<string | null>(null);
  const error = ref<string | null>(null);
  const noticeMessage = ref<string | null>(null);
  const noticeVariant = ref<NoticeVariant>("info");
  const { scheduleRevealTick, resetReveal } = useEditorChatReveal(messages);
  const { sendMessage, cancel, resetRequest } = useEditorChatRequest(options, {
    messages,
    streaming,
    disabledMessage,
    error,
    noticeMessage,
    noticeVariant,
    clearNoticeMessage,
    scheduleRevealTick,
  });

  function resetLocal(): void {
    resetRequest();
    messages.value = [];
    disabledMessage.value = null;
    error.value = null;
    noticeMessage.value = null;
    noticeVariant.value = "info";
    resetReveal();
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
