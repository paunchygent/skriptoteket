<script setup lang="ts">
import DraftLockBanner from "./DraftLockBanner.vue";
import EditorWorkspacePanel from "./EditorWorkspacePanel.vue";
import ScriptEditorAiPanel from "./ScriptEditorAiPanel.vue";
import WorkflowActionModal from "./WorkflowActionModal.vue";
import WorkingCopyRestorePrompt from "./WorkingCopyRestorePrompt.vue";
import SystemMessage from "../ui/SystemMessage.vue";
import { useScriptEditorPageState } from "../../composables/editor/useScriptEditorPageState";

const {
  errorMessage,
  renderError,
  draftLockError,
  isLoading,
  editor,
  isRestorePromptOpen,
  restoreDiffItems,
  workingCopyUpdatedAt,
  restoreWorkingCopy,
  handleDiscardWorkingCopy,
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
  compareActiveFileId,
  aiFields,
  createBeforeAiApplyCheckpoint,
  isChatDrawerOpen,
  handleAiProposalReady,
  slugError,
  taxonomyError,
  maintainersError,
  changeSummary,
  entrypoint,
  sourceCode,
  settingsSchemaText,
  inputSchemaText,
  usageInstructions,
  metadataTitle,
  metadataSlug,
  metadataSummary,
  selectedProfessionIds,
  selectedCategoryIds,
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
  isWorkflowSubmitting,
  isSaving,
  saveButtonLabel,
  saveButtonTitle,
  statusLine,
  isTitleSaving,
  isSummarySaving,
  editorMode,
  canEnterDiff,
  openCompareTitle,
  hasDirtyChanges,
  isHistoryDrawerOpen,
  isChatCollapsed,
  canCompareVersions,
  compareTarget,
  hasWorkingCopyHead,
  workingCopyProvider,
  checkpointSummaries,
  pinnedCheckpointCount,
  pinnedCheckpointLimit,
  isCheckpointBusy,
  lockBadge,
  canSubmitReview,
  submitReviewTooltip,
  canPublish,
  canRequestChanges,
  canRollback,
  professions,
  categories,
  isTaxonomyLoading,
  isSavingAllMetadata,
  maintainers,
  ownerUserId,
  isMaintainersLoading,
  isMaintainersSaving,
  handleSave,
  toggleHistoryDrawer,
  setEditorMode,
  toggleChatCollapsed,
  openWorkflowAction,
  closeDrawer,
  selectHistoryVersion,
  handleCompareVersion,
  openRollbackForVersion,
  saveAllMetadata,
  applySlugSuggestionFromTitle,
  addMaintainer,
  removeMaintainer,
  handleCloseCompare,
  handleCompareTargetUpdate,
  handleCompareActiveFileIdUpdate,
  createPinnedCheckpoint,
  saveTitle,
  saveSummary,
  restoreCheckpoint,
  removeCheckpoint,
  handleRestoreServerVersion,
  isWorkflowModalOpen,
  workflowActionMeta,
  workflowNote,
  showWorkflowNoteField,
  workflowError,
  submitReviewBlockedItems,
  confirmButtonClass,
  closeWorkflowModal,
  openEditorHelp,
  submitWorkflowAction,
} = useScriptEditorPageState();
</script>

<template>
  <div class="flex flex-col gap-4 min-h-0 flex-1 h-full">
    <!-- Inline errors (validation / blocking states) -->
    <SystemMessage
      v-model="errorMessage"
      variant="error"
    />
    <SystemMessage
      v-model="renderError"
      variant="error"
    />
    <SystemMessage
      v-model="draftLockError"
      variant="error"
    />

    <!-- Loading state -->
    <div
      v-if="isLoading"
      class="flex items-center gap-3 p-4 border border-navy bg-white shadow-brutal-sm text-sm text-navy/70"
    >
      <span class="inline-block w-4 h-4 border-2 border-navy/20 border-t-navy rounded-full animate-spin" />
      <span>Laddar editorn...</span>
    </div>

    <!-- Error state -->
    <div
      v-else-if="!editor"
      class="p-4 border border-navy bg-white shadow-brutal-sm text-sm text-navy/70"
    >
      Det gick inte att ladda editorn.
    </div>

    <!-- Main content -->
    <template v-else>
      <!-- PANEL 1: Editor + Test -->
      <div class="flex flex-col gap-3 min-h-0 flex-1">
        <WorkingCopyRestorePrompt
          v-if="isRestorePromptOpen"
          :is-open="isRestorePromptOpen"
          :diff-items="restoreDiffItems"
          :updated-at="workingCopyUpdatedAt"
          @restore="restoreWorkingCopy"
          @discard="handleDiscardWorkingCopy"
        />

        <DraftLockBanner
          v-if="draftLockState === 'locked'"
          :state="draftLockState"
          :message="draftLockStatus"
          :expires-at="expiresAt"
          :can-force="canForceTakeover"
          :is-busy="isLocking"
          @force="forceTakeover"
        />

        <div class="flex-1 min-h-0">
          <ScriptEditorAiPanel
            v-slot="aiPanel"
            :tool-id="editorToolId"
            :base-version-id="selectedVersion?.id ?? null"
            :is-read-only="isReadOnly"
            :editor-view="editorView"
            :compare-active-file-id="compareActiveFileId"
            :fields="aiFields"
            :create-before-apply-checkpoint="createBeforeAiApplyCheckpoint"
            :is-chat-drawer-open="isChatDrawerOpen"
            @proposal-ready="handleAiProposalReady"
          >
            <EditorWorkspacePanel
              v-model:slug-error="slugError"
              v-model:taxonomy-error="taxonomyError"
              v-model:maintainers-error="maintainersError"
              v-model:change-summary="changeSummary"
              v-model:entrypoint="entrypoint"
              v-model:source-code="sourceCode"
              v-model:settings-schema-text="settingsSchemaText"
              v-model:input-schema-text="inputSchemaText"
              v-model:usage-instructions="usageInstructions"
              v-model:metadata-title="metadataTitle"
              v-model:metadata-slug="metadataSlug"
              v-model:metadata-summary="metadataSummary"
              v-model:selected-profession-ids="selectedProfessionIds"
              v-model:selected-category-ids="selectedCategoryIds"
              :tool-id="editor.tool.id"
              :versions="editor.versions"
              :selected-version="selectedVersion"
              :entrypoint-options="entrypointOptions"
              :settings-schema="settingsSchema"
              :settings-schema-error="settingsSchemaError"
              :input-schema="inputSchema"
              :input-schema-error="inputSchemaError"
              :schema-issues-by-schema="schemaIssuesBySchema"
              :has-blocking-schema-issues="hasBlockingSchemaIssues"
              :is-schema-validating="isSchemaValidating"
              :schema-validation-error="schemaValidationError"
              :validate-schemas-now="validateSchemasNow"
              :can-edit-taxonomy="canEditTaxonomy"
              :can-edit-maintainers="canEditMaintainers"
              :can-edit-slug="canEditSlug"
              :can-rollback-versions="canRollbackVersions"
              :is-workflow-submitting="isWorkflowSubmitting"
              :is-saving="isSaving"
              :save-label="saveButtonLabel"
              :save-title="saveButtonTitle"
              :status-line="statusLine"
              :is-title-saving="isTitleSaving"
              :is-summary-saving="isSummarySaving"
              :active-mode="editorMode"
              :can-enter-diff="canEnterDiff"
              :open-compare-title="openCompareTitle"
              :has-dirty-changes="hasDirtyChanges"
              :is-read-only="isReadOnly"
              :is-history-drawer-open="isHistoryDrawerOpen"
              :is-chat-drawer-open="isChatDrawerOpen"
              :is-chat-collapsed="isChatCollapsed"
              :can-compare-versions="canCompareVersions"
              :compare-target="compareTarget"
              :compare-active-file-id="compareActiveFileId"
              :can-compare-working-copy="hasWorkingCopyHead"
              :working-copy-provider="workingCopyProvider"
              :local-checkpoints="checkpointSummaries"
              :pinned-checkpoint-count="pinnedCheckpointCount"
              :pinned-checkpoint-limit="pinnedCheckpointLimit"
              :is-checkpoint-busy="isCheckpointBusy"
              :lock-badge-label="lockBadge?.label ?? null"
              :lock-badge-tone="lockBadge?.tone ?? 'neutral'"
              :can-submit-review="canSubmitReview"
              :submit-review-tooltip="submitReviewTooltip"
              :can-publish="canPublish"
              :can-request-changes="canRequestChanges"
              :can-rollback="canRollback"
              :chat-messages="aiPanel.chatMessages"
              :chat-is-streaming="aiPanel.chatStreaming"
              :chat-disabled-message="aiPanel.chatDisabledMessage"
              :chat-error="aiPanel.chatError"
              :chat-notice-message="aiPanel.chatNoticeMessage"
              :chat-notice-variant="aiPanel.chatNoticeVariant"
              :remote-fallback-prompt="aiPanel.remoteFallbackPrompt"
              :edit-ops-request-error="aiPanel.editOpsRequestError"
              :edit-ops-disabled-message="aiPanel.editOpsDisabledMessage"
              :edit-ops-clear-draft-token="aiPanel.editOpsClearDraftToken"
              :edit-ops-state="aiPanel.editOpsState"
              :is-edit-ops-requesting="aiPanel.isEditOpsRequesting"
              :is-edit-ops-slow="aiPanel.isEditOpsSlow"
              :professions="professions"
              :categories="categories"
              :is-taxonomy-loading="isTaxonomyLoading"
              :is-saving-all-metadata="isSavingAllMetadata"
              :maintainers="maintainers"
              :owner-user-id="ownerUserId"
              :is-maintainers-loading="isMaintainersLoading"
              :is-maintainers-saving="isMaintainersSaving"
              @save="handleSave"
              @open-history-drawer="toggleHistoryDrawer"
              @select-mode="setEditorMode"
              @toggle-chat-collapsed="toggleChatCollapsed"
              @workflow-action="openWorkflowAction"
              @close-drawer="closeDrawer"
              @select-history-version="selectHistoryVersion"
              @compare-version="handleCompareVersion"
              @rollback-version="openRollbackForVersion"
              @save-all-metadata="saveAllMetadata"
              @suggest-slug-from-title="applySlugSuggestionFromTitle"
              @add-maintainer="addMaintainer"
              @remove-maintainer="removeMaintainer"
              @close-compare="handleCloseCompare"
              @update:compare-target="handleCompareTargetUpdate($event)"
              @update:compare-active-file-id="handleCompareActiveFileIdUpdate($event)"
              @create-checkpoint="createPinnedCheckpoint"
              @commit-title="saveTitle"
              @commit-summary="saveSummary"
              @restore-checkpoint="restoreCheckpoint"
              @remove-checkpoint="removeCheckpoint"
              @restore-server-version="handleRestoreServerVersion"
              @editor-view-ready="editorView = $event"
              @send-chat-message="aiPanel.sendChatMessage"
              @cancel-chat-stream="aiPanel.cancelChat"
              @clear-chat="aiPanel.clearChat"
              @clear-chat-error="aiPanel.clearChatError"
              @clear-chat-disabled="aiPanel.clearChatDisabled"
              @clear-chat-notice="aiPanel.clearChatNotice"
              @allow-remote-fallback-prompt="aiPanel.allowRemoteFallbackPrompt"
              @deny-remote-fallback-prompt="aiPanel.denyRemoteFallbackPrompt"
              @dismiss-remote-fallback-prompt="aiPanel.dismissRemoteFallbackPrompt"
              @clear-edit-ops-error="aiPanel.clearEditOpsRequestError"
              @clear-edit-ops-disabled="aiPanel.clearEditOpsDisabledMessage"
              @request-edit-ops="aiPanel.requestEditOps"
              @set-edit-ops-confirmation-accepted="aiPanel.setEditOpsConfirmationAccepted($event)"
              @apply-edit-ops="aiPanel.applyEditOps"
              @discard-edit-ops="aiPanel.discardEditOps"
              @regenerate-edit-ops="aiPanel.regenerateEditOps"
              @undo-edit-ops="aiPanel.undoEditOps"
              @redo-edit-ops="aiPanel.redoEditOps"
            />
          </ScriptEditorAiPanel>
        </div>
      </div>
    </template>
  </div>

  <WorkflowActionModal
    :is-open="isWorkflowModalOpen"
    :action-meta="workflowActionMeta"
    :note="workflowNote"
    :show-note-field="showWorkflowNoteField"
    :error="workflowError"
    :blocked-items="submitReviewBlockedItems"
    blocked-intro="Följande behöver vara klart innan du kan begära publicering:"
    blocked-help-label="Öppna hjälp"
    :is-submitting="isWorkflowSubmitting"
    :confirm-button-class="confirmButtonClass"
    @close="closeWorkflowModal"
    @help="openEditorHelp"
    @submit="submitWorkflowAction"
    @update:error="workflowError = $event"
    @update:note="workflowNote = $event"
  />
</template>
