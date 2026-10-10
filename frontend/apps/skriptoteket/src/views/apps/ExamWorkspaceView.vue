<script setup lang="ts">
/**
 * Teacher exam workspace host frame.
 *
 * Domain purpose:
 *   Convert a .docx exam into files Exam.net imports as intended, in two
 *   modes switched in one stable toolbar: Filer (import, saved exams,
 *   readiness, QTI/PDF/DOCX files, answer-key proposals) and Redigera
 *   (question list plus one dominating editor, with question details in a
 *   drawer). Save state stays in the toolbar in both modes. Desktop is the
 *   canonical composition; tablet narrows it and overlays the drawer; phone
 *   makes the editor the screen with a "Fråga N av M" question sheet.
 *
 * Relationships:
 *   - Mounted by the canonical `/apps/exam-workspace` route; the
 *     `?document=<lineage_id>` query opens a saved document, on load and
 *     when the query changes later.
 *   - Owns state through `useExamWorkspaceDocument`,
 *     `useExamWorkspaceExports`, and `useExamWorkspaceEnrichment`; selects
 *     the composition through `useExamWorkspaceLayout`; mirrors the export
 *     gate per question through `examWorkspaceItemReadiness`.
 *   - Renders `ExamWorkspaceFilesMode`, `ExamWorkspaceItemTable`,
 *     `ExamWorkspaceItemEditor`, `ExamWorkspaceItemDrawer`, and, on phones,
 *     `ExamWorkspaceSheet`.
 */

import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { ChevronDown } from "lucide-vue-next";

import {
  IconNextPage,
  IconPlus,
  IconPreviousPage,
  IconWarning,
} from "../../components/icons";
import { UiDenseStatusPill, UiSegmentedToggle } from "../../components/ui";
import type { UiSegmentedToggleOption } from "../../components/ui";
import type { ExamWorkspaceExportTarget } from "../../api/examWorkspace";
import ExamWorkspaceFilesMode from "./exam-workspace/ExamWorkspaceFilesMode.vue";
import type { ExamWorkspaceReadinessEntry } from "./exam-workspace/ExamWorkspaceFilesMode.vue";
import ExamWorkspaceItemDrawer from "./exam-workspace/ExamWorkspaceItemDrawer.vue";
import ExamWorkspaceItemEditor from "./exam-workspace/ExamWorkspaceItemEditor.vue";
import ExamWorkspaceItemTable from "./exam-workspace/ExamWorkspaceItemTable.vue";
import ExamWorkspaceSheet from "./exam-workspace/ExamWorkspaceSheet.vue";
import { examWorkspaceReadinessByItemId } from "./exam-workspace/examWorkspaceItemReadiness";
import { toExamWorkspaceItemRows } from "./exam-workspace/examWorkspaceRows";
import { useExamWorkspaceDocument } from "./exam-workspace/useExamWorkspaceDocument";
import { useExamWorkspaceEnrichment } from "./exam-workspace/useExamWorkspaceEnrichment";
import { useExamWorkspaceExports } from "./exam-workspace/useExamWorkspaceExports";
import { useExamWorkspaceLayout } from "./exam-workspace/useExamWorkspaceLayout";

type ExamWorkspaceMode = "filer" | "redigera";

const DOCX_EXTENSION = ".docx";
const INVALID_DOCX_COPY = "Det gick inte att använda filen. Välj en .docx-fil.";
const MULTIPLE_FILES_COPY = "Välj en provfil åt gången.";

const route = useRoute();
const router = useRouter();
const layout = useExamWorkspaceLayout();

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
  updateItemChoiceText,
  updateItemCorrectChoices,
  updateItemGapValues,
  updateItemParagraphSegments,
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

const mode = ref<ExamWorkspaceMode>("filer");
const detailsOpen = ref(false);
const questionSheetOpen = ref(false);
const sourceFileError = ref<string | null>(null);

const isPhone = computed(() => layout.value === "phone");

const modeOptions = computed<UiSegmentedToggleOption[]>(() => [
  { dataTest: "exam-workspace-mode-filer", label: "Filer", value: "filer" },
  {
    dataTest: "exam-workspace-mode-redigera",
    disabled: !workspaceDocument.value,
    label: "Redigera",
    value: "redigera",
  },
]);

const items = computed(() => workspaceDocument.value?.items ?? []);

const itemRows = computed(() => toExamWorkspaceItemRows(items.value));

const readinessByItemId = computed(() => examWorkspaceReadinessByItemId(items.value));

const readinessEntries = computed<ExamWorkspaceReadinessEntry[]>(() =>
  items.value
    .filter((item) => readinessByItemId.value[item.item_id])
    .map((item) => ({
      itemId: item.item_id,
      reasons: readinessByItemId.value[item.item_id] ?? [],
      sequence: item.sequence,
      title: item.title ?? "",
    })),
);

const proposalItemIds = computed(() =>
  openProposals.value.map((proposal) => proposal.item_id),
);

const selectedProposal = computed(() =>
  selectedItem.value ? proposalForItem(selectedItem.value.item_id) : null,
);

const selectedPosition = computed(() => {
  const index = items.value.findIndex((item) => item.item_id === selectedItemId.value);
  return index + 1;
});

const selectedReadiness = computed(() =>
  selectedItem.value ? (readinessByItemId.value[selectedItem.value.item_id] ?? []) : [],
);

const selectedServerBlockers = computed(() =>
  selectedItem.value ? (exportBlockersByItemId.value[selectedItem.value.item_id] ?? []) : [],
);

const otherSavedDocuments = computed(() =>
  savedDocuments.value.filter((entry) => entry.lineage_id !== summary.value?.lineage_id),
);

const enrichmentDisabled = computed(
  () => isDirty.value || isBusy.value || isRequesting.value || isEnrichmentPending.value,
);

const redigeraGridClass = computed(() => {
  if (layout.value === "desktop") {
    return "h-full grid-cols-[minmax(15rem,19rem)_minmax(0,1fr)]";
  }
  return layout.value === "tablet"
    ? "h-full grid-cols-[minmax(12rem,15rem)_minmax(0,1fr)]"
    : "grid-cols-1";
});

// Desktop keeps the drawer beside the editor, tablet lays it over the
// editor, and phone gives it the whole screen.
const drawerFrameClass = computed(() => {
  if (layout.value === "desktop") {
    return "min-h-0 w-[22rem] shrink-0 overflow-y-auto border-l border-navy/20";
  }
  if (layout.value === "tablet") {
    return "absolute inset-y-0 right-0 z-10 w-[min(22rem,90%)] overflow-y-auto border-l border-navy bg-panel shadow-brutal-sm";
  }
  return "fixed inset-0 z-50 overflow-y-auto bg-panel";
});

// Opening another exam starts in Redigera; closing it returns to Filer.
watch(
  () => summary.value?.lineage_id ?? null,
  (lineageId, previousLineageId) => {
    if (!lineageId) {
      mode.value = "filer";
    } else if (lineageId !== previousLineageId) {
      mode.value = "redigera";
    }
  },
);

// A waiting answer-key proposal is the next thing to decide, so the drawer
// opens by itself for it.
watch(
  () => selectedProposal.value?.item_id ?? null,
  (proposalItemId) => {
    if (proposalItemId) {
      detailsOpen.value = true;
    }
  },
);

function setMode(value: string): void {
  mode.value = value === "redigera" && workspaceDocument.value ? "redigera" : "filer";
}

function selectAndClose(itemId: string): void {
  selectItem(itemId);
  questionSheetOpen.value = false;
}

function stepItem(offset: number): void {
  const target = items.value[selectedPosition.value - 1 + offset];
  if (target) {
    selectItem(target.item_id);
  }
}

function goToItem(itemId: string): void {
  selectItem(itemId);
  mode.value = "redigera";
  detailsOpen.value = true;
}

function handleAddItem(): void {
  addItem();
  questionSheetOpen.value = false;
}

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

// Point the address back at the open document, or drop `document` when
// nothing is open. Both outcomes are no-ops for the address watcher below.
function restoreDocumentAddress(): void {
  const openLineageId = summary.value?.lineage_id ?? null;
  const { document: _document, ...rest } = route.query;
  void router.replace({ query: openLineageId ? { ...rest, document: openLineageId } : rest });
}

// Follow later address changes (back/forward or an in-app link). The query
// already naming the open document is a no-op, which also absorbs the write
// from the summary watcher above. With unsaved edits, or when the named
// document does not open, the open document stays and the address is pointed
// back at it.
watch(
  () => routeDocumentId(),
  async (lineageId) => {
    const openLineageId = summary.value?.lineage_id ?? null;
    if (!lineageId || lineageId === openLineageId) {
      return;
    }
    if (isDirty.value && openLineageId) {
      restoreDocumentAddress();
      return;
    }
    const opened = await openDocument(lineageId);
    if (!opened && routeDocumentId() === lineageId) {
      restoreDocumentAddress();
    }
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
    detailsOpen.value = false;
  }
}

function isDocxFile(file: File): boolean {
  return file.name.toLowerCase().endsWith(DOCX_EXTENSION);
}

function handleSelectedFile(file: File): void {
  if (!isDocxFile(file)) {
    sourceFileError.value = INVALID_DOCX_COPY;
    return;
  }
  sourceFileError.value = null;
  void importDocument(file);
}

function handleDroppedFiles(files: File[]): void {
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
    class="bg-canvas px-3 py-3 text-navy md:px-5 lg:px-6"
    aria-labelledby="exam-workspace-title"
  >
    <section
      class="mx-auto flex w-full min-w-0 max-w-[100rem] flex-col border border-navy bg-panel shadow-brutal-sm"
      :class="isPhone ? 'min-h-[calc(100dvh-72px-1.5rem)]' : 'h-[max(35rem,calc(100dvh-72px-1.5rem))]'"
      aria-label="Provredigering"
      :data-layout="layout"
      data-test="exam-workspace-frame"
    >
      <header
        class="grid gap-2 border-b border-navy bg-panel px-4 py-2.5"
        :class="isPhone ? 'sticky top-0 z-20' : undefined"
        data-test="exam-workspace-toolbar"
      >
        <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
          <h1
            id="exam-workspace-title"
            class="text-sm font-extrabold uppercase leading-none tracking-wide text-navy"
            :class="isPhone ? 'sr-only' : undefined"
          >
            Provredigering
          </h1>
          <UiSegmentedToggle
            :model-value="mode"
            :options="modeOptions"
            aria-label="Läge"
            density="compact"
            width="auto"
            @update:model-value="setMode"
          />
          <div
            v-if="workspaceDocument && summary"
            class="flex min-w-0 flex-1 items-center justify-end gap-3"
            data-test="exam-workspace-summary"
          >
            <span
              class="min-w-0 truncate text-sm font-medium leading-snug text-navy"
              :class="isPhone ? 'sr-only' : undefined"
              data-test="exam-workspace-summary-title"
            >
              {{ workspaceDocument.title || summary.name }}
            </span>
            <span
              class="shrink-0 text-xs leading-snug text-navy/65"
              data-test="exam-workspace-summary-version"
            >
              Version {{ summary.version }}
            </span>
            <UiDenseStatusPill
              v-if="isDirty"
              label="Osparat"
              tone="warning"
              data-test="exam-workspace-dirty-pill"
            />
            <button
              type="button"
              class="btn-cta shrink-0 shadow-none"
              :disabled="!isDirty || isBusy"
              data-test="exam-workspace-save"
              @click="saveDocument"
            >
              Spara
            </button>
          </div>
        </div>

        <div
          v-if="isPhone && mode === 'redigera' && selectedItem"
          class="grid grid-cols-[auto_minmax(0,1fr)_auto] items-stretch"
          data-test="exam-workspace-phone-question-bar"
        >
          <button
            type="button"
            class="inline-flex h-11 w-11 items-center justify-center border border-navy/35 bg-panel disabled:opacity-40"
            aria-label="Föregående fråga"
            :disabled="selectedPosition <= 1"
            data-test="exam-workspace-phone-previous"
            @click="stepItem(-1)"
          >
            <IconPreviousPage :size="20" />
          </button>
          <button
            type="button"
            class="-mx-px inline-flex h-11 min-w-0 items-center justify-center gap-2 border border-navy/35 bg-panel px-3 text-sm font-semibold text-navy"
            aria-haspopup="dialog"
            :aria-expanded="questionSheetOpen ? 'true' : 'false'"
            data-test="exam-workspace-question-picker"
            @click="questionSheetOpen = true"
          >
            <span class="truncate">Fråga {{ selectedPosition }} av {{ items.length }}</span>
            <IconWarning
              v-if="readinessEntries.length > 0"
              :size="16"
              class="h-4 w-4 shrink-0 text-warning"
              aria-hidden="true"
            />
            <ChevronDown
              class="h-4 w-4 shrink-0"
              aria-hidden="true"
            />
          </button>
          <button
            type="button"
            class="inline-flex h-11 w-11 items-center justify-center border border-navy/35 bg-panel disabled:opacity-40"
            aria-label="Nästa fråga"
            :disabled="selectedPosition >= items.length"
            data-test="exam-workspace-phone-next"
            @click="stepItem(1)"
          >
            <IconNextPage :size="20" />
          </button>
        </div>
      </header>

      <p
        v-if="conflictNotice"
        class="border-b border-navy bg-saffron px-4 py-2 text-xs font-semibold leading-snug"
        data-test="exam-workspace-conflict-notice"
      >
        {{ conflictNotice }}
      </p>

      <div class="flex min-h-0 flex-1 flex-col">
        <div
          v-show="mode === 'filer'"
          class="min-h-0 flex-1 overflow-y-auto"
          role="region"
          aria-label="Filer"
          data-test="exam-workspace-rail"
        >
          <ExamWorkspaceFilesMode
            :compact="isPhone"
            :enrichment-disabled="enrichmentDisabled"
            :enrichment-message="enrichmentMessage"
            :export-notice="exportNotice"
            :exporting-target="exportingTarget"
            :has-document="workspaceDocument !== null"
            :is-busy="isBusy"
            :is-dirty="isDirty"
            :notes="notes"
            :readiness="readinessEntries"
            :saved-documents="otherSavedDocuments"
            :source-file-error="sourceFileError"
            @drop-files="handleDroppedFiles"
            @export="handleExport"
            @go-to-item="goToItem"
            @open="openDocument"
            @reload="reloadDocument"
            @request-proposals="requestProposals"
            @select-file="handleSelectedFile"
          />
        </div>

        <div
          v-show="mode === 'redigera'"
          class="min-h-0 flex-1"
          role="region"
          aria-label="Redigera"
          data-test="exam-workspace-workspace"
        >
          <div
            v-if="workspaceDocument"
            class="grid min-h-0"
            :class="redigeraGridClass"
          >
            <section
              v-if="!isPhone"
              class="flex min-h-0 flex-col border-r border-navy/20"
              aria-labelledby="exam-workspace-questions-title"
              data-test="exam-workspace-question-list"
            >
              <header class="flex items-center justify-between gap-2 border-b border-navy/20 px-3 py-2">
                <h2
                  id="exam-workspace-questions-title"
                  class="text-sm font-semibold leading-tight text-navy"
                >
                  Frågor <span class="font-normal text-navy/65">({{ items.length }})</span>
                </h2>
                <button
                  type="button"
                  class="inline-flex h-8 items-center gap-1 border border-navy/35 bg-panel px-2 text-xs font-semibold text-navy hover:bg-canvas disabled:opacity-50"
                  :disabled="isBusy"
                  data-test="exam-workspace-add-item"
                  @click="handleAddItem"
                >
                  <IconPlus
                    :size="14"
                    class="h-3.5 w-3.5"
                  />
                  Ny fråga
                </button>
              </header>
              <div class="min-h-0 flex-1 overflow-y-auto">
                <ExamWorkspaceItemTable
                  :export-blockers-by-item-id="exportBlockersByItemId"
                  :proposal-item-ids="proposalItemIds"
                  :readiness-by-item-id="readinessByItemId"
                  :rows="itemRows"
                  :selected-item-id="selectedItemId"
                  @select="selectItem"
                />
              </div>
            </section>

            <div class="relative flex min-h-0 min-w-0">
              <div
                class="min-w-0 flex-1"
                :class="isPhone ? undefined : 'min-h-0 overflow-y-auto'"
              >
                <div :class="isPhone ? 'p-4' : 'mx-auto w-full max-w-[60rem] p-6'">
                  <ExamWorkspaceItemEditor
                    v-if="selectedItem"
                    :attention-count="selectedReadiness.length"
                    :details-open="detailsOpen"
                    :item="selectedItem"
                    :position="selectedPosition"
                    :show-navigation="!isPhone"
                    :total="items.length"
                    @mark-reviewed="markItemReviewed"
                    @next="stepItem(1)"
                    @previous="stepItem(-1)"
                    @toggle-details="detailsOpen = !detailsOpen"
                    @update-choice-text="updateItemChoiceText"
                    @update-correct-choices="updateItemCorrectChoices"
                    @update-gap-values="updateItemGapValues"
                    @update-paragraph-segments="updateItemParagraphSegments"
                    @update-points="updateItemPoints"
                    @update-title="updateItemTitle"
                  />
                  <p
                    v-else
                    class="text-sm text-navy/65"
                  >
                    Välj en fråga i listan.
                  </p>
                </div>
              </div>
              <div
                v-if="detailsOpen && selectedItem"
                :class="drawerFrameClass"
              >
                <ExamWorkspaceItemDrawer
                  :disabled="isBusy"
                  :item="selectedItem"
                  :proposed-item="selectedProposal?.proposed_item ?? null"
                  :readiness="selectedReadiness"
                  :server-blockers="selectedServerBlockers"
                  @approve="handleApproveProposal"
                  @close="detailsOpen = false"
                  @dismiss="dismissProposal"
                  @edit="handleEditProposal"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <ExamWorkspaceSheet
      v-if="isPhone && questionSheetOpen && workspaceDocument"
      title="Frågor"
      @close="questionSheetOpen = false"
    >
      <ExamWorkspaceItemTable
        :export-blockers-by-item-id="exportBlockersByItemId"
        :proposal-item-ids="proposalItemIds"
        :readiness-by-item-id="readinessByItemId"
        :rows="itemRows"
        :selected-item-id="selectedItemId"
        @select="selectAndClose"
      />
      <div class="p-4">
        <button
          type="button"
          class="btn-ghost w-full justify-center shadow-none"
          :disabled="isBusy"
          data-test="exam-workspace-phone-add-item"
          @click="handleAddItem"
        >
          Ny fråga
        </button>
      </div>
    </ExamWorkspaceSheet>
  </main>
</template>
