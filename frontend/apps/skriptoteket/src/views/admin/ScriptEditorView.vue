<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { onBeforeRouteLeave, useRoute, useRouter } from "vue-router";
import type { components } from "../../api/openapi";
import CodeMirrorEditor from "../../components/editor/CodeMirrorEditor.vue";
import EntrypointDropdown from "../../components/editor/EntrypointDropdown.vue";
import InlineEditableText from "../../components/editor/InlineEditableText.vue";
import MetadataDrawer from "../../components/editor/MetadataDrawer.vue";
import SandboxRunner from "../../components/editor/SandboxRunner.vue";
import VersionHistoryDrawer from "../../components/editor/VersionHistoryDrawer.vue";
import WorkflowContextButtons from "../../components/editor/WorkflowContextButtons.vue";
import { useEditorWorkflowActions } from "../../composables/editor/useEditorWorkflowActions";
import { useScriptEditor } from "../../composables/editor/useScriptEditor";
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
const entrypointOptions = ["run_tool", "main", "run", "execute"];
const activeDrawer = ref<"history" | "metadata" | null>(null);

const isSavingAllMetadata = computed(() => isMetadataSaving.value || isTaxonomySaving.value);

async function saveAllMetadata(): Promise<void> {
  await saveToolMetadata();
  if (canEditTaxonomy.value) {
    await saveTaxonomy();
  }
}
const isHistoryDrawerOpen = computed(() => activeDrawer.value === "history");
const isMetadataDrawerOpen = computed(() => activeDrawer.value === "metadata");
const isDrawerOpen = computed(() => activeDrawer.value !== null);

function openHistoryDrawer(): void {
  activeDrawer.value = activeDrawer.value === "history" ? null : "history";
}

function openMetadataDrawer(): void {
  if (!canEditTaxonomy.value) return;
  activeDrawer.value = activeDrawer.value === "metadata" ? null : "metadata";
}

function closeDrawer(): void {
  activeDrawer.value = null;
}

function handleHistorySelect(): void {
  closeDrawer();
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
    closeDrawer();
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

            <!-- Drawer buttons -->
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
            </div>
          </div>
        </div>

        <!-- Code editor section -->
        <div
          :class="[
            'grid',
            isDrawerOpen
              ? 'md:grid-cols-[minmax(0,1fr)_400px]'
              : 'md:grid-cols-[minmax(0,1fr)]',
          ]"
        >
          <div class="p-4 space-y-4">
            <!-- Source code -->
            <div class="space-y-3">
              <h2 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
                Källkod
              </h2>
              <div class="h-[420px] border border-navy bg-canvas shadow-brutal-sm">
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
            @close="closeDrawer"
            @select="handleHistorySelect"
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
        </div>
      </div>
    </template>
  </div>

  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="isWorkflowModalOpen && workflowActionMeta"
        class="fixed inset-0 z-50 flex items-center justify-center bg-navy/40"
        role="dialog"
        aria-modal="true"
        aria-labelledby="workflow-modal-title"
        @click.self="closeWorkflowModal"
      >
        <div class="relative w-full max-w-lg mx-4 p-6 bg-canvas border border-navy shadow-brutal">
          <button
            type="button"
            class="absolute top-3 right-3 text-navy/60 hover:text-navy text-xl leading-none"
            @click="closeWorkflowModal"
          >
            &times;
          </button>

          <h2
            id="workflow-modal-title"
            class="text-xl font-semibold text-navy"
          >
            {{ workflowActionMeta.title }}
          </h2>

          <p
            v-if="workflowActionMeta.description"
            class="mt-2 text-sm text-navy/70"
          >
            {{ workflowActionMeta.description }}
          </p>

          <div
            v-if="workflowError"
            class="mt-4 p-3 border border-burgundy bg-white text-burgundy text-sm"
          >
            {{ workflowError }}
          </div>

          <form
            class="mt-5 space-y-4"
            @submit.prevent="submitWorkflowAction"
          >
            <div v-if="showWorkflowNoteField">
              <label class="block text-sm font-semibold text-navy mb-1">
                {{ workflowActionMeta.noteLabel }}
              </label>
              <textarea
                v-model="workflowNote"
                rows="4"
                class="w-full px-3 py-2 border border-navy bg-white text-navy"
                :placeholder="workflowActionMeta.notePlaceholder"
                :disabled="isWorkflowSubmitting"
              />
            </div>

            <div class="flex flex-wrap gap-3">
              <button
                type="button"
                class="px-4 py-2 text-xs font-semibold uppercase tracking-wide border border-navy bg-white text-navy shadow-brutal-sm hover:bg-canvas btn-secondary-hover transition-colors active:translate-x-1 active:translate-y-1 active:shadow-none"
                :disabled="isWorkflowSubmitting"
                @click="closeWorkflowModal"
              >
                Avbryt
              </button>
              <button
                type="submit"
                class="px-4 py-2 text-xs font-semibold uppercase tracking-wide border shadow-brutal-sm transition-colors active:translate-x-1 active:translate-y-1 active:shadow-none"
                :class="confirmButtonClass"
                :disabled="isWorkflowSubmitting"
              >
                {{ isWorkflowSubmitting ? "Arbetar..." : workflowActionMeta.confirmLabel }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--huleedu-duration-default) var(--huleedu-ease-default);
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
