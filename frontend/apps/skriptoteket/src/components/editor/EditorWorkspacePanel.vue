<script setup lang="ts">
import type { EditorView } from "@codemirror/view";
import { computed, ref } from "vue";
import type { components } from "../../api/openapi";

import type { EditorCompareTarget } from "../../composables/editor/useEditorCompareState";
import type { EditOpsPanelState } from "../../composables/editor/useEditorEditOps";
import type { WorkingCopyProvider } from "../../composables/editor/useEditorCompareData";
import type { EditorWorkingCopyCheckpointSummary } from "../../composables/editor/useEditorWorkingCopy";
import type { SchemaIssuesBySchema } from "../../composables/editor/useEditorSchemaValidation";
import type { VirtualFileId } from "../../composables/editor/virtualFiles";
import { virtualFileTextFromEditorFields } from "../../composables/editor/virtualFiles";
import type { EditorChatMessage } from "../../composables/editor/useEditorChat";
import type { SubmitReviewTooltip } from "../../composables/editor/useEditorWorkflowActions";
import EditorComparePanel from "./EditorComparePanel.vue";
import EditorEditOpsPanel from "./EditorEditOpsPanel.vue";
import EditorInputSchemaPanel from "./EditorInputSchemaPanel.vue";
import EditorSandboxPanel from "./EditorSandboxPanel.vue";
import EditorSettingsSchemaPanel from "./EditorSettingsSchemaPanel.vue";
import EditorSourceCodePanel from "./EditorSourceCodePanel.vue";
import EditorWorkspaceDrawers from "./EditorWorkspaceDrawers.vue";
import EditorWorkspaceModeSelector from "./EditorWorkspaceModeSelector.vue";
import EditorWorkspaceToolbar from "./EditorWorkspaceToolbar.vue";
import ScriptEditorHeaderPanel from "./ScriptEditorHeaderPanel.vue";
import WorkflowContextButtons from "./WorkflowContextButtons.vue";
import InstructionsDrawer from "./InstructionsDrawer.vue";
import MaintainersDrawer from "./MaintainersDrawer.vue";
import MetadataDrawer from "./MetadataDrawer.vue";
import VersionHistoryDrawer from "./VersionHistoryDrawer.vue";

type EditorVersionSummary = components["schemas"]["EditorVersionSummary"];
type ProfessionItem = components["schemas"]["ProfessionItem"];
type CategoryItem = components["schemas"]["CategoryItem"];
type MaintainerSummary = components["schemas"]["MaintainerSummary"];
type CreateDraftVersionRequest = components["schemas"]["CreateDraftVersionRequest"];
type ToolInputSchema = NonNullable<CreateDraftVersionRequest["input_schema"]>;
type ToolSettingsSchema = NonNullable<CreateDraftVersionRequest["settings_schema"]>;

type EditorWorkspacePanelProps = {
  toolId: string;
  versions: EditorVersionSummary[];
  selectedVersion: EditorVersionSummary | null;
  entrypointOptions: string[];

  changeSummary: string;
  entrypoint: string;
  sourceCode: string;
  settingsSchemaText: string;
  inputSchemaText: string;
  settingsSchema: ToolSettingsSchema | null;
  settingsSchemaError: string | null;
  inputSchema: ToolInputSchema;
  inputSchemaError: string | null;
  schemaIssuesBySchema: SchemaIssuesBySchema;
  hasBlockingSchemaIssues: boolean;
  isSchemaValidating: boolean;
  schemaValidationError: string | null;
  validateSchemasNow: () => Promise<boolean>;
  usageInstructions: string;

  metadataTitle: string;
  metadataSlug: string;
  metadataSummary: string;
  slugError: string | null;
  statusLine: string;
  isTitleSaving: boolean;
  isSummarySaving: boolean;

  selectedProfessionIds: string[];
  selectedCategoryIds: string[];

  canEditTaxonomy: boolean;
  canEditMaintainers: boolean;
  canEditSlug: boolean;
  canRollbackVersions: boolean;
  isWorkflowSubmitting: boolean;

  isSaving: boolean;
  saveLabel: string;
  saveTitle: string;
  openCompareTitle: string;
  activeMode: "source" | "diff" | "metadata" | "test";
  canEnterDiff: boolean;
  hasDirtyChanges: boolean;
  isReadOnly: boolean;

  isHistoryDrawerOpen: boolean;
  isChatDrawerOpen: boolean;
  isChatCollapsed: boolean;
  canCompareVersions: boolean;
  lockBadgeLabel: string | null;
  lockBadgeTone: "success" | "neutral";
  canSubmitReview: boolean;
  submitReviewTooltip: SubmitReviewTooltip | null;
  canPublish: boolean;
  canRequestChanges: boolean;
  canRollback: boolean;

  professions: ProfessionItem[];
  categories: CategoryItem[];
  taxonomyError: string | null;
  isTaxonomyLoading: boolean;
  isSavingAllMetadata: boolean;

  maintainers: MaintainerSummary[];
  ownerUserId: string | null;
  isMaintainersLoading: boolean;
  isMaintainersSaving: boolean;
  maintainersError: string | null;

  compareTarget: EditorCompareTarget | null;
  compareActiveFileId: VirtualFileId | null;
  canCompareWorkingCopy: boolean;
  workingCopyProvider?: WorkingCopyProvider | null;
  localCheckpoints: EditorWorkingCopyCheckpointSummary[];
  pinnedCheckpointCount: number;
  pinnedCheckpointLimit: number;
  isCheckpointBusy: boolean;

  chatMessages: EditorChatMessage[];
  chatIsStreaming: boolean;
  chatDisabledMessage: string | null;
  chatError: string | null;

  editOpsState: EditOpsPanelState;
  isEditOpsRequesting: boolean;
};

const props = defineProps<EditorWorkspacePanelProps>();

const emit = defineEmits<{
  (event: "save"): void;
  (event: "openHistoryDrawer"): void;
  (event: "workflowAction", action: "submit_review" | "publish" | "request_changes" | "rollback"): void;
  (event: "selectMode", mode: "source" | "diff" | "metadata" | "test"): void;
  (event: "closeDrawer"): void;
  (event: "toggleChatCollapsed"): void;
  (event: "selectHistoryVersion", versionId: string): void;
  (event: "compareVersion", versionId: string): void;
  (event: "rollbackVersion", versionId: string): void;
  (event: "saveAllMetadata"): void;
  (event: "suggestSlugFromTitle"): void;
  (event: "addMaintainer", email: string): void;
  (event: "removeMaintainer", userId: string): void;
  (event: "update:changeSummary", value: string): void;
  (event: "update:entrypoint", value: string): void;
  (event: "update:sourceCode", value: string): void;
  (event: "update:settingsSchemaText", value: string): void;
  (event: "update:inputSchemaText", value: string): void;
  (event: "update:usageInstructions", value: string): void;
  (event: "update:metadataTitle", value: string): void;
  (event: "update:metadataSlug", value: string): void;
  (event: "update:metadataSummary", value: string): void;
  (event: "commitTitle"): void;
  (event: "commitSummary"): void;
  (event: "update:slugError", value: string | null): void;
  (event: "update:taxonomyError", value: string | null): void;
  (event: "update:maintainersError", value: string | null): void;
  (event: "update:selectedProfessionIds", value: string[]): void;
  (event: "update:selectedCategoryIds", value: string[]): void;
  (event: "editorViewReady", value: EditorView | null): void;
  (event: "closeCompare"): void;
  (event: "update:compareTarget", value: EditorCompareTarget | null): void;
  (event: "update:compareActiveFileId", value: VirtualFileId): void;
  (event: "createCheckpoint", label: string): void;
  (event: "restoreCheckpoint", checkpointId: string): void;
  (event: "removeCheckpoint", checkpointId: string): void;
  (event: "restoreServerVersion"): void;
  (event: "sendChatMessage", message: string): void;
  (event: "cancelChatStream"): void;
  (event: "clearChat"): void;
  (event: "clearChatError"): void;
  (event: "clearChatDisabled"): void;
  (event: "requestEditOps", message: string): void;
  (event: "applyEditOps"): void;
  (event: "discardEditOps"): void;
  (event: "regenerateEditOps"): void;
  (event: "undoEditOps"): void;
}>();

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
      class="grid flex-1 min-h-0 h-full gap-y-3 transition-[grid-template-columns] duration-200 ease-out md:grid-cols-[minmax(0,1fr)_var(--chat-column-width)] md:grid-rows-[auto_minmax(0,1fr)_auto]"
      :style="{ '--chat-column-width': chatColumnWidth, '--chat-rail-width': chatRailWidth }"
    >
      <div class="min-w-0 px-3 pt-3 md:col-span-2 md:row-start-1">
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
              :save-label="props.saveLabel"
              :save-title="props.saveTitle"
              :change-summary="props.changeSummary"
              :input-schema-error="props.inputSchemaError"
              :settings-schema-error="props.settingsSchemaError"
              :has-blocking-schema-issues="props.hasBlockingSchemaIssues"
              :is-checkpoint-busy="props.isCheckpointBusy"
              :lock-badge-label="props.lockBadgeLabel"
              :lock-badge-tone="props.lockBadgeTone"
              @save="emit('save')"
              @open-history-drawer="emit('openHistoryDrawer')"
              @create-checkpoint="emit('createCheckpoint', $event)"
              @update:change-summary="emit('update:changeSummary', $event)"
            />
          </div>

          <div class="flex items-start justify-end md:col-start-2 md:row-start-1">
            <span class="text-[10px] font-semibold uppercase tracking-wide text-navy/60 text-right">
              {{ props.statusLine }}
            </span>
          </div>

          <div class="flex items-start justify-end md:col-start-2 md:row-start-2 md:mt-0.5">
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

          <div class="flex items-end justify-end md:col-start-2 md:row-start-3 md:self-end">
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
        class="min-h-0 min-w-0 px-3 md:col-start-1 md:row-start-2 flex flex-col h-full overflow-hidden"
        :class="{ 'pb-3': !showsSchemaPanels }"
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
              class="p-4 border border-navy bg-white shadow-brutal-sm text-sm text-navy/70"
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
          <div class="h-full min-h-0 overflow-y-auto">
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
              v-if="props.editOpsState.proposal || props.editOpsState.hasUndoSnapshot"
              :state="props.editOpsState"
              @apply="emit('applyEditOps')"
              @discard="emit('discardEditOps')"
              @regenerate="emit('regenerateEditOps')"
              @undo="emit('undoEditOps')"
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
        class="min-h-0 min-w-0 px-3 pb-3 md:col-start-1 md:row-start-3"
      >
        <section class="border border-navy/20 bg-white shadow-brutal-sm">
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
            class="grid lg:grid-cols-2 divide-x divide-navy/20"
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
        class="min-h-0 min-w-0 md:col-start-2 md:row-start-2 md:row-span-2 md:border-l md:border-t md:border-navy md:bg-canvas md:shadow-brutal-sm"
      >
        <EditorWorkspaceDrawers
          variant="column"
          :is-chat-drawer-open="props.isChatDrawerOpen"
          :is-chat-collapsed="props.isChatCollapsed"
          :chat-messages="props.chatMessages"
          :chat-is-streaming="props.chatIsStreaming"
          :chat-disabled-message="props.chatDisabledMessage"
          :chat-error="props.chatError"
          :is-edit-ops-loading="props.isEditOpsRequesting"
          @close="emit('closeDrawer')"
          @toggle-chat-collapsed="emit('toggleChatCollapsed')"
          @send-chat-message="emit('sendChatMessage', $event)"
          @cancel-chat-stream="emit('cancelChatStream')"
          @clear-chat="emit('clearChat')"
          @clear-chat-error="emit('clearChatError')"
          @clear-chat-disabled="emit('clearChatDisabled')"
          @request-edit-ops="emit('requestEditOps', $event)"
        />
      </div>
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
