<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { useRoute, useRouter } from "vue-router";
import type { components } from "../../api/openapi";
import DraftLockBanner from "../../components/editor/DraftLockBanner.vue";
import EditorWorkspacePanel from "../../components/editor/EditorWorkspacePanel.vue";
import SystemMessage from "../../components/ui/SystemMessage.vue";
import WorkflowActionModal from "../../components/editor/WorkflowActionModal.vue";
import WorkingCopyRestorePrompt from "../../components/editor/WorkingCopyRestorePrompt.vue";
import { useEditorChat } from "../../composables/editor/useEditorChat";
import {
  resolveDefaultCompareTarget,
  resolveMostRecentRejectedReviewVersionId,
} from "../../composables/editor/editorCompareDefaults";
import { useEditorCompareState, type EditorCompareTarget } from "../../composables/editor/useEditorCompareState";
import { useEditorSchemaParsing } from "../../composables/editor/useEditorSchemaParsing";
import { useEditorSchemaValidation } from "../../composables/editor/useEditorSchemaValidation";
import { useEditorWorkingCopy } from "../../composables/editor/useEditorWorkingCopy";
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
import { useLayoutStore } from "../../stores/layout";
import { useHelp } from "../../components/help/useHelp";
type VersionState = components["schemas"]["VersionState"];
const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const layout = useLayoutStore();
const toast = useToast();
const help = useHelp();
const { focusMode } = storeToRefs(layout);
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
const currentUserId = computed(() => auth.user?.id ?? null);
const {
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
} = useScriptEditor({
  toolId,
  versionId,
  route,
  router,
  notify,
});
const focusInitialized = ref(false);
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
  isModalOpen: isWorkflowModalOpen,
  activeAction: activeWorkflowAction,
  actionMeta: workflowActionMeta,
  showNoteField: showWorkflowNoteField,
  note: workflowNote,
  workflowError,
  isSubmitting: isWorkflowSubmitting,
  canSubmitReview,
  submitReviewBlockers,
  submitReviewTooltip,
  canPublish,
  canRequestChanges,
  canRollback,
  openRollbackForVersion,
  openAction: openWorkflowAction,
  closeAction: closeWorkflowModal,
  submitAction: submitWorkflowAction,
} = useEditorWorkflowActions({
  selectedVersion,
  toolSlug: metadataSlug,
  selectedProfessionIds,
  selectedCategoryIds,
  route,
  router,
  reloadEditor: loadEditor,
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
  await createBeforeSaveCheckpoint();
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
  confirmDiscardChanges,
});
const {
  isHistoryDrawerOpen,
  isChatDrawerOpen,
  isChatCollapsed,
  toggleHistoryDrawer,
  toggleChatCollapsed,
  closeDrawer,
  selectHistoryVersion,
} = drawers;

const compare = useEditorCompareState({ route, router });
const compareTarget = compare.compareTarget;
const compareActiveFileId = compare.activeFileId;

const rejectedReviewVersionId = computed(() => {
  if (!editor.value) return null;
  return resolveMostRecentRejectedReviewVersionId(editor.value.versions);
});

const defaultCompareTarget = computed(() => {
  if (!editor.value) {
    return { target: null, reason: null } as const;
  }
  return resolveDefaultCompareTarget({
    baseVersion: selectedVersion.value,
    toolIsPublished: editor.value.tool.is_published,
    activeVersionId: editor.value.tool.active_version_id ?? null,
    versions: editor.value.versions,
    parentVersionId: editor.value.parent_version_id ?? null,
  });
});

const canOpenCompare = computed(
  () => compareTarget.value === null && defaultCompareTarget.value.target !== null,
);
const openCompareTitle = computed(() => defaultCompareTarget.value.reason ?? "");

const canCompareVersions = computed(() => {
  if (!editor.value) return true;
  if (selectedVersion.value?.state !== "in_review") return true;
  if (editor.value.tool.is_published) return true;
  return rejectedReviewVersionId.value !== null;
});

async function handleCompareVersion(versionId: string): Promise<void> {
  await compare.toggleCompareVersionId(versionId);
  closeDrawer();
}

async function handleOpenCompare(): Promise<void> {
  const target = defaultCompareTarget.value.target;
  if (!target) return;
  await compare.setCompareTarget(target);
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

type EditorWorkspaceMode = "source" | "diff" | "metadata" | "test";

const editorMode = ref<EditorWorkspaceMode>("source");
const canEnterDiff = computed(() => true);

function setEditorMode(nextMode: EditorWorkspaceMode): void {
  if (nextMode === editorMode.value) {
    if (nextMode === "diff") {
      void handleCloseCompare();
      editorMode.value = "source";
    }
    if (nextMode === "metadata" || nextMode === "test") {
      editorMode.value = "source";
    }
    return;
  }

  if (nextMode === "diff") {
    if (compareTarget.value) {
      editorMode.value = "diff";
      return;
    }
    if (!canOpenCompare.value) {
      editorMode.value = "diff";
      return;
    }
    editorMode.value = "diff";
    void handleOpenCompare();
    return;
  }

  if (compareTarget.value && nextMode !== "diff") {
    void handleCloseCompare();
  }

  editorMode.value = nextMode;
}

const workingCopy = useEditorWorkingCopy({
  userId: currentUserId,
  toolId: editorToolId,
  baseVersionId: computed(() => selectedVersion.value?.id ?? null),
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
});

const {
  isRestorePromptOpen,
  hasWorkingCopyHead,
  restoreDiffItems,
  workingCopyUpdatedAt,
  checkpointSummaries,
  pinnedCheckpointCount,
  pinnedCheckpointLimit,
  isCheckpointBusy,
  restoreWorkingCopy,
  discardWorkingCopy,
  restoreServerVersion,
  createBeforeSaveCheckpoint,
  createPinnedCheckpoint,
  restoreCheckpoint,
  removeCheckpoint,
  workingCopyProvider,
} = workingCopy;

const editorChat = useEditorChat({
  toolId: editorToolId,
  baseVersionId: computed(() => selectedVersion.value?.id ?? null),
});

const {
  messages: chatMessages,
  streaming: chatStreaming,
  disabledMessage: chatDisabledMessage,
  error: chatError,
  loadHistory: loadChatHistory,
  sendMessage: sendChatMessage,
  cancel: cancelChat,
  clear: clearChat,
  clearError: clearChatError,
  clearDisabledMessage: clearChatDisabled,
} = editorChat;

watch(
  () => isChatDrawerOpen.value,
  (open) => {
    if (!open) return;
    void loadChatHistory();
  },
  { immediate: true },
);

watch(
  () => editorToolId.value,
  (value, previous) => {
    if (!value || value === previous) return;
    if (!isChatDrawerOpen.value) return;
    void loadChatHistory();
  },
);

watch(
  () => isChatDrawerOpen.value,
  (open) => {
    if (!open) return;
    if (!focusMode.value) {
      layout.enable();
    }
  },
);

watch(
  () => compareTarget.value,
  (value) => {
    if (value && editorMode.value !== "diff") {
      editorMode.value = "diff";
    }
    if (!value && editorMode.value === "diff") {
      editorMode.value = "source";
    }
  },
);

watch(
  () => editorMode.value,
  (mode) => {
    if (mode !== "metadata") return;
    if (!canEditMaintainers.value) return;
    if (!editorToolId.value) return;
    void loadMaintainers(editorToolId.value);
  },
);

watch(
  () => editor.value,
  (value) => {
    if (!value || focusInitialized.value) return;
    focusInitialized.value = true;
    if (!focusMode.value) {
      layout.enable();
    }
  },
  { immediate: true },
);

function handleRestoreServerVersion(): void {
  if (pinnedCheckpointCount.value > 0) {
    const message =
      hasDirtyChanges.value
        ? `Återställ till serverversion och rensa lokalt? Dina osparade ändringar försvinner och ${pinnedCheckpointCount.value} manuella återställningspunkter tas bort.`
        : `Rensa lokalt arbetsexemplar? ${pinnedCheckpointCount.value} manuella återställningspunkter tas bort.`;

    if (!window.confirm(message)) {
      return;
    }
    void restoreServerVersion();
    return;
  }

  if (!confirmDiscardChanges("Återställ till serverversion och rensa lokalt?")) return;
  void restoreServerVersion();
}

function handleDiscardWorkingCopy(): void {
  if (pinnedCheckpointCount.value > 0) {
    const message = `Kasta lokalt arbetsexemplar? Det här tar bort lokalt arbetsexemplar och ${pinnedCheckpointCount.value} manuella återställningspunkter. Serverversionen påverkas inte.`;
    if (!window.confirm(message)) {
      return;
    }
  }
  void discardWorkingCopy();
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

const submitReviewBlockedItems = computed(() => {
  if (activeWorkflowAction.value !== "submit_review") {
    return [];
  }
  return submitReviewBlockers.value.map((blocker) => blocker.message);
});

function openEditorHelp(): void {
  help.showTopic("admin_editor");
  help.open();
  closeWorkflowModal();
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

const lockBadge = computed(() => {
  if (draftLockState.value === "owner") {
    return {
      label: "Redigeringslås aktivt",
      tone: "success" as const,
    };
  }
  if (draftLockState.value === "acquiring") {
    return {
      label: "Säkrar redigeringslås...",
      tone: "neutral" as const,
    };
  }
  return null;
});
</script>

<template>
  <div class="flex flex-col gap-4 min-h-0 h-full">
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
      <!-- PANEL 1: Editor + Test -->
      <div class="flex flex-col gap-3 min-h-0">
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
            :chat-messages="chatMessages"
            :chat-is-streaming="chatStreaming"
            :chat-disabled-message="chatDisabledMessage"
            :chat-error="chatError"
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
            @send-chat-message="sendChatMessage"
            @cancel-chat-stream="cancelChat"
            @clear-chat="clearChat"
            @clear-chat-error="clearChatError"
            @clear-chat-disabled="clearChatDisabled"
          />
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
