/**
 * Request and error lifecycle of one edit-ops request.
 *
 * Sends the teacher's message to the door, turns an answer with ops into the
 * current proposal and loads its preview, and keeps the request error, the
 * elapsed-time clock behind the slow-request hint, and the daily-limit
 * handoff: a refused allowance shows its note beside the disabled composer,
 * never as a request error.
 */

import { computed, onScopeDispose, ref, watch, type Ref } from "vue";

import { createCorrelationId } from "../../../api/correlation";
import { isApiError } from "../../../api/client";
import { aiLimitFromError, markAiDailyLimit } from "../../aiDailyLimit";
import { requestEditOps as requestEditOpsApi, type EditorEditOpsResponse } from "./editorEditOpsApi";
import type {
  EditOpsProposal,
  EditorEditOpsCursor,
  EditorEditOpsSelection,
} from "./editOpsState";
import type { useEditOpsPreview } from "./useEditOpsPreview";
import type { VirtualFileId, VirtualFileTextMap } from "../virtualFiles";

const DEFAULT_ACTIVE_FILE: VirtualFileId = "tool.py";
const SLOW_REQUEST_SECONDS = 45;

type EditOpsRequestResult = {
  response: EditorEditOpsResponse;
  message: string;
  activeFile: VirtualFileId;
  selection: EditorEditOpsSelection | null;
  cursor: EditorEditOpsCursor | null;
  correlationId: string | null;
};

type UseEditOpsRequestOptions = {
  toolId: Readonly<Ref<string>>;
  proposal: Ref<EditOpsProposal | null>;
  currentFiles: Readonly<Ref<VirtualFileTextMap>>;
  preview: ReturnType<typeof useEditOpsPreview>;
  /** Clears the apply and undo errors that belong to the previous proposal. */
  clearStaleErrors: () => void;
};

export function useEditOpsRequest(options: UseEditOpsRequestOptions) {
  const { toolId, proposal, currentFiles, preview, clearStaleErrors } = options;

  const isRequesting = ref(false);
  const requestError = ref<string | null>(null);
  const requestStartedAt = ref<number | null>(null);
  const requestNow = ref(Date.now());
  let requestInterval: ReturnType<typeof setInterval> | null = null;

  const requestElapsedSeconds = computed(() => {
    if (!isRequesting.value || requestStartedAt.value === null) return 0;
    return Math.max(0, Math.floor((requestNow.value - requestStartedAt.value) / 1000));
  });

  const isSlowRequest = computed(() => requestElapsedSeconds.value >= SLOW_REQUEST_SECONDS);

  function clearRequestError(): void {
    requestError.value = null;
  }

  async function requestEditOps(message: string): Promise<EditOpsRequestResult | null> {
    const trimmed = message.trim();
    if (!trimmed) {
      requestError.value = "Skriv ett meddelande först.";
      return null;
    }
    if (!toolId.value) {
      requestError.value = "Ingen editor hittades.";
      return null;
    }

    requestError.value = null;
    clearStaleErrors();
    preview.reset();
    isRequesting.value = true;

    const activeFile = DEFAULT_ACTIVE_FILE;
    const virtualFiles = currentFiles.value;
    const selection = null;
    const cursor = null;

    try {
      const correlationId = createCorrelationId();
      const response = await requestEditOpsApi({
        toolId: toolId.value,
        message: trimmed,
        activeFile,
        virtualFiles,
        selection,
        cursor,
        correlationId,
      });

      if (response.enabled && response.ops.length > 0) {
        const nextProposal: EditOpsProposal = {
          message: trimmed,
          assistantMessage: response.assistant_message,
          ops: response.ops,
          activeFile,
          selection,
          cursor,
          correlationId,
          createdAt: new Date().toISOString(),
        };
        proposal.value = nextProposal;
        await preview.loadPreview({ proposal: nextProposal, virtualFiles });
      } else {
        proposal.value = null;
        preview.reset();
      }

      return { response, message: trimmed, activeFile, selection, cursor, correlationId };
    } catch (error: unknown) {
      proposal.value = null;
      preview.reset();
      const limit = aiLimitFromError(error);
      if (limit) {
        // The door's limit note shows beside the disabled composer, not as a request error.
        markAiDailyLimit("full", limit);
        return null;
      }
      if (isApiError(error) || error instanceof Error) {
        requestError.value = error.message;
      } else {
        requestError.value = "Det gick inte att skapa ett AI-förslag.";
      }
      return null;
    } finally {
      isRequesting.value = false;
    }
  }

  onScopeDispose(() => {
    if (requestInterval) {
      clearInterval(requestInterval);
      requestInterval = null;
    }
  });

  watch(
    () => isRequesting.value,
    (isActive) => {
      if (requestInterval) {
        clearInterval(requestInterval);
        requestInterval = null;
      }

      if (!isActive) {
        requestStartedAt.value = null;
        requestNow.value = Date.now();
        return;
      }

      requestStartedAt.value = Date.now();
      requestNow.value = Date.now();
      requestInterval = setInterval(() => {
        requestNow.value = Date.now();
      }, 1000);
    },
    { immediate: true },
  );

  return {
    isRequesting,
    requestError,
    requestElapsedSeconds,
    isSlowRequest,
    clearRequestError,
    requestEditOps,
  };
}

export type { EditOpsRequestResult };
