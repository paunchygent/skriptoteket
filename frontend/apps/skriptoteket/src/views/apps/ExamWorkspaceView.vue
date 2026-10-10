<script setup lang="ts">
/**
 * Teacher exam workspace host frame.
 *
 * Domain purpose:
 *   Provide the minimal teacher exam workspace: upload a .docx exam or
 *   reopen a saved one, review extracted questions with per-item review
 *   status, edit the selected question, review advisory answer-key
 *   proposals, save versioned revisions, and download QTI, PDF, and DOCX
 *   files from the saved version.
 *
 * Relationships:
 *   - Mounted by the canonical `/apps/exam-workspace` route; the
 *     `?document=<lineage_id>` query opens a saved document, on load and
 *     when the query changes later.
 *   - Owns state through `useExamWorkspaceDocument`,
 *     `useExamWorkspaceExports`, and `useExamWorkspaceEnrichment`; renders
 *     the rail through `ExamWorkspaceSavedDocuments`,
 *     `ExamWorkspaceExportPanel`, and `ExamWorkspaceEnrichmentPanel`, the
 *     question list through `ExamWorkspaceItemTable`, item editing through
 *     `ExamWorkspaceItemEditor`, and proposals through
 *     `ExamWorkspaceProposalPanel`.
 */

import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { Upload } from "lucide-vue-next";

import { UiDenseStatusPill } from "../../components/ui";
import type { ExamWorkspaceExportTarget } from "../../api/examWorkspace";
import ExamWorkspaceEnrichmentPanel from "./exam-workspace/ExamWorkspaceEnrichmentPanel.vue";
import ExamWorkspaceExportPanel from "./exam-workspace/ExamWorkspaceExportPanel.vue";
import ExamWorkspaceItemEditor from "./exam-workspace/ExamWorkspaceItemEditor.vue";
import ExamWorkspaceItemTable from "./exam-workspace/ExamWorkspaceItemTable.vue";
import ExamWorkspaceProposalPanel from "./exam-workspace/ExamWorkspaceProposalPanel.vue";
import ExamWorkspaceSavedDocuments from "./exam-workspace/ExamWorkspaceSavedDocuments.vue";
import { toExamWorkspaceItemRows } from "./exam-workspace/examWorkspaceRows";
import { useExamWorkspaceDocument } from "./exam-workspace/useExamWorkspaceDocument";
import { useExamWorkspaceEnrichment } from "./exam-workspace/useExamWorkspaceEnrichment";
import { useExamWorkspaceExports } from "./exam-workspace/useExamWorkspaceExports";

const DOCX_EXTENSION = ".docx";
const INVALID_DOCX_COPY = "Det gick inte att använda filen. Välj en .docx-fil.";
const MULTIPLE_FILES_COPY = "Välj en provfil åt gången.";

const route = useRoute();
const router = useRouter();

const {
  addItem,
  applyProposal,
  conflictNotice,
  importDocument,
  isBusy,
  isDirty,
  loadSavedDocuments,
  markItemReviewed,
  notes,
  openDocument,
  reloadDocument,
  saveDocument,
  savedDocuments,
  selectItem,
  selectedItem,
  selectedItemId,
  summary,
  updateItemBodyText,
  updateItemChoiceText,
  updateItemCorrectChoices,
  updateItemGapValues,
  updateItemPoints,
  updateItemTitle,
  workspaceDocument,
} = useExamWorkspaceDocument();

const { exportBlockersByItemId, exportDocument, exportNotice, exportingTarget } =
  useExamWorkspaceExports(summary);

const {
  dismissProposal,
  enrichmentMessage,
  isEnrichmentPending,
  isRequesting,
  openProposals,
  proposalForItem,
  requestProposals,
} = useExamWorkspaceEnrichment(summary);

const sourceFileError = ref<string | null>(null);

const itemRows = computed(() =>
  workspaceDocument.value ? toExamWorkspaceItemRows(workspaceDocument.value.items) : [],
);

const proposalItemIds = computed(() =>
  openProposals.value.map((proposal) => proposal.item_id),
);

const selectedProposal = computed(() =>
  selectedItem.value ? proposalForItem(selectedItem.value.item_id) : null,
);

const otherSavedDocuments = computed(() =>
  savedDocuments.value.filter((entry) => entry.lineage_id !== summary.value?.lineage_id),
);

function routeDocumentId(): string | null {
  const value = route.query.document;
  return typeof value === "string" && value.length > 0 ? value : null;
}

watch(
  () => summary.value?.lineage_id ?? null,
  (lineageId) => {
    if (lineageId && routeDocumentId() !== lineageId) {
      void router.replace({ query: { ...route.query, document: lineageId } });
    }
  },
);

// Follow later address changes (back/forward or an in-app link). The query
// already naming the open document is a no-op, which also absorbs the write
// from the summary watcher above. With unsaved edits the open document stays
// and the address is pointed back at it.
watch(
  () => routeDocumentId(),
  (lineageId) => {
    const openLineageId = summary.value?.lineage_id ?? null;
    if (!lineageId || lineageId === openLineageId) {
      return;
    }
    if (isDirty.value && openLineageId) {
      void router.replace({ query: { ...route.query, document: openLineageId } });
      return;
    }
    void openDocument(lineageId);
  },
);

onMounted(() => {
  const lineageId = routeDocumentId();
  if (lineageId) {
    void openDocument(lineageId);
  }
  void loadSavedDocuments();
});

function handleExport(target: ExamWorkspaceExportTarget): void {
  void exportDocument(target);
}

function handleApproveProposal(itemId: string): void {
  const proposal = proposalForItem(itemId);
  if (proposal) {
    applyProposal(itemId, proposal.proposed_item, true);
    dismissProposal(itemId);
  }
}

function handleEditProposal(itemId: string): void {
  const proposal = proposalForItem(itemId);
  if (proposal) {
    applyProposal(itemId, proposal.proposed_item, false);
    dismissProposal(itemId);
  }
}

function isDocxFile(file: File): boolean {
  return file.name.toLowerCase().endsWith(DOCX_EXTENSION);
}

async function handleSelectedFile(file: File): Promise<void> {
  if (!isDocxFile(file)) {
    sourceFileError.value = INVALID_DOCX_COPY;
    return;
  }
  sourceFileError.value = null;
  await importDocument(file);
}

function handleSourceFileInput(event: Event): void {
  const input = event.target as HTMLInputElement;
  const [file] = Array.from(input.files ?? []);
  if (file) {
    void handleSelectedFile(file);
  }
  input.value = "";
}

function handleDrop(event: DragEvent): void {
  const files = Array.from(event.dataTransfer?.files ?? []);
  const docxFiles = files.filter(isDocxFile);
  if (docxFiles.length > 1) {
    sourceFileError.value = MULTIPLE_FILES_COPY;
    return;
  }
  const [file] = docxFiles;
  if (file) {
    sourceFileError.value = null;
    void importDocument(file);
    return;
  }
  sourceFileError.value = INVALID_DOCX_COPY;
}
</script>

<template>
  <main
    class="min-h-[calc(100vh-72px)] overflow-x-hidden bg-canvas px-3 py-4 text-navy md:px-5 lg:px-6"
    aria-labelledby="exam-workspace-title"
  >
    <section
      class="mx-auto grid min-h-[28rem] w-full min-w-0 max-w-[90rem] grid-cols-1 items-stretch border border-navy bg-panel shadow-brutal-sm xl:grid-cols-[minmax(14rem,17rem)_minmax(0,1fr)] 2xl:grid-cols-[minmax(15rem,18rem)_minmax(0,1fr)]"
      aria-label="Provredigering"
      data-test="exam-workspace-frame"
    >
      <aside
        class="border-b border-navy/20 bg-panel p-4 xl:border-b-0 xl:border-r"
        aria-labelledby="exam-workspace-title"
        data-test="exam-workspace-rail"
      >
        <h1
          id="exam-workspace-title"
          class="text-base font-semibold leading-tight text-navy"
        >
          Provredigering
        </h1>

        <div class="mt-5 grid gap-6">
          <section class="grid gap-2">
            <h2 class="text-sm font-semibold leading-tight text-navy">
              Provfil
            </h2>
            <label
              class="grid cursor-pointer gap-2 border border-dashed border-navy/35 bg-panel px-3 py-4 text-center hover:bg-canvas"
              :class="isBusy ? 'cursor-not-allowed opacity-60' : undefined"
              data-test="exam-workspace-drop-zone"
              @dragover.prevent
              @drop.prevent="handleDrop"
            >
              <input
                class="sr-only"
                type="file"
                accept=".docx"
                :disabled="isBusy"
                data-test="exam-workspace-source-file-input"
                @change="handleSourceFileInput"
              >
              <Upload
                class="mx-auto h-5 w-5 text-action"
                aria-hidden="true"
              />
              <span class="text-sm font-medium leading-snug text-navy">
                Välj provfil (.docx)
              </span>
              <span class="text-xs leading-snug text-navy/65">
                Dra hit .docx-filen eller välj provfilen här.
              </span>
            </label>
            <p
              v-if="sourceFileError"
              class="text-xs leading-snug text-error"
              data-test="exam-workspace-source-file-error"
            >
              {{ sourceFileError }}
            </p>
            <p
              v-else-if="!workspaceDocument"
              class="text-xs leading-snug text-navy/65"
            >
              Ladda upp ett .docx-prov för att börja.
            </p>
          </section>

          <ExamWorkspaceSavedDocuments
            :documents="otherSavedDocuments"
            :is-busy="isBusy"
            :is-dirty="isDirty"
            @open="openDocument"
          />

          <section
            v-if="workspaceDocument && summary"
            class="grid gap-2"
            data-test="exam-workspace-summary"
          >
            <h2 class="text-sm font-semibold leading-tight text-navy">
              Aktuellt prov
            </h2>
            <div class="grid gap-1 border border-navy/20 bg-canvas p-3">
              <span
                class="truncate text-sm font-medium leading-snug text-navy"
                data-test="exam-workspace-summary-title"
              >
                {{ workspaceDocument.title || summary.name }}
              </span>
              <span
                class="text-xs leading-snug text-navy/65"
                data-test="exam-workspace-summary-version"
              >
                Version {{ summary.version }}
              </span>
              <UiDenseStatusPill
                v-if="isDirty"
                class="justify-self-start"
                label="Osparat"
                tone="warning"
                data-test="exam-workspace-dirty-pill"
              />
            </div>
            <div class="grid gap-2">
              <button
                type="button"
                class="btn-cta justify-center shadow-none"
                :disabled="!isDirty || isBusy"
                data-test="exam-workspace-save"
                @click="saveDocument"
              >
                Spara
              </button>
              <button
                type="button"
                class="btn-ghost justify-center shadow-none"
                :disabled="isBusy"
                data-test="exam-workspace-reload"
                @click="reloadDocument"
              >
                Läs in på nytt
              </button>
            </div>
          </section>

          <ExamWorkspaceExportPanel
            v-if="workspaceDocument"
            :export-notice="exportNotice"
            :exporting-target="exportingTarget"
            :is-busy="isBusy"
            :is-dirty="isDirty"
            @export="handleExport"
          />

          <ExamWorkspaceEnrichmentPanel
            v-if="workspaceDocument && summary"
            :disabled="isDirty || isBusy || isRequesting || isEnrichmentPending"
            :message="enrichmentMessage"
            @request="requestProposals"
          />
        </div>
      </aside>

      <div
        class="min-w-0"
        data-test="exam-workspace-workspace"
      >
        <p
          v-if="conflictNotice"
          class="border-b border-navy bg-saffron px-4 py-2 text-xs font-semibold leading-snug"
          data-test="exam-workspace-conflict-notice"
        >
          {{ conflictNotice }}
        </p>

        <section
          v-if="workspaceDocument"
          class="grid gap-4 p-4"
          aria-label="Frågor"
        >
          <header class="flex flex-wrap items-center justify-between gap-3">
            <h2 class="text-sm font-semibold leading-tight text-navy">
              Frågor
            </h2>
            <button
              type="button"
              class="btn-ghost shadow-none"
              :disabled="isBusy"
              data-test="exam-workspace-add-item"
              @click="addItem"
            >
              Lägg till fråga
            </button>
          </header>

          <ul
            v-if="notes.length > 0"
            class="grid gap-1 text-xs leading-snug text-navy/70"
            data-test="exam-workspace-notes"
          >
            <li
              v-for="note in notes"
              :key="note"
            >
              {{ note }}
            </li>
          </ul>

          <ExamWorkspaceItemTable
            :export-blockers-by-item-id="exportBlockersByItemId"
            :proposal-item-ids="proposalItemIds"
            :rows="itemRows"
            :selected-item-id="selectedItemId"
            @select="selectItem"
          />

          <ExamWorkspaceItemEditor
            v-if="selectedItem"
            :item="selectedItem"
            @mark-reviewed="markItemReviewed"
            @update-body-text="updateItemBodyText"
            @update-choice-text="updateItemChoiceText"
            @update-correct-choices="updateItemCorrectChoices"
            @update-gap-values="updateItemGapValues"
            @update-points="updateItemPoints"
            @update-title="updateItemTitle"
          />

          <ExamWorkspaceProposalPanel
            v-if="selectedItem && selectedProposal"
            :disabled="isBusy"
            :item="selectedItem"
            :proposed-item="selectedProposal.proposed_item"
            @approve="handleApproveProposal"
            @dismiss="dismissProposal"
            @edit="handleEditProposal"
          />
        </section>

        <section
          v-else
          class="grid min-h-[20rem] place-items-center p-8 text-center"
          data-test="exam-workspace-empty"
        >
          <div class="grid gap-2">
            <h2 class="text-sm font-semibold leading-tight text-navy">
              Inget prov är inläst
            </h2>
            <p class="text-xs leading-snug text-navy/65">
              Ladda upp ett .docx-prov eller öppna ett sparat prov för att börja.
            </p>
          </div>
        </section>
      </div>
    </section>
  </main>
</template>
