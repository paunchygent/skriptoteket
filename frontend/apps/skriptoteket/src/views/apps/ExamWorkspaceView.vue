<script setup lang="ts">
/**
 * Teacher exam workspace host frame.
 *
 * Domain purpose:
 *   Convert a .docx exam into files Exam.net imports as intended, in two
 *   modes switched in one stable toolbar: Filer (import, saved exams,
 *   readiness, QTI/PDF/DOCX files, answer-key suggestions) and Redigera
 *   (question list plus one dominating editor, with question details in a
 *   drawer). Save state stays in the toolbar in both modes. Desktop is the
 *   canonical composition; tablet narrows it and overlays the drawer; phone
 *   makes the editor the screen with a "Fråga N av M" question sheet.
 *
 * Relationships:
 *   - Mounted by the canonical `/apps/exam-workspace` route; the
 *     `?document=<lineage_id>` query and the open document stay in step
 *     through `useExamWorkspaceAddress`.
 *   - Owns state through `useExamWorkspaceDocument`,
 *     `useExamWorkspaceExports`, and `useExamWorkspaceEnrichment`; takes
 *     .docx files through `useExamWorkspaceSourceFile`; selects the
 *     composition through `useExamWorkspaceLayout`; mirrors the export gate
 *     and the save rules per question through `examWorkspaceItemReadiness`.
 *   - `ExamWorkspaceConversionStatus` renders conversion progress and retry;
 *     `ExamWorkspaceConvertingNotice` marks a question whose batch still
 *     converts, and the editor pane locks it until that batch arrives.
 *   - Files mode and `ExamWorkspaceEditorPane` (question list, editor, and
 *     drawer) render the workspace; phones add a question bar and sheet.
 *   - Resolves the open document's shared instructions and each parent's stem
 *     against its picture URLs once, so the list and sheet show the same text
 *     and diagrams read-only.
 */

import { computed, onMounted, ref, watch } from "vue";

import { UiDenseStatusPill, UiSegmentedToggle } from "../../components/ui";
import type { UiSegmentedToggleOption } from "../../components/ui";
import type { ExamWorkspaceExportTarget } from "../../api/examWorkspace";
import ExamWorkspaceConversionStatus from "./exam-workspace/ExamWorkspaceConversionStatus.vue";
import ExamWorkspaceConvertingNotice from "./exam-workspace/ExamWorkspaceConvertingNotice.vue";
import ExamWorkspaceFilesMode from "./exam-workspace/ExamWorkspaceFilesMode.vue";
import type { ExamWorkspaceReadinessEntry } from "./exam-workspace/ExamWorkspaceFilesMode.vue";
import ExamWorkspaceEditorPane from "./exam-workspace/ExamWorkspaceEditorPane.vue";
import ExamWorkspaceItemTable from "./exam-workspace/ExamWorkspaceItemTable.vue";
import ExamWorkspaceSharedInstruction from "./exam-workspace/ExamWorkspaceSharedInstruction.vue";
import ExamWorkspacePhoneQuestionBar from "./exam-workspace/ExamWorkspacePhoneQuestionBar.vue";
import ExamWorkspaceSheet from "./exam-workspace/ExamWorkspaceSheet.vue";
import { examWorkspaceReadinessByItemId } from "./exam-workspace/examWorkspaceItemReadiness";
import { toExamWorkspaceItemRows } from "./exam-workspace/examWorkspaceRows";
import { examWorkspaceSharedParagraphs } from "./exam-workspace/examWorkspaceSharedInstruction";
import { useExamWorkspaceAddress } from "./exam-workspace/useExamWorkspaceAddress";
import { useExamWorkspaceDocument } from "./exam-workspace/useExamWorkspaceDocument";
import { useExamWorkspaceEnrichment } from "./exam-workspace/useExamWorkspaceEnrichment";
import { useExamWorkspaceExports } from "./exam-workspace/useExamWorkspaceExports";
import { useExamWorkspaceLayout } from "./exam-workspace/useExamWorkspaceLayout";
import { useExamWorkspaceSourceFile } from "./exam-workspace/useExamWorkspaceSourceFile";

type ExamWorkspaceMode = "filer" | "redigera";

const layout = useExamWorkspaceLayout();

const {
  addItem,
  applyArrivingSuggestions,
  assetUrls,
  conflictNotice,
  conversionError,
  conversionMessage,
  conversionProgress,
  convertingItemIds,
  isConverting,
  retryConversionStatus,
  importBlocked,
  importDocument,
  isBusy,
  isDirty,
  isOpen,
  loadSavedDocuments,
  markItemReviewed,
  notes,
  openDocument,
  openExam,
  reloadDocument,
  retryItem,
  saveDocument,
  savedDocuments,
  savedRevision,
  selectItem,
  selectedItem,
  selectedItemId,
  summary,
  updateItemChoiceText,
  updateItemCorrectChoices,
  updateItemGapValues,
  undoItemInterpretation,
  removeItemAutomaticValue,
  showItemGapAsText,
  updateItemCriteria,
  updateItemMatchEntryText,
  updateItemMatchPairs,
  updateItemParagraphSegments,
  updateItemPoints,
  updateItemTickPoints,
  workspaceDocument,
} = useExamWorkspaceDocument();

const { showDocument } = useExamWorkspaceAddress({ isDirty, openDocument, summary });

const { handleDroppedFiles, handleSelectedFile, sourceFileError } =
  useExamWorkspaceSourceFile(importDocument, importBlocked);

const { exportBlockersByItemId, exportDocument, exportNotice, exportingTarget } =
  useExamWorkspaceExports(summary);

const {
  enrichmentLookupError,
  enrichmentMessage,
  isEnrichmentPending,
  isRequesting,
  requestSuggestionsForAll,
  retryEnrichmentLookup,
} = useExamWorkspaceEnrichment({
  applySuggestions: applyArrivingSuggestions,
  document: workspaceDocument,
  isOpen,
  openExam,
  savedRevision,
});

const mode = ref<ExamWorkspaceMode>("filer");
const detailsOpen = ref(false);
const questionSheetOpen = ref(false);

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

const itemRows = computed(() =>
  toExamWorkspaceItemRows(
    items.value,
    workspaceDocument.value?.parents ?? [],
    assetUrls.value,
  ),
);

const selectedAiKeyLabel = computed(() =>
  itemRows.value.find((row) => row.itemId === selectedItemId.value)?.aiKeyLabel ?? null,
);

/** The exam's shared instructions with their pictures resolved, once above the rows. */
const globalInstructions = computed(() =>
  examWorkspaceSharedParagraphs(workspaceDocument.value?.instructions ?? [], assetUrls.value),
);

const readinessByItemId = computed(() => examWorkspaceReadinessByItemId(items.value));

const readinessEntries = computed<ExamWorkspaceReadinessEntry[]>(() =>
  items.value
    .filter((item) => readinessByItemId.value[item.item_id])
    .map((item) => ({
      itemId: item.item_id,
      reasons: readinessByItemId.value[item.item_id] ?? [],
      sequence: item.sequence,
    })),
);

const selectedPosition = computed(() => {
  const index = items.value.findIndex((item) => item.item_id === selectedItemId.value);
  return index + 1;
});

const otherSavedDocuments = computed(() =>
  savedDocuments.value.filter((entry) => entry.lineage_id !== summary.value?.lineage_id),
);

// Suggestion requests send the editor's current document, so unsaved
// changes never disable them (TASK-SKRIPT-39-04-07).
const enrichmentDisabled = computed(
  () => isBusy.value || isRequesting.value || isEnrichmentPending.value,
);

// A newly open exam goes into the address and starts in Redigera; closing
// it returns to Filer.
watch(
  () => summary.value?.lineage_id ?? null,
  (lineageId, previousLineageId) => {
    showDocument(lineageId);
    if (!lineageId) {
      mode.value = "filer";
    } else if (lineageId !== previousLineageId) {
      mode.value = "redigera";
    }
  },
);

// The question sheet exists only on phones; leaving the phone layout closes it.
watch(isPhone, (phone) => {
  if (!phone) {
    questionSheetOpen.value = false;
  }
});

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

onMounted(() => {
  void loadSavedDocuments();
});

function handleExport(target: ExamWorkspaceExportTarget): void {
  if (!isBusy.value) void exportDocument(target);
}

async function handleSave(): Promise<void> {
  await saveDocument();
}
</script>

<template>
  <main
    class="flex min-h-0 flex-1 flex-col bg-canvas text-navy"
    aria-labelledby="exam-workspace-title"
  >
    <section
      class="mx-auto flex w-full min-w-0 max-w-[100rem] flex-1 flex-col"
      :class="isPhone ? undefined : 'min-h-[35rem] border border-navy bg-panel shadow-brutal-sm'"
      aria-label="Provredigering"
      :data-layout="layout"
      data-test="exam-workspace-frame"
    >
      <header
        class="grid gap-2 border-b border-navy py-2.5"
        :class="isPhone ? 'sticky top-0 z-20 bg-modal' : 'bg-panel px-4'"
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
              @click="handleSave"
            >
              Spara
            </button>
          </div>
        </div>

        <ExamWorkspacePhoneQuestionBar
          v-if="isPhone && mode === 'redigera' && selectedItem"
          :ai-key-label="selectedAiKeyLabel"
          :needs-attention="readinessEntries.length > 0"
          :position="selectedPosition"
          :sheet-open="questionSheetOpen"
          :total="items.length"
          @next="stepItem(1)"
          @open-questions="questionSheetOpen = true"
          @previous="stepItem(-1)"
        />
      </header>

      <ExamWorkspaceConversionStatus
        :conversion-message="conversionMessage"
        :conversion-error="conversionError"
        :conversion-progress="conversionProgress"
        :is-converting="isConverting"
        @retry="retryConversionStatus"
      />

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
            :enrichment-lookup-error="enrichmentLookupError"
            :enrichment-message="enrichmentMessage"
            :export-notice="exportNotice"
            :exporting-target="exportingTarget"
            :has-document="workspaceDocument !== null"
            :import-blocked="importBlocked"
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
            @request-proposals="requestSuggestionsForAll"
            @retry-enrichment-lookup="retryEnrichmentLookup"
            @select-file="handleSelectedFile"
          />
        </div>

        <div
          v-show="mode === 'redigera'"
          class="flex min-h-0 flex-1 flex-col"
          role="region"
          aria-label="Redigera"
          data-test="exam-workspace-workspace"
        >
          <ExamWorkspaceConvertingNotice
            v-if="selectedItemId !== null && convertingItemIds.has(selectedItemId)"
          />
          <ExamWorkspaceEditorPane
            v-if="workspaceDocument"
            v-model:details-open="detailsOpen"
            :asset-urls="assetUrls"
            :disabled="isBusy"
            :export-blockers-by-item-id="exportBlockersByItemId"
            :global-instructions="globalInstructions"
            :item-count="items.length"
            :item-rows="itemRows"
            :layout="layout"
            :readiness-by-item-id="readinessByItemId"
            :selected-item="selectedItem"
            :selected-item-id="selectedItemId"
            :selected-item-locked="selectedItemId !== null && convertingItemIds.has(selectedItemId)"
            :selected-position="selectedPosition"
            @add="handleAddItem"
            @mark-reviewed="markItemReviewed"
            @retry="retryItem"
            @select="selectItem"
            @step="stepItem"
            @update-choice-text="updateItemChoiceText"
            @update-correct-choices="updateItemCorrectChoices"
            @update-gap-values="updateItemGapValues"
            @undo-interpretation="undoItemInterpretation"
            @remove-automatic-value="removeItemAutomaticValue"
            @show-gap-as-text="showItemGapAsText"
            @update-criteria="updateItemCriteria"
            @update-match-entry-text="updateItemMatchEntryText"
            @update-match-pairs="updateItemMatchPairs"
            @update-paragraph-segments="updateItemParagraphSegments"
            @update-points="updateItemPoints"
            @update-tick-points="updateItemTickPoints"
          />
        </div>
      </div>
    </section>

    <ExamWorkspaceSheet
      v-if="isPhone && questionSheetOpen && workspaceDocument"
      title="Frågor"
      @close="questionSheetOpen = false"
    >
      <ExamWorkspaceSharedInstruction
        v-if="globalInstructions.length > 0"
        :paragraphs="globalInstructions"
        class="border-b border-navy/15 bg-canvas px-3 py-2"
        data-test="exam-workspace-global-instruction"
      />
      <ExamWorkspaceItemTable
        :export-blockers-by-item-id="exportBlockersByItemId"
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
