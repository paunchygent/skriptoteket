<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { onBeforeRouteLeave, useRoute, useRouter } from "vue-router";
import type { components } from "../../api/openapi";
import CodeMirrorEditor from "../../components/editor/CodeMirrorEditor.vue";
import EntrypointDropdown from "../../components/editor/EntrypointDropdown.vue";
import InlineEditableText from "../../components/editor/InlineEditableText.vue";
import MaintainersDrawer from "../../components/editor/MaintainersDrawer.vue";
import MetadataDrawer from "../../components/editor/MetadataDrawer.vue";
import SandboxRunner from "../../components/editor/SandboxRunner.vue";
import VersionHistoryDrawer from "../../components/editor/VersionHistoryDrawer.vue";
import WorkflowActionModal from "../../components/editor/WorkflowActionModal.vue";
import WorkflowContextButtons from "../../components/editor/WorkflowContextButtons.vue";
import { useEditorWorkflowActions } from "../../composables/editor/useEditorWorkflowActions";
import { useScriptEditor } from "../../composables/editor/useScriptEditor";
import { useToolMaintainers } from "../../composables/editor/useToolMaintainers";
import { useToolTaxonomy } from "../../composables/editor/useToolTaxonomy";
import { useAuthStore } from "../../stores/auth";
type VersionState = components["schemas"]["VersionState"];
const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

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
  changeSummary,
  metadataTitle,
  metadataSummary,
  isLoading,
  isSaving,
  isMetadataSaving,
  errorMessage,
  successMessage,
  selectedVersion,
  editorToolId,
  hasDirtyChanges,
  save,
  saveToolMetadata,
  loadEditor,
} = useScriptEditor({
  toolId,
  versionId,
  route,
  router,
});
const {
  isModalOpen: isWorkflowModalOpen,
  activeAction: activeWorkflowAction,
  actionMeta: workflowActionMeta,
  showNoteField: showWorkflowNoteField,
  note: workflowNote,
  workflowError,
  workflowSuccess,
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
});
const {
  professions,
  categories,
  selectedProfessionIds,
  selectedCategoryIds,
  taxonomyError,
  taxonomySuccess,
  isTaxonomyLoading,
  isTaxonomySaving,
  saveTaxonomy,
} = useToolTaxonomy({
  toolId: editorToolId,
  canEdit: canEditTaxonomy,
});
const {
  maintainers,
  ownerUserId,
  isLoading: isMaintainersLoading,
  isSaving: isMaintainersSaving,
  error: maintainersError,
  success: maintainersSuccess,
  loadMaintainers,
  addMaintainer,
  removeMaintainer,
} = useToolMaintainers({
  toolId: editorToolId,
  canEdit: canEditMaintainers,
});
const entrypointOptions = ["run_tool", "main", "run", "execute"];
const activeDrawer = ref<"history" | "metadata" | "maintainers" | null>(null);

const isSavingAllMetadata = computed(() => isMetadataSaving.value || isTaxonomySaving.value);

async function saveAllMetadata(): Promise<void> {
  await saveToolMetadata();
  if (canEditTaxonomy.value) {
    await saveTaxonomy();
  }
}
const isHistoryDrawerOpen = computed(() => activeDrawer.value === "history");
const isMetadataDrawerOpen = computed(() => activeDrawer.value === "metadata");
const isMaintainersDrawerOpen = computed(() => activeDrawer.value === "maintainers");
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
      return "bg-burgundy text-canvas border-navy btn-secondary-hover";
    case "submit_review":
      return "bg-navy text-canvas border-navy btn-secondary-hover";
    case "request_changes":
      return "bg-white text-navy border-navy hover:bg-canvas btn-secondary-hover";
    case "rollback":
      return "bg-white text-burgundy border-burgundy hover:bg-burgundy/10";
    default:
      return "bg-navy text-canvas border-navy btn-secondary-hover";
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

    <!-- Success/Error messages -->
    <div
      v-if="successMessage || workflowSuccess"
      class="p-4 border border-success bg-success/10 shadow-brutal-sm text-sm text-success"
    >
      {{ successMessage || workflowSuccess }}
    </div>
    <div
      v-if="errorMessage || workflowError"
      class="p-4 border border-burgundy bg-white shadow-brutal-sm text-sm text-burgundy"
    >
      {{ errorMessage || workflowError }}
    </div>

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
            />
            <p class="text-sm text-navy/70">
              <span class="font-mono">{{ editor.tool.slug }}</span>
            </p>
            <InlineEditableText
              v-model="metadataSummary"
              tag="p"
              display-class="text-sm text-navy/70"
              input-class="text-sm"
              placeholder="Lägg till en sammanfattning..."
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
      <div class="border border-navy bg-white shadow-brutal-sm">
        <!-- Control row -->
        <div class="p-4 border-b border-navy/20">
          <div class="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <!-- Save group: Spara + Osparat + Ändringssammanfattning -->
            <div class="flex flex-col gap-2 sm:flex-row sm:items-end sm:gap-3">
              <div class="flex items-center gap-2">
                <button
                  type="button"
                  :disabled="isSaving"
                  class="min-w-[80px] px-4 py-2 text-xs font-bold uppercase tracking-widest bg-navy text-canvas border border-navy shadow-brutal-sm btn-secondary-hover transition-colors active:translate-x-1 active:translate-y-1 active:shadow-none disabled:opacity-50 disabled:cursor-not-allowed"
                  @click="save"
                >
                  <span
                    v-if="isSaving"
                    class="inline-block w-3 h-3 border-2 border-canvas/30 border-t-canvas rounded-full animate-spin"
                  />
                  <span v-else>Spara</span>
                </button>
                <span
                  v-if="hasDirtyChanges"
                  class="text-xs text-burgundy font-semibold uppercase tracking-wide"
                >
                  Osparat
                </span>
              </div>

              <div class="min-w-[180px] max-w-xs space-y-1">
                <label class="text-xs font-semibold uppercase tracking-wide text-navy/70">
                  Ändringssammanfattning
                </label>
                <input
                  v-model="changeSummary"
                  class="w-full border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
                  placeholder="T.ex. fixade bugg..."
                >
              </div>
            </div>

            <div class="flex flex-wrap items-center gap-2">
              <button
                type="button"
                class="px-3 py-2 text-xs font-semibold uppercase tracking-wide border border-navy bg-white text-navy shadow-brutal-sm hover:bg-canvas btn-secondary-hover transition-colors active:translate-x-1 active:translate-y-1 active:shadow-none"
                @click="openHistoryDrawer"
              >
                Öppna sparade
              </button>
              <button
                v-if="canEditTaxonomy"
                type="button"
                class="px-3 py-2 text-xs font-semibold uppercase tracking-wide border border-navy bg-white text-navy shadow-brutal-sm hover:bg-canvas btn-secondary-hover transition-colors active:translate-x-1 active:translate-y-1 active:shadow-none"
                @click="openMetadataDrawer"
              >
                Metadata
              </button>
              <button
                v-if="canEditMaintainers"
                type="button"
                class="px-3 py-2 text-xs font-semibold uppercase tracking-wide border border-navy bg-white text-navy shadow-brutal-sm hover:bg-canvas btn-secondary-hover transition-colors active:translate-x-1 active:translate-y-1 active:shadow-none"
                @click="openMaintainersDrawer"
              >
                Redigeringsbehörigheter
              </button>
            </div>
          </div>
        </div>

        <div
          :class="[
            'grid',
            isDrawerOpen
              ? 'md:grid-cols-[minmax(0,1fr)_400px]'
              : 'md:grid-cols-[minmax(0,1fr)]',
          ]"
        >
          <div class="p-4 space-y-4 min-w-0">
            <!-- Source code -->
            <div class="space-y-3">
              <h2 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
                Källkod
              </h2>
              <div class="h-[420px] border border-navy bg-canvas shadow-brutal-sm overflow-hidden">
                <CodeMirrorEditor v-model="sourceCode" />
              </div>
            </div>

            <!-- Test section -->
            <div class="border-t border-navy/20 pt-4 space-y-3">
              <h2 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
                Testkör kod
              </h2>

              <!-- Entrypoint + file picker + run button -->
              <div class="flex flex-col gap-3 sm:flex-row sm:items-end">
                <EntrypointDropdown
                  v-model="entrypoint"
                  :options="entrypointOptions"
                />
              </div>

              <SandboxRunner
                v-if="selectedVersion"
                :version-id="selectedVersion.id"
                :tool-id="editor.tool.id"
              />
              <p
                v-else
                class="text-sm text-navy/60"
              >
                Spara ett utkast för att kunna testa.
              </p>
            </div>
          </div>

          <!-- Drawers -->
          <VersionHistoryDrawer
            v-if="isHistoryDrawerOpen"
            :is-open="isHistoryDrawerOpen"
            :versions="editor.versions"
            :active-version-id="selectedVersion?.id"
            :can-rollback="canRollbackVersions"
            :is-submitting="isWorkflowSubmitting"
            @close="closeDrawer"
            @select="handleHistorySelect"
            @rollback="openRollbackForVersion"
          />

          <MetadataDrawer
            v-if="isMetadataDrawerOpen"
            :is-open="isMetadataDrawerOpen"
            :metadata-title="metadataTitle"
            :metadata-summary="metadataSummary"
            :professions="professions"
            :categories="categories"
            :selected-profession-ids="selectedProfessionIds"
            :selected-category-ids="selectedCategoryIds"
            :taxonomy-error="taxonomyError"
            :taxonomy-success="taxonomySuccess"
            :is-loading="isTaxonomyLoading"
            :is-saving="isSavingAllMetadata"
            @close="closeDrawer"
            @save="saveAllMetadata"
            @update:metadata-title="metadataTitle = $event"
            @update:metadata-summary="metadataSummary = $event"
            @update:selected-profession-ids="updateProfessionIds"
            @update:selected-category-ids="updateCategoryIds"
          />

          <MaintainersDrawer
            v-if="isMaintainersDrawerOpen"
            :is-open="isMaintainersDrawerOpen"
            :maintainers="maintainers"
            :owner-user-id="ownerUserId"
            :is-superuser="canRollbackVersions"
            :is-loading="isMaintainersLoading"
            :is-saving="isMaintainersSaving"
            :error="maintainersError"
            :success="maintainersSuccess"
            @close="closeDrawer"
            @add="addMaintainer"
            @remove="removeMaintainer"
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
    :is-submitting="isWorkflowSubmitting"
    :confirm-button-class="confirmButtonClass"
    @close="closeWorkflowModal"
    @submit="submitWorkflowAction"
    @update:note="workflowNote = $event"
  />
</template>
