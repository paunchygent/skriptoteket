<script setup lang="ts">
import type { EditorView } from "@codemirror/view";
import { computed } from "vue";
import type { components } from "../../api/openapi";

import type { SchemaIssuesBySchema } from "../../composables/editor/useEditorSchemaValidation";
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

  isSaving: boolean;
  hasDirtyChanges: boolean;
  isReadOnly: boolean;

  isDrawerOpen: boolean;
  isHistoryDrawerOpen: boolean;
  isMetadataDrawerOpen: boolean;
  isMaintainersDrawerOpen: boolean;
  isInstructionsDrawerOpen: boolean;

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
};

const props = defineProps<EditorWorkspacePanelProps>();

const emit = defineEmits<{
  (event: "save"): void;
  (event: "openHistoryDrawer"): void;
  (event: "openMetadataDrawer"): void;
  (event: "openMaintainersDrawer"): void;
  (event: "openInstructionsDrawer"): void;
  (event: "closeDrawer"): void;
  (event: "selectHistoryVersion", versionId: string): void;
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
}>();

const activeVersionId = computed(() => props.selectedVersion?.id ?? null);
</script>

<template>
  <div class="border border-navy bg-white shadow-brutal-sm">
    <EditorWorkspaceToolbar
      :is-saving="props.isSaving"
      :is-read-only="props.isReadOnly"
      :has-dirty-changes="props.hasDirtyChanges"
      :change-summary="props.changeSummary"
      :input-schema-error="props.inputSchemaError"
      :settings-schema-error="props.settingsSchemaError"
      :has-blocking-schema-issues="props.hasBlockingSchemaIssues"
      :can-edit-taxonomy="props.canEditTaxonomy"
      :can-edit-maintainers="props.canEditMaintainers"
      @save="emit('save')"
      @open-history-drawer="emit('openHistoryDrawer')"
      @open-metadata-drawer="emit('openMetadataDrawer')"
      @open-maintainers-drawer="emit('openMaintainersDrawer')"
      @open-instructions-drawer="emit('openInstructionsDrawer')"
      @update:change-summary="emit('update:changeSummary', $event)"
    />

    <div
      :class="[
        'grid',
        props.isDrawerOpen ? 'md:grid-cols-[minmax(0,1fr)_400px]' : 'md:grid-cols-[minmax(0,1fr)]',
      ]"
    >
      <div class="p-4 space-y-4 min-w-0">
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
      </div>

      <EditorWorkspaceDrawers
        :is-history-drawer-open="props.isHistoryDrawerOpen"
        :is-metadata-drawer-open="props.isMetadataDrawerOpen"
        :is-maintainers-drawer-open="props.isMaintainersDrawerOpen"
        :is-instructions-drawer-open="props.isInstructionsDrawerOpen"
        :versions="props.versions"
        :active-version-id="activeVersionId"
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
        @close="emit('closeDrawer')"
        @select-history-version="emit('selectHistoryVersion', $event)"
        @rollback-version="emit('rollbackVersion', $event)"
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
      />
    </div>
  </div>
</template>
