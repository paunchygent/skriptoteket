import { computed } from "vue";

import type { components } from "../../api/openapi";
import { useScriptEditorCompareMode } from "./useScriptEditorCompareMode";
import { useScriptEditorCoreState } from "./useScriptEditorCoreState";
import { useScriptEditorDrawers } from "./useScriptEditorDrawers";
import { useScriptEditorFocusEffects } from "./useScriptEditorFocusEffects";
import { useScriptEditorMetadataState } from "./useScriptEditorMetadataState";
import { useScriptEditorWorkingCopyState } from "./useScriptEditorWorkingCopyState";
import { useScriptEditorWorkflowState } from "./useScriptEditorWorkflowState";
import { useUnsavedChangesGuards } from "./useUnsavedChangesGuards";

type VersionState = components["schemas"]["VersionState"];

export function useScriptEditorPageState() {
  const {
    route,
    router,
    layout,
    focusMode,
    notify,
    renderError,
    editorView,
    editor,
    entrypoint,
    sourceCode,
    settingsSchemaText,
    inputSchemaText,
    usageInstructions,
    initialSnapshot,
    changeSummary,
    metadataTitle,
    metadataSummary,
    metadataSlug,
    isLoading,
    isSaving,
    isMetadataSaving,
    isSlugSaving,
    errorMessage,
    slugError,
    selectedVersion,
    editorToolId,
    saveButtonLabel,
    saveButtonTitle,
    hasDirtyChanges,
    save,
    saveToolMetadata,
    saveToolSlug,
    applySlugSuggestionFromTitle,
    loadEditor,
    inputSchema,
    inputSchemaError,
    settingsSchema,
    settingsSchemaError,
    schemaIssuesBySchema,
    hasBlockingSchemaIssues,
    isSchemaValidating,
    schemaValidationError,
    validateSchemasNow,
    canEditTaxonomy,
    canEditMaintainers,
    canEditSlug,
    canRollbackVersions,
    canForceTakeover,
    currentUserId,
    entrypointOptions,
    draftLockState,
    isReadOnly,
    isLocking,
    expiresAt,
    draftLockStatus,
    draftLockError,
    forceTakeover,
    lockBadge,
  } = useScriptEditorCoreState();

  const { confirmDiscardChanges } = useUnsavedChangesGuards({ hasDirtyChanges, isSaving });
  const drawers = useScriptEditorDrawers({ route, router, confirmDiscardChanges });
  const {
    isHistoryDrawerOpen,
    isChatDrawerOpen,
    isChatCollapsed,
    toggleHistoryDrawer,
    toggleChatCollapsed,
    closeDrawer,
    selectHistoryVersion,
  } = drawers;

  const compare = useScriptEditorCompareMode({
    route,
    router,
    editor,
    selectedVersion,
    onCompareVersion: closeDrawer,
  });

  const workingCopy = useScriptEditorWorkingCopyState({
    userId: currentUserId,
    toolId: editorToolId,
    selectedVersion,
    hasDirtyChanges,
    initialSnapshot,
    fields: {
      entrypoint,
      sourceCode,
      settingsSchemaText,
      inputSchemaText,
      usageInstructions,
    },
    notify,
    confirmDiscardChanges,
  });

  const metadata = useScriptEditorMetadataState({
    toolId: editorToolId,
    canEditTaxonomy,
    canEditMaintainers,
    canEditSlug,
    notify,
    isMetadataSaving,
    isSlugSaving,
    saveToolMetadata,
    saveToolSlug,
    editorMode: compare.editorMode,
  });

  const workflow = useScriptEditorWorkflowState({
    selectedVersion,
    metadataSlug,
    selectedProfessionIds: metadata.selectedProfessionIds,
    selectedCategoryIds: metadata.selectedCategoryIds,
    route,
    router,
    reloadEditor: loadEditor,
    notify,
  });

  useScriptEditorFocusEffects({
    layout,
    focusMode,
    editor,
    isChatDrawerOpen,
  });

  async function handleSave(): Promise<void> {
    await workingCopy.createBeforeSaveCheckpoint();
    await save({ validateSchemasNow, schemaValidationError });
  }

  function versionLabel(state: VersionState): string {
    const labels: Record<VersionState, string> = {
      draft: "Arbetsversion",
      in_review: "Granskning",
      active: "Publicerad",
      archived: "Arkiverad",
    };
    return labels[state] ?? state;
  }

  const statusLine = computed(() => {
    if (!editor.value) return "";
    const publication = editor.value.tool.is_published ? "Publicerad" : "Ej publicerad";
    const versionSegment = selectedVersion.value
      ? `v${selectedVersion.value.version_number} · ${versionLabel(selectedVersion.value.state)}`
      : "Ny arbetsversion";
    return `${publication} · ${versionSegment}`;
  });

  return {
    errorMessage,
    renderError,
    draftLockError,
    isLoading,
    editor,
    isRestorePromptOpen: workingCopy.isRestorePromptOpen,
    restoreDiffItems: workingCopy.restoreDiffItems,
    workingCopyUpdatedAt: workingCopy.workingCopyUpdatedAt,
    restoreWorkingCopy: workingCopy.restoreWorkingCopy,
    handleDiscardWorkingCopy: workingCopy.handleDiscardWorkingCopy,
    draftLockState,
    draftLockStatus,
    expiresAt,
    canForceTakeover,
    isLocking,
    forceTakeover,
    editorToolId,
    selectedVersion,
    isReadOnly,
    editorView,
    compareActiveFileId: compare.compareActiveFileId,
    aiFields: workingCopy.aiFields,
    createBeforeAiApplyCheckpoint: workingCopy.createBeforeAiApplyCheckpoint,
    isChatDrawerOpen,
    handleAiProposalReady: compare.handleAiProposalReady,
    slugError,
    taxonomyError: metadata.taxonomyError,
    maintainersError: metadata.maintainersError,
    changeSummary,
    entrypoint,
    sourceCode,
    settingsSchemaText,
    inputSchemaText,
    usageInstructions,
    metadataTitle,
    metadataSlug,
    metadataSummary,
    selectedProfessionIds: metadata.selectedProfessionIds,
    selectedCategoryIds: metadata.selectedCategoryIds,
    entrypointOptions,
    settingsSchema,
    settingsSchemaError,
    inputSchema,
    inputSchemaError,
    schemaIssuesBySchema,
    hasBlockingSchemaIssues,
    isSchemaValidating,
    schemaValidationError,
    validateSchemasNow,
    canEditTaxonomy,
    canEditMaintainers,
    canEditSlug,
    canRollbackVersions,
    isWorkflowSubmitting: workflow.isWorkflowSubmitting,
    isSaving,
    saveButtonLabel,
    saveButtonTitle,
    statusLine,
    isTitleSaving: metadata.isTitleSaving,
    isSummarySaving: metadata.isSummarySaving,
    editorMode: compare.editorMode,
    canEnterDiff: compare.canEnterDiff,
    openCompareTitle: compare.openCompareTitle,
    hasDirtyChanges,
    isHistoryDrawerOpen,
    isChatCollapsed,
    canCompareVersions: compare.canCompareVersions,
    compareTarget: compare.compareTarget,
    hasWorkingCopyHead: workingCopy.hasWorkingCopyHead,
    workingCopyProvider: workingCopy.workingCopyProvider,
    checkpointSummaries: workingCopy.checkpointSummaries,
    pinnedCheckpointCount: workingCopy.pinnedCheckpointCount,
    pinnedCheckpointLimit: workingCopy.pinnedCheckpointLimit,
    isCheckpointBusy: workingCopy.isCheckpointBusy,
    lockBadge,
    canSubmitReview: workflow.canSubmitReview,
    submitReviewTooltip: workflow.submitReviewTooltip,
    canPublish: workflow.canPublish,
    canRequestChanges: workflow.canRequestChanges,
    canRollback: workflow.canRollback,
    professions: metadata.professions,
    categories: metadata.categories,
    isTaxonomyLoading: metadata.isTaxonomyLoading,
    isSavingAllMetadata: metadata.isSavingAllMetadata,
    maintainers: metadata.maintainers,
    ownerUserId: metadata.ownerUserId,
    isMaintainersLoading: metadata.isMaintainersLoading,
    isMaintainersSaving: metadata.isMaintainersSaving,
    handleSave,
    toggleHistoryDrawer,
    setEditorMode: compare.setEditorMode,
    toggleChatCollapsed,
    openWorkflowAction: workflow.openWorkflowAction,
    closeDrawer,
    selectHistoryVersion,
    handleCompareVersion: compare.handleCompareVersion,
    openRollbackForVersion: workflow.openRollbackForVersion,
    saveAllMetadata: metadata.saveAllMetadata,
    applySlugSuggestionFromTitle,
    addMaintainer: metadata.addMaintainer,
    removeMaintainer: metadata.removeMaintainer,
    handleCloseCompare: compare.handleCloseCompare,
    handleCompareTargetUpdate: compare.handleCompareTargetUpdate,
    handleCompareActiveFileIdUpdate: compare.handleCompareActiveFileIdUpdate,
    createPinnedCheckpoint: workingCopy.createPinnedCheckpoint,
    saveTitle: metadata.saveTitle,
    saveSummary: metadata.saveSummary,
    restoreCheckpoint: workingCopy.restoreCheckpoint,
    removeCheckpoint: workingCopy.removeCheckpoint,
    handleRestoreServerVersion: workingCopy.handleRestoreServerVersion,
    isWorkflowModalOpen: workflow.isWorkflowModalOpen,
    workflowActionMeta: workflow.workflowActionMeta,
    workflowNote: workflow.workflowNote,
    showWorkflowNoteField: workflow.showWorkflowNoteField,
    workflowError: workflow.workflowError,
    submitReviewBlockedItems: workflow.submitReviewBlockedItems,
    confirmButtonClass: workflow.confirmButtonClass,
    closeWorkflowModal: workflow.closeWorkflowModal,
    openEditorHelp: workflow.openEditorHelp,
    submitWorkflowAction: workflow.submitWorkflowAction,
  };
}
