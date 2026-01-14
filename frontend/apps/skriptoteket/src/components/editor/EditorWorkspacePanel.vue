<script setup lang="ts">
import { computed, defineAsyncComponent, ref } from "vue";

import { virtualFileTextFromEditorFields } from "../../composables/editor/virtualFiles";
import type { EditorWorkspacePanelEmits, EditorWorkspacePanelProps } from "./EditorWorkspacePanel.types";
import EditorComparePanel from "./EditorComparePanel.vue";
import EditorInputSchemaPanel from "./EditorInputSchemaPanel.vue";
import EditorSandboxPanel from "./EditorSandboxPanel.vue";
import EditorSettingsSchemaPanel from "./EditorSettingsSchemaPanel.vue";
import EditorSourceCodePanel from "./EditorSourceCodePanel.vue";
import EditorWorkspaceModeSelector from "./EditorWorkspaceModeSelector.vue";
import EditorWorkspaceToolbar from "./EditorWorkspaceToolbar.vue";
import ScriptEditorHeaderPanel from "./ScriptEditorHeaderPanel.vue";
import WorkflowContextButtons from "./WorkflowContextButtons.vue";
import InstructionsDrawer from "./InstructionsDrawer.vue";
import MaintainersDrawer from "./MaintainersDrawer.vue";
import MetadataDrawer from "./MetadataDrawer.vue";
import VersionHistoryDrawer from "./VersionHistoryDrawer.vue";

const EditorEditOpsPanel = defineAsyncComponent(() => import("./EditorEditOpsPanel.vue"));
const EditorWorkspaceDrawers = defineAsyncComponent(() => import("./EditorWorkspaceDrawers.vue"));

const props = defineProps<EditorWorkspacePanelProps>();

const emit = defineEmits<EditorWorkspacePanelEmits>();

const activeVersionId = computed(() => props.selectedVersion?.id ?? null);

const baseFiles = computed(() =>
  virtualFileTextFromEditorFields({
    entrypoint: props.entrypoint,
    sourceCode: props.sourceCode,
    settingsSchemaText: props.settingsSchemaText,
    inputSchemaText: props.inputSchemaText,
    usageInstructions: props.usageInstructions,
  }),
);

const isDiffMode = computed(() => props.activeMode === "diff");
const isMetadataMode = computed(() => props.activeMode === "metadata");
const isTestMode = computed(() => props.activeMode === "test");
const showsSchemaPanels = computed(() => props.activeMode === "source");
const isSchemaCollapsed = ref(false);
const chatRailWidth = "64px";
const chatColumnWidth = computed(() => {
  if (!props.isChatDrawerOpen) return "0px";
  return props.isChatCollapsed ? chatRailWidth : "clamp(280px, 34vw, 360px)";
});
</script>

<template>
  <div class="border border-navy bg-white shadow-brutal-sm flex flex-col min-h-0 h-full">
    <div
      class="grid flex-1 min-h-0 h-full gap-y-3 transition-[grid-template-columns] duration-200 ease-out lg:grid-cols-[minmax(0,1fr)_var(--chat-column-width)] lg:grid-rows-[auto_minmax(0,1fr)_auto]"
      :style="{ '--chat-column-width': chatColumnWidth, '--chat-rail-width': chatRailWidth }"
    >
      <div class="min-w-0 px-3 pt-3 lg:col-span-2 lg:row-start-1">
        <div
          class="grid gap-x-4 gap-y-2 border-b border-navy/20 pb-3 md:grid-cols-[minmax(0,1fr)_auto] md:grid-rows-[auto_auto_auto]"
        >
          <div class="min-w-0 md:col-start-1 md:row-start-1">
            <ScriptEditorHeaderPanel
              section="title"
              :metadata-title="props.metadataTitle"
              :metadata-summary="props.metadataSummary"
              :tool-slug="props.metadataSlug"
              :is-title-saving="props.isTitleSaving"
              :is-summary-saving="props.isSummarySaving"
              @update:metadata-title="emit('update:metadataTitle', $event)"
              @update:metadata-summary="emit('update:metadataSummary', $event)"
              @commit-title="emit('commitTitle')"
              @commit-summary="emit('commitSummary')"
            />
          </div>

          <div class="min-w-0 md:col-start-1 md:row-start-2 md:-mt-0.5">
            <ScriptEditorHeaderPanel
              section="summary"
              :metadata-title="props.metadataTitle"
              :metadata-summary="props.metadataSummary"
              :tool-slug="props.metadataSlug"
              :is-title-saving="props.isTitleSaving"
              :is-summary-saving="props.isSummarySaving"
              @update:metadata-title="emit('update:metadataTitle', $event)"
              @update:metadata-summary="emit('update:metadataSummary', $event)"
              @commit-title="emit('commitTitle')"
              @commit-summary="emit('commitSummary')"
            />
          </div>

          <div class="min-w-0 md:col-start-1 md:row-start-3 md:self-end">
            <EditorWorkspaceToolbar
              :is-saving="props.isSaving"
              :is-read-only="props.isReadOnly"
              :has-dirty-changes="props.hasDirtyChanges"
              :is-chat-collapsed="props.isChatCollapsed"
              :save-label="props.saveLabel"
              :save-title="props.saveTitle"
              :change-summary="props.changeSummary"
              :input-schema-error="props.inputSchemaError"
              :settings-schema-error="props.settingsSchemaError"
              :has-blocking-schema-issues="props.hasBlockingSchemaIssues"
              :is-checkpoint-busy="props.isCheckpointBusy"
              :lock-badge-label="props.lockBadgeLabel"
              :lock-badge-tone="props.lockBadgeTone"
              :ai-status="props.editOpsState.aiStatus"
              :ai-applied-at="props.editOpsState.aiAppliedAt"
              :ai-can-undo="props.editOpsState.canUndo"
              :ai-undo-disabled-reason="props.editOpsState.undoDisabledReason"
              :ai-can-redo="props.editOpsState.canRedo"
              :ai-redo-disabled-reason="props.editOpsState.redoDisabledReason"
              :ai-error="props.editOpsState.undoError"
              @save="emit('save')"
              @open-history-drawer="emit('openHistoryDrawer')"
              @create-checkpoint="emit('createCheckpoint', $event)"
              @update:change-summary="emit('update:changeSummary', $event)"
              @toggle-chat-collapsed="emit('toggleChatCollapsed')"
              @undo-ai="emit('undoEditOps')"
              @redo-ai="emit('redoEditOps')"
            />
          </div>

          <div class="flex items-start justify-start md:justify-end md:col-start-2 md:row-start-1">
            <span class="text-[10px] font-semibold uppercase tracking-wide text-navy/60 md:text-right">
              {{ props.statusLine }}
            </span>
          </div>

          <div class="flex items-start justify-start md:justify-end md:col-start-2 md:row-start-2 md:mt-0.5">
            <WorkflowContextButtons
              :can-submit-review="props.canSubmitReview"
              :submit-review-tooltip="props.submitReviewTooltip"
              :can-publish="props.canPublish"
              :can-request-changes="props.canRequestChanges"
              :can-rollback="props.canRollback"
              :is-submitting="props.isWorkflowSubmitting"
              @action="emit('workflowAction', $event)"
            />
          </div>

          <div class="flex items-end justify-start md:justify-end md:col-start-2 md:row-start-3 md:self-end">
            <EditorWorkspaceModeSelector
              :active-mode="props.activeMode"
              :can-enter-diff="props.canEnterDiff"
              :open-compare-title="props.openCompareTitle"
              @select="emit('selectMode', $event)"
            />
          </div>
        </div>
      </div>

      <div
        class="min-h-0 min-w-0 px-3 lg:col-start-1 lg:row-start-2 flex flex-col h-full overflow-hidden"
        :class="{ 'pb-3': !showsSchemaPanels }"
        data-editor-panel="mode"
      >
        <template v-if="isDiffMode">
          <div class="h-full min-h-0 flex flex-col gap-4">
            <EditorComparePanel
              v-if="props.compareTarget"
              class="flex-1 min-h-0"
              :versions="props.versions"
              :base-version="props.selectedVersion"
              :base-files="baseFiles"
              :compare-target="props.compareTarget"
              :active-file-id="props.compareActiveFileId"
              :base-is-dirty="props.hasDirtyChanges"
              :can-compare-working-copy="props.canCompareWorkingCopy"
              :working-copy-provider="props.workingCopyProvider"
              @close="emit('closeCompare')"
              @update-compare-target-value="
                emit(
                  'update:compareTarget',
                  $event === 'working' ? { kind: 'working' } : { kind: 'version', versionId: $event },
                )
              "
              @update-active-file-id="emit('update:compareActiveFileId', $event)"
            />
            <div
              v-else
              class="flex-1 min-h-0 panel-inset p-4 text-sm text-navy/70 flex items-center justify-center"
              data-editor-empty="diff"
            >
              Ingen diff att visa.
            </div>
          </div>
        </template>

        <template v-else-if="isMetadataMode">
          <div class="h-full min-h-0 overflow-y-auto">
            <div class="grid gap-3 lg:grid-cols-2 content-start">
              <MetadataDrawer
                variant="panel"
                :is-open="true"
                :metadata-title="props.metadataTitle"
                :metadata-slug="props.metadataSlug"
                :metadata-summary="props.metadataSummary"
                :can-edit-slug="props.canEditSlug"
                :slug-error="props.slugError"
                :professions="props.professions"
                :categories="props.categories"
                :selected-profession-ids="props.selectedProfessionIds"
                :selected-category-ids="props.selectedCategoryIds"
                :taxonomy-error="props.taxonomyError"
                :is-loading="props.isTaxonomyLoading"
                :is-saving="props.isSavingAllMetadata"
                @close="emit('closeDrawer')"
                @save="emit('saveAllMetadata')"
                @update:metadata-title="emit('update:metadataTitle', $event)"
                @update:metadata-slug="emit('update:metadataSlug', $event)"
                @update:metadata-summary="emit('update:metadataSummary', $event)"
                @update:slug-error="emit('update:slugError', $event)"
                @suggest-slug-from-title="emit('suggestSlugFromTitle')"
                @update:selected-profession-ids="emit('update:selectedProfessionIds', $event)"
                @update:selected-category-ids="emit('update:selectedCategoryIds', $event)"
                @update:taxonomy-error="emit('update:taxonomyError', $event)"
              />

              <InstructionsDrawer
                variant="panel"
                :is-open="true"
                :usage-instructions="props.usageInstructions"
                :is-saving="props.isSaving"
                :is-read-only="props.isReadOnly"
                @close="emit('closeDrawer')"
                @save="emit('save')"
                @update:usage-instructions="emit('update:usageInstructions', $event)"
              />

              <MaintainersDrawer
                v-if="props.canEditMaintainers"
                class="lg:col-span-2"
                variant="panel"
                :is-open="true"
                :maintainers="props.maintainers"
                :owner-user-id="props.ownerUserId"
                :is-superuser="props.canRollbackVersions"
                :is-loading="props.isMaintainersLoading"
                :is-saving="props.isMaintainersSaving"
                :error="props.maintainersError"
                @close="emit('closeDrawer')"
                @add="emit('addMaintainer', $event)"
                @remove="emit('removeMaintainer', $event)"
                @update:error="emit('update:maintainersError', $event)"
              />
            </div>
          </div>
        </template>

        <template v-else-if="isTestMode">
          <div class="flex flex-col h-full min-h-0 overflow-y-auto">
            <EditorSandboxPanel
              class="flex-1 min-h-0"
              variant="mode"
              :tool-id="props.toolId"
              :selected-version="props.selectedVersion"
              :entrypoint-options="props.entrypointOptions"
              :entrypoint="props.entrypoint"
              :is-read-only="props.isReadOnly"
              :source-code="props.sourceCode"
              :usage-instructions="props.usageInstructions"
              :settings-schema="props.settingsSchema"
              :settings-schema-error="props.settingsSchemaError"
              :input-schema="props.inputSchema"
              :input-schema-error="props.inputSchemaError"
              :has-blocking-schema-issues="props.hasBlockingSchemaIssues"
              :schema-validation-error="props.schemaValidationError"
              :validate-schemas-now="props.validateSchemasNow"
              @update:entrypoint="emit('update:entrypoint', $event)"
            />
          </div>
        </template>

        <template v-else>
          <div class="h-full min-h-0 flex flex-col gap-3">
            <EditorEditOpsPanel
              v-if="props.editOpsState.proposal"
              :state="props.editOpsState"
              @apply="emit('applyEditOps')"
              @discard="emit('discardEditOps')"
              @regenerate="emit('regenerateEditOps')"
              @set-confirmation-accepted="emit('setEditOpsConfirmationAccepted', $event)"
            />
            <div class="flex-1 min-h-0">
              <EditorSourceCodePanel
                :entrypoint="props.entrypoint"
                :source-code="props.sourceCode"
                :is-read-only="props.isReadOnly"
                @update:source-code="emit('update:sourceCode', $event)"
                @editor-view-ready="emit('editorViewReady', $event)"
              />
            </div>
          </div>
        </template>
      </div>

      <div
        v-if="showsSchemaPanels"
        class="min-h-0 min-w-0 px-3 pb-3 lg:col-start-1 lg:row-start-3"
      >
        <section class="panel-inset">
          <div class="border-b border-navy/20 px-3 py-2 flex items-center justify-between gap-3">
            <span class="text-[10px] font-semibold uppercase tracking-wide text-navy/60">
              Indata & inst&auml;llningar (JSON)
            </span>
            <button
              type="button"
              class="btn-ghost shadow-none px-2 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] border-navy/30 bg-canvas"
              :aria-expanded="!isSchemaCollapsed"
              @click="isSchemaCollapsed = !isSchemaCollapsed"
            >
              {{ isSchemaCollapsed ? "Visa" : "D&ouml;lj" }}
            </button>
          </div>
          <div
            v-show="!isSchemaCollapsed"
            class="grid md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-navy/20"
            :aria-hidden="isSchemaCollapsed"
          >
            <EditorInputSchemaPanel
              variant="inline"
              :input-schema-text="props.inputSchemaText"
              :input-schema-error="props.inputSchemaError"
              :schema-issues="props.schemaIssuesBySchema.input_schema"
              :is-read-only="props.isReadOnly"
              @update:input-schema-text="emit('update:inputSchemaText', $event)"
            />

            <EditorSettingsSchemaPanel
              variant="inline"
              :settings-schema-text="props.settingsSchemaText"
              :settings-schema-error="props.settingsSchemaError"
              :schema-issues="props.schemaIssuesBySchema.settings_schema"
              :is-read-only="props.isReadOnly"
              @update:settings-schema-text="emit('update:settingsSchemaText', $event)"
            />
          </div>
        </section>
      </div>

      <div
        v-if="props.isChatDrawerOpen"
        class="hidden min-h-0 min-w-0 lg:block lg:col-start-2 lg:row-start-2 lg:row-span-2 lg:border-l-2 lg:border-t-2 lg:border-navy/20 lg:bg-canvas lg:shadow-none"
      >
        <EditorWorkspaceDrawers
          variant="column"
          :is-chat-drawer-open="props.isChatDrawerOpen"
          :is-chat-collapsed="props.isChatCollapsed"
          :chat-messages="props.chatMessages"
          :chat-is-streaming="props.chatIsStreaming"
          :chat-disabled-message="props.chatDisabledMessage"
          :chat-error="props.chatError"
          :chat-notice-message="props.chatNoticeMessage"
          :chat-notice-variant="props.chatNoticeVariant"
          :remote-fallback-prompt="props.remoteFallbackPrompt"
          :is-edit-ops-loading="props.isEditOpsRequesting"
          :is-edit-ops-slow="props.isEditOpsSlow"
          :edit-ops-error="props.editOpsRequestError"
          :edit-ops-disabled-message="props.editOpsDisabledMessage"
          :edit-ops-clear-draft-token="props.editOpsClearDraftToken"
          @close="emit('closeDrawer')"
          @toggle-chat-collapsed="emit('toggleChatCollapsed')"
          @send-chat-message="emit('sendChatMessage', $event)"
          @cancel-chat-stream="emit('cancelChatStream')"
          @clear-chat="emit('clearChat')"
          @clear-chat-error="emit('clearChatError')"
          @clear-chat-disabled="emit('clearChatDisabled')"
          @clear-chat-notice="emit('clearChatNotice')"
          @allow-remote-fallback-prompt="emit('allowRemoteFallbackPrompt')"
          @deny-remote-fallback-prompt="emit('denyRemoteFallbackPrompt')"
          @dismiss-remote-fallback-prompt="emit('dismissRemoteFallbackPrompt')"
          @clear-edit-ops-error="emit('clearEditOpsError')"
          @clear-edit-ops-disabled="emit('clearEditOpsDisabled')"
          @request-edit-ops="emit('requestEditOps', $event)"
        />
      </div>
    </div>

    <div
      v-if="props.isChatDrawerOpen && !props.isChatCollapsed"
      class="lg:hidden"
    >
      <EditorWorkspaceDrawers
        variant="drawer"
        :is-chat-drawer-open="props.isChatDrawerOpen"
        :is-chat-collapsed="props.isChatCollapsed"
        :chat-messages="props.chatMessages"
        :chat-is-streaming="props.chatIsStreaming"
        :chat-disabled-message="props.chatDisabledMessage"
        :chat-error="props.chatError"
        :chat-notice-message="props.chatNoticeMessage"
        :chat-notice-variant="props.chatNoticeVariant"
        :remote-fallback-prompt="props.remoteFallbackPrompt"
        :is-edit-ops-loading="props.isEditOpsRequesting"
        :is-edit-ops-slow="props.isEditOpsSlow"
        :edit-ops-error="props.editOpsRequestError"
        :edit-ops-disabled-message="props.editOpsDisabledMessage"
        :edit-ops-clear-draft-token="props.editOpsClearDraftToken"
        @close="emit('closeDrawer')"
        @toggle-chat-collapsed="emit('toggleChatCollapsed')"
        @send-chat-message="emit('sendChatMessage', $event)"
        @cancel-chat-stream="emit('cancelChatStream')"
        @clear-chat="emit('clearChat')"
        @clear-chat-error="emit('clearChatError')"
        @clear-chat-disabled="emit('clearChatDisabled')"
        @clear-chat-notice="emit('clearChatNotice')"
        @allow-remote-fallback-prompt="emit('allowRemoteFallbackPrompt')"
        @deny-remote-fallback-prompt="emit('denyRemoteFallbackPrompt')"
        @dismiss-remote-fallback-prompt="emit('dismissRemoteFallbackPrompt')"
        @clear-edit-ops-error="emit('clearEditOpsError')"
        @clear-edit-ops-disabled="emit('clearEditOpsDisabled')"
        @request-edit-ops="emit('requestEditOps', $event)"
      />
    </div>

    <VersionHistoryDrawer
      v-if="props.isHistoryDrawerOpen"
      variant="popover"
      :is-open="props.isHistoryDrawerOpen"
      :versions="props.versions"
      :active-version-id="activeVersionId"
      :compare-version-id="props.compareTarget?.kind === 'version' ? props.compareTarget.versionId : null"
      :can-compare="props.canCompareVersions"
      :can-rollback="props.canRollbackVersions"
      :is-submitting="props.isWorkflowSubmitting"
      :checkpoints="props.localCheckpoints"
      @close="emit('closeDrawer')"
      @select="emit('selectHistoryVersion', $event)"
      @compare="emit('compareVersion', $event)"
      @rollback="emit('rollbackVersion', $event)"
      @restore-checkpoint="emit('restoreCheckpoint', $event)"
      @remove-checkpoint="emit('removeCheckpoint', $event)"
      @restore-server-version="emit('restoreServerVersion')"
    />
  </div>
</template>
