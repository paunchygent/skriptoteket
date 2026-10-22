/**
 * Apply and checkpoint integration of the current edit-ops proposal.
 *
 * Applies the previewed proposal through `applyEditOps`, takes the
 * before-apply checkpoint, writes the result into the editor fields and hands
 * the before and after files to the undo history. A server refusal returns to
 * the preview as its error; a conflict reloads the preview.
 */

import { computed, ref, type Ref } from "vue";

import { isApiError } from "../../../api/client";
import { applyEditOps } from "./editorEditOpsApi";
import { applyVirtualFiles, cloneVirtualFiles, type EditorFieldRefs } from "./editOpsSnapshots";
import type { EditOpsProposal } from "./editOpsState";
import type { useEditOpsHistory } from "./useEditOpsHistory";
import type { useEditOpsPreview } from "./useEditOpsPreview";
import type { VirtualFileTextMap } from "../virtualFiles";

type UseEditOpsApplyOptions = {
  toolId: Readonly<Ref<string>>;
  isReadOnly: Readonly<Ref<boolean>>;
  isApplying: Ref<boolean>;
  fields: EditorFieldRefs;
  proposal: Ref<EditOpsProposal | null>;
  currentFiles: Readonly<Ref<VirtualFileTextMap>>;
  preview: ReturnType<typeof useEditOpsPreview>;
  history: ReturnType<typeof useEditOpsHistory>;
  createBeforeApplyCheckpoint: () => Promise<void> | void;
};

export function useEditOpsApply(options: UseEditOpsApplyOptions) {
  const {
    toolId,
    isReadOnly,
    isApplying,
    fields,
    proposal,
    currentFiles,
    preview,
    history,
    createBeforeApplyCheckpoint,
  } = options;

  const applyError = ref<string | null>(null);

  const applyDisabledReason = computed(() => {
    if (!proposal.value) return null;
    if (isReadOnly.value) return "Kodredigeraren är låst för redigering.";
    if (preview.isPreviewing.value) return "Skapar förhandsvisning...";
    if (preview.error.value) return preview.error.value;
    if (!preview.hasChanges.value) return "Inga ändringar att tillämpa.";
    if (preview.requiresConfirmation.value && !preview.confirmationAccepted.value) {
      return "Bekräfta att du har granskat ändringen.";
    }
    return null;
  });

  const canApply = computed(
    () =>
      Boolean(proposal.value) &&
      !isReadOnly.value &&
      !preview.isPreviewing.value &&
      !preview.error.value &&
      preview.hasChanges.value &&
      (!preview.requiresConfirmation.value || preview.confirmationAccepted.value) &&
      !isApplying.value,
  );

  async function applyProposal(): Promise<boolean> {
    applyError.value = null;
    history.undoError.value = null;

    const proposalValue = proposal.value;
    if (!proposalValue) return false;
    if (!proposalValue.correlationId) {
      applyError.value = "Korrelation-ID saknas. Regenerera.";
      return false;
    }
    if (isReadOnly.value) {
      applyError.value = "Kodredigeraren är låst för redigering.";
      return false;
    }

    if (!preview.response.value || preview.error.value) {
      await preview.refreshPreview();
    }

    const previewed = preview.response.value;
    if (!previewed) {
      applyError.value = preview.error.value ?? "Förhandsvisningen saknas. Försök igen.";
      return false;
    }

    if (!previewed.ok) {
      const errors = previewed.errors ?? [];
      applyError.value = errors[0] ?? "Förhandsvisningen misslyckades. Regenerera.";
      return false;
    }

    if (!preview.hasChanges.value) {
      applyError.value = "Inga ändringar att tillämpa.";
      return false;
    }

    if (previewed.meta.requires_confirmation && !preview.confirmationAccepted.value) {
      applyError.value = "Bekräfta att du har granskat ändringen innan du tillämpar.";
      return false;
    }

    const beforeFiles = cloneVirtualFiles(currentFiles.value);

    isApplying.value = true;
    try {
      const response = await applyEditOps({
        toolId: toolId.value,
        activeFile: proposalValue.activeFile,
        virtualFiles: beforeFiles,
        ops: proposalValue.ops,
        baseHash: previewed.meta.base_hash,
        patchId: previewed.meta.patch_id,
        selection: null,
        cursor: null,
        correlationId: proposalValue.correlationId,
      });

      if (!response.ok) {
        const errors = response.errors ?? [];
        applyError.value = null;
        preview.showRejectedApply(
          response,
          beforeFiles,
          errors[0] ?? "Förslaget kunde inte tillämpas. Regenerera.",
        );
        return false;
      }

      await createBeforeApplyCheckpoint();
      const afterFiles = response.after_virtual_files;
      applyVirtualFiles(fields, afterFiles);
      history.recordApplied(beforeFiles, afterFiles);
      proposal.value = null;
      preview.reset();
      return true;
    } catch (error: unknown) {
      if (isApiError(error) && error.status === 409) {
        preview.setConfirmationAccepted(false);
        const message = error.message;
        await preview.refreshPreview();
        applyError.value = message;
        return false;
      }

      applyError.value =
        isApiError(error) || error instanceof Error
          ? error.message
          : "Det gick inte att tillämpa förslaget.";
      return false;
    } finally {
      isApplying.value = false;
    }
  }

  return { applyError, applyDisabledReason, canApply, applyProposal };
}
