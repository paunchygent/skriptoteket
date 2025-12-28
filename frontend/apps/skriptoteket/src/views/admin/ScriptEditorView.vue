<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { onBeforeRouteLeave, useRoute, useRouter } from "vue-router";
import type { components } from "../../api/openapi";
import DraftLockBanner from "../../components/editor/DraftLockBanner.vue";
import EditorWorkspacePanel from "../../components/editor/EditorWorkspacePanel.vue";
import InlineEditableText from "../../components/editor/InlineEditableText.vue";
import SystemMessage from "../../components/ui/SystemMessage.vue";
import WorkflowActionModal from "../../components/editor/WorkflowActionModal.vue";
import WorkflowContextButtons from "../../components/editor/WorkflowContextButtons.vue";
import { useEditorWorkflowActions } from "../../composables/editor/useEditorWorkflowActions";
import { useDraftLock } from "../../composables/editor/useDraftLock";
import { useScriptEditor } from "../../composables/editor/useScriptEditor";
import { useToolMaintainers } from "../../composables/editor/useToolMaintainers";
import { useToolTaxonomy } from "../../composables/editor/useToolTaxonomy";
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
const activeDrawer = ref<"history" | "metadata" | "maintainers" | "instructions" | null>(null);

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
const isHistoryDrawerOpen = computed(() => activeDrawer.value === "history");
const isMetadataDrawerOpen = computed(() => activeDrawer.value === "metadata");
const isMaintainersDrawerOpen = computed(() => activeDrawer.value === "maintainers");
const isInstructionsDrawerOpen = computed(() => activeDrawer.value === "instructions");
const isDrawerOpen = computed(() => activeDrawer.value !== null);

function openHistoryDrawer(): void {
  activeDrawer.value = activeDrawer.value === "history" ? null : "history";
}

function openMetadataDrawer(): void {
  if (!canEditTaxonomy.value) return;
  activeDrawer.value = activeDrawer.value === "metadata" ? null : "metadata";
}

function openMaintainersDrawer(): void {
  if (!canEditMaintainers.value) return;
  const next = activeDrawer.value === "maintainers" ? null : "maintainers";
  activeDrawer.value = next;
  if (next === "maintainers" && editorToolId.value) {
    void loadMaintainers(editorToolId.value);
  }
}

function openInstructionsDrawer(): void {
  activeDrawer.value = activeDrawer.value === "instructions" ? null : "instructions";
}

function closeDrawer(): void {
  activeDrawer.value = null;
}

function handleHistorySelect(versionIdValue: string): void {
  if (hasDirtyChanges.value && !isSaving.value) {
    const confirmed = window.confirm("Du har osparade ändringar. Vill du byta version?");
    if (!confirmed) {
      return;
    }
  }
  void router.replace({
    query: {
      ...route.query,
      version: versionIdValue,
    },
  });
}

function updateProfessionIds(value: string[]): void {
  selectedProfessionIds.value = value;
}

function updateCategoryIds(value: string[]): void {
  selectedCategoryIds.value = value;
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

const beforeUnloadHandler = (event: BeforeUnloadEvent) => {
  if (!hasDirtyChanges.value || isSaving.value) return;
  event.preventDefault();
  event.returnValue = "";
};

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape" && isDrawerOpen.value) {
    closeDrawer();
  }
}

onBeforeRouteLeave((_to, _from, next) => {
  if (!hasDirtyChanges.value || isSaving.value) {
    next();
    return;
  }

  if (window.confirm("Du har osparade ändringar. Vill du lämna sidan?")) {
    next();
  } else {
    next(false);
  }
});

onMounted(() => {
  window.addEventListener("beforeunload", beforeUnloadHandler);
  window.addEventListener("keydown", handleKeydown);
});

onBeforeUnmount(() => {
  window.removeEventListener("beforeunload", beforeUnloadHandler);
  window.removeEventListener("keydown", handleKeydown);
});

watch(
  () => route.fullPath,
  () => {
    if (activeDrawer.value && activeDrawer.value !== "history") {
      closeDrawer();
    }
  },
);
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
      <div class="border border-navy bg-white shadow-brutal-sm p-5 space-y-4">
        <!-- Title and summary section -->
        <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div class="space-y-2 flex-1">
            <InlineEditableText
              v-model="metadataTitle"
              tag="h1"
              display-class="text-2xl font-semibold text-navy"
              input-class="text-2xl font-semibold"
              placeholder="Verktygets titel"
              :saving="isTitleSaving"
              @commit="saveTitle"
            />
            <p class="text-sm text-navy/70">
              URL-namn: <span class="font-mono">{{ editor.tool.slug }}</span>
            </p>
            <InlineEditableText
              v-model="metadataSummary"
              tag="p"
              display-class="text-sm text-navy/70"
              input-class="text-sm"
              placeholder="Lägg till en sammanfattning..."
              :saving="isSummarySaving"
              @commit="saveSummary"
            />
          </div>

          <div class="text-sm font-medium text-navy/70 shrink-0">
            {{ statusLine }}
          </div>
        </div>

        <!-- Workflow context buttons -->
        <div class="border-t border-navy/20 pt-4">
          <WorkflowContextButtons
            :can-submit-review="canSubmitReview"
            :can-publish="canPublish"
            :can-request-changes="canRequestChanges"
            :can-rollback="canRollback"
            :is-submitting="isWorkflowSubmitting"
            @action="openWorkflowAction"
          />
        </div>
      </div>

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
          :tool-id="editor.tool.id"
          :versions="editor.versions"
          :selected-version="selectedVersion"
          :entrypoint-options="entrypointOptions"
          :change-summary="changeSummary"
          :entrypoint="entrypoint"
          :source-code="sourceCode"
          :settings-schema-text="settingsSchemaText"
          :input-schema-text="inputSchemaText"
          :usage-instructions="usageInstructions"
          :metadata-title="metadataTitle"
          :metadata-slug="metadataSlug"
          :metadata-summary="metadataSummary"
          :selected-profession-ids="selectedProfessionIds"
          :selected-category-ids="selectedCategoryIds"
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
          :professions="professions"
          :categories="categories"
          :is-taxonomy-loading="isTaxonomyLoading"
          :is-saving-all-metadata="isSavingAllMetadata"
          :maintainers="maintainers"
          :owner-user-id="ownerUserId"
          :is-maintainers-loading="isMaintainersLoading"
          :is-maintainers-saving="isMaintainersSaving"
          @save="save"
          @open-history-drawer="openHistoryDrawer"
          @open-metadata-drawer="openMetadataDrawer"
          @open-maintainers-drawer="openMaintainersDrawer"
          @open-instructions-drawer="openInstructionsDrawer"
          @close-drawer="closeDrawer"
          @select-history-version="handleHistorySelect"
          @rollback-version="openRollbackForVersion"
          @save-all-metadata="saveAllMetadata"
          @suggest-slug-from-title="applySlugSuggestionFromTitle"
          @add-maintainer="addMaintainer"
          @remove-maintainer="removeMaintainer"
          @update:change-summary="changeSummary = $event"
          @update:entrypoint="entrypoint = $event"
          @update:source-code="sourceCode = $event"
          @update:settings-schema-text="settingsSchemaText = $event"
          @update:input-schema-text="inputSchemaText = $event"
          @update:usage-instructions="usageInstructions = $event"
          @update:metadata-title="metadataTitle = $event"
          @update:metadata-slug="metadataSlug = $event"
          @update:metadata-summary="metadataSummary = $event"
          @update:selected-profession-ids="updateProfessionIds"
          @update:selected-category-ids="updateCategoryIds"
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
