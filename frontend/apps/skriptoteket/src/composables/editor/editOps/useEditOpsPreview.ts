/**
 * Preview state and transport of one edit-ops proposal.
 *
 * Holds the server's dry-run of the proposal (diff base, response, errors,
 * confirmation) and loads it through `previewEditOps`. The request lifecycle
 * resets it when a new proposal starts, and the apply lifecycle reads it to
 * decide whether the proposal may be applied.
 */

import { computed, ref, type Ref } from "vue";

import { isApiError } from "../../../api/client";
import { previewEditOps, type EditorEditOpsPreviewResponse } from "./editorEditOpsApi";
import { buildDiffItems, uniqueTargetFiles } from "./editOpsDiff";
import { cloneVirtualFiles } from "./editOpsSnapshots";
import type {
  EditOpsDiffItem,
  EditOpsProposal,
  EditorEditOpsPreviewErrorDetails,
} from "./editOpsState";
import type { VirtualFileTextMap } from "../virtualFiles";

type UseEditOpsPreviewOptions = {
  toolId: Readonly<Ref<string>>;
  proposal: Readonly<Ref<EditOpsProposal | null>>;
  currentFiles: Readonly<Ref<VirtualFileTextMap>>;
};

export function useEditOpsPreview(options: UseEditOpsPreviewOptions) {
  const { toolId, proposal, currentFiles } = options;

  const response = ref<EditorEditOpsPreviewResponse | null>(null);
  const baseFiles = ref<VirtualFileTextMap | null>(null);
  const error = ref<string | null>(null);
  const errorDetails = ref<EditorEditOpsPreviewErrorDetails | null>(null);
  const confirmationAccepted = ref(false);
  const isPreviewing = ref(false);

  const targetFiles = computed(() => (proposal.value ? uniqueTargetFiles(proposal.value.ops) : []));

  const diffItems = computed<EditOpsDiffItem[]>(() => {
    if (!proposal.value || !response.value || !baseFiles.value) return [];
    if (!response.value.ok) return [];
    return buildDiffItems({
      targetFiles: targetFiles.value,
      beforeFiles: baseFiles.value,
      afterFiles: response.value.after_virtual_files,
    });
  });

  const hasChanges = computed(() => diffItems.value.length > 0);
  const meta = computed(() => response.value?.meta ?? null);
  const requiresConfirmation = computed(() => meta.value?.requires_confirmation ?? false);

  /** Drop the preview result and its confirmation; a new or closed proposal starts clean. */
  function reset(): void {
    response.value = null;
    baseFiles.value = null;
    error.value = null;
    errorDetails.value = null;
    confirmationAccepted.value = false;
  }

  function clearError(): void {
    error.value = null;
    errorDetails.value = null;
  }

  function setConfirmationAccepted(nextValue: boolean): void {
    confirmationAccepted.value = nextValue;
  }

  /** Show the server's refusal of an apply as the preview error of the files it was applied to. */
  function showRejectedApply(
    rejected: EditorEditOpsPreviewResponse,
    appliedTo: VirtualFileTextMap,
    message: string,
  ): void {
    response.value = rejected;
    baseFiles.value = cloneVirtualFiles(appliedTo);
    error.value = message;
    errorDetails.value = (rejected.error_details ?? [])[0] ?? null;
    confirmationAccepted.value = false;
  }

  async function loadPreview(params: {
    proposal: EditOpsProposal;
    virtualFiles: VirtualFileTextMap;
  }): Promise<EditorEditOpsPreviewResponse | null> {
    if (!toolId.value) {
      error.value = "Ingen editor hittades.";
      return null;
    }
    if (!params.proposal.correlationId) {
      error.value = "Korrelation-ID saknas. Regenerera.";
      return null;
    }

    isPreviewing.value = true;
    clearError();

    try {
      const previewed = await previewEditOps({
        toolId: toolId.value,
        activeFile: params.proposal.activeFile,
        virtualFiles: params.virtualFiles,
        ops: params.proposal.ops,
        selection: null,
        cursor: null,
        correlationId: params.proposal.correlationId,
      });

      response.value = previewed;
      baseFiles.value = cloneVirtualFiles(params.virtualFiles);

      const errors = previewed.errors ?? [];
      const details = previewed.error_details ?? [];
      error.value = previewed.ok ? null : (errors[0] ?? "Förhandsvisningen misslyckades. Regenerera.");
      errorDetails.value = details[0] ?? null;
      confirmationAccepted.value = false;

      return previewed;
    } catch (caught: unknown) {
      response.value = null;
      baseFiles.value = null;
      confirmationAccepted.value = false;
      if (isApiError(caught) || caught instanceof Error) {
        error.value = caught.message;
      } else {
        error.value = "Det gick inte att förhandsvisa förslaget.";
      }
      return null;
    } finally {
      isPreviewing.value = false;
    }
  }

  async function refreshPreview(): Promise<EditorEditOpsPreviewResponse | null> {
    if (!proposal.value) {
      reset();
      return null;
    }

    return await loadPreview({ proposal: proposal.value, virtualFiles: currentFiles.value });
  }

  return {
    response,
    error,
    errorDetails,
    confirmationAccepted,
    isPreviewing,
    diffItems,
    hasChanges,
    meta,
    requiresConfirmation,
    reset,
    clearError,
    setConfirmationAccepted,
    showRejectedApply,
    loadPreview,
    refreshPreview,
  };
}
