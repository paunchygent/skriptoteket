<script setup lang="ts">
import type { EditorView } from "@codemirror/view";
import { computed } from "vue";
import type { components } from "../../api/openapi";

import type { EditorCompareTarget } from "../../composables/editor/useEditorCompareState";
import type { WorkingCopyProvider } from "../../composables/editor/useEditorCompareData";
import type { EditorWorkingCopyCheckpointSummary } from "../../composables/editor/useEditorWorkingCopy";
import type { SchemaIssuesBySchema } from "../../composables/editor/useEditorSchemaValidation";
import type { VirtualFileId } from "../../composables/editor/virtualFiles";
import { virtualFileTextFromEditorFields } from "../../composables/editor/virtualFiles";
import type { EditorChatMessage } from "../../composables/editor/useEditorChat";
import EditorComparePanel from "./EditorComparePanel.vue";
import EditorEditSuggestionPanel from "./EditorEditSuggestionPanel.vue";
import EditorInputSchemaPanel from "./EditorInputSchemaPanel.vue";
import EditorSandboxPanel from "./EditorSandboxPanel.vue";
import EditorSettingsSchemaPanel from "./EditorSettingsSchemaPanel.vue";
import EditorSourceCodePanel from "./EditorSourceCodePanel.vue";
import EditorWorkspaceDrawers from "./EditorWorkspaceDrawers.vue";
import EditorWorkspaceToolbar from "./EditorWorkspaceToolbar.vue";

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

  selectedProfessionIds: string[];
  selectedCategoryIds: string[];

  canEditTaxonomy: boolean;
  canEditMaintainers: boolean;
  canEditSlug: boolean;
  canRollbackVersions: boolean;
  isWorkflowSubmitting: boolean;
  isFocusMode: boolean;

  isSaving: boolean;
  saveLabel: string;
  saveTitle: string;
  canOpenCompare: boolean;
  openCompareTitle: string;
  hasDirtyChanges: boolean;
  isReadOnly: boolean;

  isDrawerOpen: boolean;
  isHistoryDrawerOpen: boolean;
  isMetadataDrawerOpen: boolean;
  isMaintainersDrawerOpen: boolean;
  isInstructionsDrawerOpen: boolean;
  isChatDrawerOpen: boolean;
  canCompareVersions: boolean;

  editInstruction: string;
  editSuggestion: string;
  editIsLoading: boolean;
  editError: string | null;
  canApplyEdit: boolean;

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
};

const props = defineProps<EditorWorkspacePanelProps>();

const emit = defineEmits<{
  (event: "save"): void;
  (event: "openCompare"): void;
  (event: "openHistoryDrawer"): void;
  (event: "openMetadataDrawer"): void;
  (event: "openMaintainersDrawer"): void;
  (event: "openInstructionsDrawer"): void;
  (event: "openChatDrawer"): void;
  (event: "closeDrawer"): void;
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
  (event: "update:slugError", value: string | null): void;
  (event: "update:taxonomyError", value: string | null): void;
  (event: "update:maintainersError", value: string | null): void;
  (event: "update:selectedProfessionIds", value: string[]): void;
  (event: "update:selectedCategoryIds", value: string[]): void;
  (event: "editorViewReady", value: EditorView | null): void;
  (event: "requestEditSuggestion"): void;
  (event: "applyEditSuggestion"): void;
  (event: "clearEditSuggestion"): void;
  (event: "update:editInstruction", value: string): void;
  (event: "closeCompare"): void;
  (event: "update:compareTarget", value: EditorCompareTarget | null): void;
  (event: "update:compareActiveFileId", value: VirtualFileId): void;
  (event: "createCheckpoint", label: string): void;
  (event: "restoreCheckpoint", checkpointId: string): void;
  (event: "removeCheckpoint", checkpointId: string): void;
  (event: "restoreServerVersion"): void;
  (event: "toggleFocusMode"): void;
  (event: "sendChatMessage", message: string): void;
  (event: "cancelChatStream"): void;
  (event: "clearChat"): void;
  (event: "clearChatError"): void;
  (event: "clearChatDisabled"): void;
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

const isCompareMode = computed(() => props.compareTarget !== null);
</script>

<template>
  <div class="border border-navy bg-white shadow-brutal-sm">
    <EditorWorkspaceToolbar
      :is-saving="props.isSaving"
      :is-read-only="props.isReadOnly"
      :has-dirty-changes="props.hasDirtyChanges"
      :save-label="props.saveLabel"
      :save-title="props.saveTitle"
      :can-open-compare="props.canOpenCompare"
      :open-compare-title="props.openCompareTitle"
      :change-summary="props.changeSummary"
      :input-schema-error="props.inputSchemaError"
      :settings-schema-error="props.settingsSchemaError"
      :has-blocking-schema-issues="props.hasBlockingSchemaIssues"
      :can-edit-taxonomy="props.canEditTaxonomy"
      :can-edit-maintainers="props.canEditMaintainers"
      :is-focus-mode="props.isFocusMode"
      @save="emit('save')"
      @open-compare="emit('openCompare')"
      @open-history-drawer="emit('openHistoryDrawer')"
      @open-metadata-drawer="emit('openMetadataDrawer')"
      @open-maintainers-drawer="emit('openMaintainersDrawer')"
      @open-instructions-drawer="emit('openInstructionsDrawer')"
      @open-chat-drawer="emit('openChatDrawer')"
      @toggle-focus-mode="emit('toggleFocusMode')"
      @update:change-summary="emit('update:changeSummary', $event)"
    />

    <div
      :class="[
        'grid',
        props.isDrawerOpen ? 'md:grid-cols-[minmax(0,1fr)_400px]' : 'md:grid-cols-[minmax(0,1fr)]',
      ]"
    >
      <div class="p-4 space-y-4 min-w-0">
        <EditorComparePanel
          v-if="isCompareMode && props.compareTarget"
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

        <template v-else>
          <EditorSourceCodePanel
            :entrypoint="props.entrypoint"
            :source-code="props.sourceCode"
            :is-read-only="props.isReadOnly"
            @update:source-code="emit('update:sourceCode', $event)"
            @editor-view-ready="emit('editorViewReady', $event)"
          />

          <EditorEditSuggestionPanel
            :instruction="props.editInstruction"
            :suggestion="props.editSuggestion"
            :is-loading="props.editIsLoading"
            :error="props.editError"
            :is-read-only="props.isReadOnly"
            :can-apply="props.canApplyEdit"
            @update:instruction="emit('update:editInstruction', $event)"
            @request="emit('requestEditSuggestion')"
            @apply="emit('applyEditSuggestion')"
            @clear="emit('clearEditSuggestion')"
          />

          <EditorSettingsSchemaPanel
            :settings-schema-text="props.settingsSchemaText"
            :settings-schema-error="props.settingsSchemaError"
            :schema-issues="props.schemaIssuesBySchema.settings_schema"
            :is-read-only="props.isReadOnly"
            @update:settings-schema-text="emit('update:settingsSchemaText', $event)"
          />

          <EditorInputSchemaPanel
            :input-schema-text="props.inputSchemaText"
            :input-schema-error="props.inputSchemaError"
            :schema-issues="props.schemaIssuesBySchema.input_schema"
            :is-read-only="props.isReadOnly"
            @update:input-schema-text="emit('update:inputSchemaText', $event)"
          />

          <EditorSandboxPanel
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
        </template>
      </div>

      <EditorWorkspaceDrawers
        :is-history-drawer-open="props.isHistoryDrawerOpen"
        :is-metadata-drawer-open="props.isMetadataDrawerOpen"
        :is-maintainers-drawer-open="props.isMaintainersDrawerOpen"
        :is-instructions-drawer-open="props.isInstructionsDrawerOpen"
        :is-chat-drawer-open="props.isChatDrawerOpen"
        :versions="props.versions"
        :active-version-id="activeVersionId"
        :can-compare-versions="props.canCompareVersions"
        :can-rollback-versions="props.canRollbackVersions"
        :is-workflow-submitting="props.isWorkflowSubmitting"
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
        :is-taxonomy-loading="props.isTaxonomyLoading"
        :is-saving-all-metadata="props.isSavingAllMetadata"
        :maintainers="props.maintainers"
        :owner-user-id="props.ownerUserId"
        :is-maintainers-loading="props.isMaintainersLoading"
        :is-maintainers-saving="props.isMaintainersSaving"
        :maintainers-error="props.maintainersError"
        :usage-instructions="props.usageInstructions"
        :is-saving="props.isSaving"
        :is-read-only="props.isReadOnly"
        :checkpoints="props.localCheckpoints"
        :pinned-checkpoint-count="props.pinnedCheckpointCount"
        :pinned-checkpoint-limit="props.pinnedCheckpointLimit"
        :is-checkpoint-busy="props.isCheckpointBusy"
        :chat-messages="props.chatMessages"
        :chat-is-streaming="props.chatIsStreaming"
        :chat-disabled-message="props.chatDisabledMessage"
        :chat-error="props.chatError"
        @close="emit('closeDrawer')"
        @select-history-version="emit('selectHistoryVersion', $event)"
        @compare-version="emit('compareVersion', $event)"
        @rollback-version="emit('rollbackVersion', $event)"
        @create-checkpoint="emit('createCheckpoint', $event)"
        @restore-checkpoint="emit('restoreCheckpoint', $event)"
        @remove-checkpoint="emit('removeCheckpoint', $event)"
        @restore-server-version="emit('restoreServerVersion')"
        @save-all-metadata="emit('saveAllMetadata')"
        @suggest-slug-from-title="emit('suggestSlugFromTitle')"
        @add-maintainer="emit('addMaintainer', $event)"
        @remove-maintainer="emit('removeMaintainer', $event)"
        @save="emit('save')"
        @update:usage-instructions="emit('update:usageInstructions', $event)"
        @update:metadata-title="emit('update:metadataTitle', $event)"
        @update:metadata-slug="emit('update:metadataSlug', $event)"
        @update:metadata-summary="emit('update:metadataSummary', $event)"
        @update:slug-error="emit('update:slugError', $event)"
        @update:taxonomy-error="emit('update:taxonomyError', $event)"
        @update:maintainers-error="emit('update:maintainersError', $event)"
        @update:selected-profession-ids="emit('update:selectedProfessionIds', $event)"
        @update:selected-category-ids="emit('update:selectedCategoryIds', $event)"
        @send-chat-message="emit('sendChatMessage', $event)"
        @cancel-chat-stream="emit('cancelChatStream')"
        @clear-chat="emit('clearChat')"
        @clear-chat-error="emit('clearChatError')"
        @clear-chat-disabled="emit('clearChatDisabled')"
      />
    </div>
  </div>
</template>
