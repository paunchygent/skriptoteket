import type { EditorView } from "@codemirror/view";
import { computed, ref, type Ref } from "vue";

import { virtualFilesFingerprint, type EditorFieldRefs } from "./editOps/editOpsSnapshots";
import { buildEditOpsPanelState, type EditOpsPanelState, type EditOpsProposal } from "./editOps/editOpsState";
import { useEditOpsApply } from "./editOps/useEditOpsApply";
import { useEditOpsHistory } from "./editOps/useEditOpsHistory";
import { useEditOpsPreview } from "./editOps/useEditOpsPreview";
import { useEditOpsRequest } from "./editOps/useEditOpsRequest";
import { virtualFileTextFromEditorFields } from "./virtualFiles";

type UseEditorEditOpsOptions = {
  toolId: Readonly<Ref<string>>;
  isReadOnly: Readonly<Ref<boolean>>;
  editorView: Readonly<Ref<EditorView | null>>;
  fields: EditorFieldRefs;
  createBeforeApplyCheckpoint: () => Promise<void> | void;
};

/**
 * One edit-ops proposal from request to undo. The request, preview, apply and
 * undo/redo lifecycles live in `./editOps/`; this composable owns the shared
 * proposal and the editor's current files, wires the lifecycles together and
 * exposes the panel state.
 */
export function useEditorEditOps(options: UseEditorEditOpsOptions) {
  const { toolId, isReadOnly, fields, createBeforeApplyCheckpoint } = options;

  const proposal = ref<EditOpsProposal | null>(null);
  const isApplying = ref(false);

  const currentFiles = computed(() =>
    virtualFileTextFromEditorFields({
      entrypoint: fields.entrypoint.value,
      sourceCode: fields.sourceCode.value,
      settingsSchemaText: fields.settingsSchemaText.value,
      inputSchemaText: fields.inputSchemaText.value,
      usageInstructions: fields.usageInstructions.value,
    }),
  );
  const currentFingerprint = computed(() => virtualFilesFingerprint(currentFiles.value));

  const preview = useEditOpsPreview({ toolId, proposal, currentFiles });
  const history = useEditOpsHistory({ isReadOnly, isApplying, fields, currentFingerprint });
  const apply = useEditOpsApply({
    toolId,
    isReadOnly,
    isApplying,
    fields,
    proposal,
    currentFiles,
    preview,
    history,
    createBeforeApplyCheckpoint,
  });
  const request = useEditOpsRequest({
    toolId,
    proposal,
    currentFiles,
    preview,
    clearStaleErrors: () => {
      apply.applyError.value = null;
      history.undoError.value = null;
    },
  });

  function discardProposal(): void {
    proposal.value = null;
    preview.reset();
    apply.applyError.value = null;
  }

  const panelState = computed<EditOpsPanelState>(() =>
    buildEditOpsPanelState({
      proposal: proposal.value,
      diffItems: preview.diffItems.value,
      previewMeta: preview.meta.value,
      previewError: preview.error.value,
      previewErrorDetails: preview.errorDetails.value,
      applyError: apply.applyError.value,
      undoError: history.undoError.value,
      canApply: apply.canApply.value,
      applyDisabledReason: apply.applyDisabledReason.value,
      canUndo: history.canUndo.value,
      undoDisabledReason: history.undoDisabledReason.value,
      canRedo: history.canRedo.value,
      redoDisabledReason: history.redoDisabledReason.value,
      lastApplied: history.lastApplied.value,
      aiPosition: history.aiPosition.value,
      isApplying: isApplying.value,
      requiresConfirmation: preview.requiresConfirmation.value,
      confirmationAccepted: preview.confirmationAccepted.value,
    }),
  );

  return {
    proposal,
    isRequesting: request.isRequesting,
    requestElapsedSeconds: request.requestElapsedSeconds,
    isSlowRequest: request.isSlowRequest,
    requestError: request.requestError,
    clearRequestError: request.clearRequestError,
    panelState,
    diffItems: preview.diffItems,
    previewError: preview.error,
    previewErrorDetails: preview.errorDetails,
    previewMeta: preview.meta,
    applyError: apply.applyError,
    undoError: history.undoError,
    canApply: apply.canApply,
    applyDisabledReason: apply.applyDisabledReason,
    canUndo: history.canUndo,
    undoDisabledReason: history.undoDisabledReason,
    isApplying,
    requiresConfirmation: preview.requiresConfirmation,
    confirmationAccepted: preview.confirmationAccepted,
    setConfirmationAccepted: preview.setConfirmationAccepted,
    requestEditOps: request.requestEditOps,
    applyProposal: apply.applyProposal,
    discardProposal,
    undoLastApply: history.undoLastApply,
    redoLastApply: history.redoLastApply,
    canRedo: history.canRedo,
    redoDisabledReason: history.redoDisabledReason,
  };
}
