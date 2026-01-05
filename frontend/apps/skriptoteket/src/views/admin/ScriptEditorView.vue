<script setup lang="ts">
import type { EditorView } from "@codemirror/view";
import { computed, ref, shallowRef } from "vue";
import { useRoute, useRouter } from "vue-router";
import type { components } from "../../api/openapi";
import DraftLockBanner from "../../components/editor/DraftLockBanner.vue";
import EditorWorkspacePanel from "../../components/editor/EditorWorkspacePanel.vue";
import ScriptEditorHeaderPanel from "../../components/editor/ScriptEditorHeaderPanel.vue";
import SystemMessage from "../../components/ui/SystemMessage.vue";
import WorkflowActionModal from "../../components/editor/WorkflowActionModal.vue";
import { useEditorEditSuggestions } from "../../composables/editor/useEditorEditSuggestions";
import { useEditorCompareState, type EditorCompareTarget } from "../../composables/editor/useEditorCompareState";
import { useEditorSchemaParsing } from "../../composables/editor/useEditorSchemaParsing";
import { useEditorSchemaValidation } from "../../composables/editor/useEditorSchemaValidation";
import { useEditorWorkflowActions } from "../../composables/editor/useEditorWorkflowActions";
import { useDraftLock } from "../../composables/editor/useDraftLock";
import { useScriptEditorDrawers } from "../../composables/editor/useScriptEditorDrawers";
import { useScriptEditor } from "../../composables/editor/useScriptEditor";
import { useToolMaintainers } from "../../composables/editor/useToolMaintainers";
import { useToolTaxonomy } from "../../composables/editor/useToolTaxonomy";
import { useUnsavedChangesGuards } from "../../composables/editor/useUnsavedChangesGuards";
import { isVirtualFileId } from "../../composables/editor/virtualFiles";
import type { UiNotifier } from "../../composables/notify";
import { useToast } from "../../composables/useToast";
import { useAuthStore } from "../../stores/auth";
type VersionState = components["schemas"]["VersionState"];
const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const toast = useToast();
const notify: UiNotifier = {
  info: (message: string) => toast.info(message),
  success: (message: string) => toast.success(message),
  warning: (message: string) => toast.warning(message),
  failure: (message: string) => toast.failure(message),
};
const toolId = computed(() => {
  const param = route.params.toolId;
  return typeof param === "string" ? param : "";
});
const versionId = computed(() => {
  const param = route.params.versionId;
  return typeof param === "string" ? param : "";
});
const canEditTaxonomy = computed(() => auth.hasAtLeastRole("admin"));
const canEditMaintainers = computed(() => auth.hasAtLeastRole("admin"));
const canRollbackVersions = computed(() => auth.hasAtLeastRole("superuser"));
const {
  editor,
  entrypoint,
  sourceCode,
  settingsSchemaText,
  inputSchemaText,
  usageInstructions,
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
  hasDirtyChanges,
  save,
  saveToolMetadata,
  saveToolSlug,
  applySlugSuggestionFromTitle,
  loadEditor,
} = useScriptEditor({
  toolId,
  versionId,
  route,
	  router,
	  notify,
	});
const { inputSchema, inputSchemaError, settingsSchema, settingsSchemaError } = useEditorSchemaParsing({
  inputSchemaText,
  settingsSchemaText,
});
const draftHeadId = computed(() => editor.value?.draft_head_id ?? null);
const initialDraftLock = computed(() => editor.value?.draft_lock ?? null);
const canForceTakeover = computed(() => auth.hasAtLeastRole("admin"));
const {
  state: draftLockState,
  isReadOnly,
  isLocking,
  expiresAt,
  statusMessage: draftLockStatus,
  lockError: draftLockError,
  forceTakeover,
} = useDraftLock({
  toolId: editorToolId,
  draftHeadId,
  initialLock: initialDraftLock,
});
const {
  issuesBySchema: schemaIssuesBySchema,
  hasBlockingIssues: hasBlockingSchemaIssues,
  isValidating: isSchemaValidating,
  validationError: schemaValidationError,
  validateNow: validateSchemasNow,
} = useEditorSchemaValidation({
  toolId: editorToolId,
  inputSchema,
  settingsSchema,
  inputSchemaError,
  settingsSchemaError,
  isReadOnly,
});
const canEditSlug = computed(() => auth.hasAtLeastRole("admin") && editor.value?.tool.is_published === false);
const {
  isModalOpen: isWorkflowModalOpen,
  activeAction: activeWorkflowAction,
  actionMeta: workflowActionMeta,
  showNoteField: showWorkflowNoteField,
  note: workflowNote,
  workflowError,
  isSubmitting: isWorkflowSubmitting,
  canSubmitReview,
  canPublish,
  canRequestChanges,
  canRollback,
  openRollbackForVersion,
  openAction: openWorkflowAction,
  closeAction: closeWorkflowModal,
  submitAction: submitWorkflowAction,
} = useEditorWorkflowActions({
  selectedVersion,
  route,
  router,
  reloadEditor: loadEditor,
  notify,
});
const {
  professions,
  categories,
  selectedProfessionIds,
  selectedCategoryIds,
  taxonomyError,
  isTaxonomyLoading,
  isTaxonomySaving,
  saveTaxonomy,
} = useToolTaxonomy({
  toolId: editorToolId,
  canEdit: canEditTaxonomy,
  notify,
});
const {
  maintainers,
  ownerUserId,
  isLoading: isMaintainersLoading,
  isSaving: isMaintainersSaving,
  error: maintainersError,
  loadMaintainers,
  addMaintainer,
  removeMaintainer,
} = useToolMaintainers({
  toolId: editorToolId,
  canEdit: canEditMaintainers,
  notify,
});
const entrypointOptions = ["run_tool"];
const editorView = shallowRef<EditorView | null>(null);
const {
  instruction: editInstruction,
  suggestion: editSuggestion,
  isLoading: isEditLoading,
  error: editError,
  canApply: canApplyEdit,
  requestSuggestion: requestEditSuggestion,
  applySuggestion: applyEditSuggestion,
  clearSuggestion: clearEditSuggestion,
} = useEditorEditSuggestions({
  editorView,
  isReadOnly,
});

const isSavingAllMetadata = computed(
  () => isMetadataSaving.value || isTaxonomySaving.value || isSlugSaving.value,
);
async function saveAllMetadata(): Promise<void> {
  if (canEditSlug.value) {
    await saveToolSlug();
  }
  await saveToolMetadata();
  if (canEditTaxonomy.value) {
    await saveTaxonomy();
  }
}

const isTitleSaving = ref(false);
const isSummarySaving = ref(false);

async function handleSave(): Promise<void> {
  await save({ validateSchemasNow, schemaValidationError });
}

async function saveTitle(): Promise<void> {
  isTitleSaving.value = true;
  try {
    await saveToolMetadata();
  } finally {
    isTitleSaving.value = false;
  }
}

async function saveSummary(): Promise<void> {
  isSummarySaving.value = true;
  try {
    await saveToolMetadata();
  } finally {
    isSummarySaving.value = false;
  }
}

const { confirmDiscardChanges } = useUnsavedChangesGuards({ hasDirtyChanges, isSaving });
const drawers = useScriptEditorDrawers({
  route,
  router,
  editorToolId,
  canEditTaxonomy,
  canEditMaintainers,
  loadMaintainers,
  confirmDiscardChanges,
});
const {
  isDrawerOpen,
  isHistoryDrawerOpen,
  isMetadataDrawerOpen,
  isMaintainersDrawerOpen,
  isInstructionsDrawerOpen,
  toggleHistoryDrawer,
  toggleMetadataDrawer,
  toggleMaintainersDrawer,
  toggleInstructionsDrawer,
  closeDrawer,
  selectHistoryVersion,
} = drawers;

const compare = useEditorCompareState({ route, router });
const compareTarget = compare.compareTarget;
const compareActiveFileId = compare.activeFileId;

async function handleCompareVersion(versionId: string): Promise<void> {
  await compare.toggleCompareVersionId(versionId);
  closeDrawer();
}

async function handleCompareTargetUpdate(target: EditorCompareTarget | null): Promise<void> {
  await compare.setCompareTarget(target);
}

async function handleCompareActiveFileIdUpdate(fileId: unknown): Promise<void> {
  if (!isVirtualFileId(fileId)) {
    return;
  }
  await compare.setActiveFileId(fileId);
}

async function handleCloseCompare(): Promise<void> {
  await compare.closeCompare();
}

const confirmButtonClass = computed(() => {
  switch (activeWorkflowAction.value) {
    case "publish":
      return "btn-cta";
    case "submit_review":
      return "btn-primary";
    case "request_changes":
      return "btn-ghost";
    case "rollback":
      return "btn-cta";
    default:
      return "btn-primary";
  }
});

function versionLabel(state: VersionState): string {
  const labels: Record<VersionState, string> = {
    draft: "Utkast",
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
    : "Nytt utkast";
  return `${publication} · ${versionSegment}`;
});
</script>

<template>
  <div class="space-y-6">
    <RouterLink
      to="/admin/tools"
      class="text-sm text-navy/70 underline hover:text-burgundy"
    >
      ← Tillbaka till verktyg
    </RouterLink>

    <!-- Inline errors (validation / blocking states) -->
    <SystemMessage
      v-model="errorMessage"
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
      <!-- PANEL 1: Title + Workflow -->
      <ScriptEditorHeaderPanel
        :metadata-title="metadataTitle"
        :metadata-summary="metadataSummary"
        :tool-slug="editor.tool.slug"
        :status-line="statusLine"
        :is-title-saving="isTitleSaving"
        :is-summary-saving="isSummarySaving"
        :can-submit-review="canSubmitReview"
        :can-publish="canPublish"
        :can-request-changes="canRequestChanges"
        :can-rollback="canRollback"
        :is-workflow-submitting="isWorkflowSubmitting"
        @update:metadata-title="metadataTitle = $event"
        @update:metadata-summary="metadataSummary = $event"
        @commit-title="saveTitle"
        @commit-summary="saveSummary"
        @action="openWorkflowAction"
      />

      <!-- PANEL 2: Editor + Test -->
      <div class="space-y-3">
        <DraftLockBanner
          :state="draftLockState"
          :message="draftLockStatus"
          :expires-at="expiresAt"
          :can-force="canForceTakeover"
          :is-busy="isLocking"
          @force="forceTakeover"
        />

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
          v-model:edit-instruction="editInstruction"
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
          :has-dirty-changes="hasDirtyChanges"
          :is-read-only="isReadOnly"
          :is-drawer-open="isDrawerOpen"
          :is-history-drawer-open="isHistoryDrawerOpen"
          :is-metadata-drawer-open="isMetadataDrawerOpen"
          :is-maintainers-drawer-open="isMaintainersDrawerOpen"
          :is-instructions-drawer-open="isInstructionsDrawerOpen"
          :compare-target="compareTarget"
          :compare-active-file-id="compareActiveFileId"
          :edit-suggestion="editSuggestion"
          :edit-is-loading="isEditLoading"
          :edit-error="editError"
          :can-apply-edit="canApplyEdit"
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
          @open-metadata-drawer="toggleMetadataDrawer"
          @open-maintainers-drawer="toggleMaintainersDrawer"
          @open-instructions-drawer="toggleInstructionsDrawer"
          @close-drawer="closeDrawer"
          @select-history-version="selectHistoryVersion"
          @compare-version="handleCompareVersion"
          @rollback-version="openRollbackForVersion"
          @save-all-metadata="saveAllMetadata"
          @suggest-slug-from-title="applySlugSuggestionFromTitle"
          @add-maintainer="addMaintainer"
          @remove-maintainer="removeMaintainer"
          @editor-view-ready="editorView = $event"
          @request-edit-suggestion="requestEditSuggestion"
          @apply-edit-suggestion="applyEditSuggestion"
          @clear-edit-suggestion="clearEditSuggestion"
          @close-compare="handleCloseCompare"
          @update:compare-target="handleCompareTargetUpdate($event)"
          @update:compare-active-file-id="handleCompareActiveFileIdUpdate($event)"
        />
      </div>
    </template>
  </div>

  <WorkflowActionModal
    :is-open="isWorkflowModalOpen"
    :action-meta="workflowActionMeta"
    :note="workflowNote"
    :show-note-field="showWorkflowNoteField"
    :error="workflowError"
    :is-submitting="isWorkflowSubmitting"
    :confirm-button-class="confirmButtonClass"
    @close="closeWorkflowModal"
    @submit="submitWorkflowAction"
    @update:error="workflowError = $event"
    @update:note="workflowNote = $event"
  />
</template>
