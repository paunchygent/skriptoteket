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
 *     `?document=<lineage_id>` query and the open document stay in step
 *     through `useExamWorkspaceAddress`.
 *   - Owns state through `useExamWorkspaceDocument`,
 *     `useExamWorkspaceExports`, and `useExamWorkspaceEnrichment`; takes
 *     .docx files through `useExamWorkspaceSourceFile`; selects the
 *     composition through `useExamWorkspaceLayout`; mirrors the export gate
 *     and the save rules per question through `examWorkspaceItemReadiness`.
 *   - Renders `ExamWorkspaceFilesMode`, `ExamWorkspaceQuestionList` with
 *     `ExamWorkspaceItemTable`, `ExamWorkspaceItemEditor`, and
 *     `ExamWorkspaceItemDrawer`; on phones, `ExamWorkspacePhoneQuestionBar`
 *     and the question list in `ExamWorkspaceSheet`.
 */

import { computed, onMounted, ref, watch } from "vue";

import { UiDenseStatusPill, UiSegmentedToggle } from "../../components/ui";
import type { UiSegmentedToggleOption } from "../../components/ui";
import type { ExamWorkspaceExportTarget } from "../../api/examWorkspace";
import ExamWorkspaceFilesMode from "./exam-workspace/ExamWorkspaceFilesMode.vue";
import type { ExamWorkspaceReadinessEntry } from "./exam-workspace/ExamWorkspaceFilesMode.vue";
import ExamWorkspaceItemDrawer from "./exam-workspace/ExamWorkspaceItemDrawer.vue";
import ExamWorkspaceItemEditor from "./exam-workspace/ExamWorkspaceItemEditor.vue";
import ExamWorkspaceItemTable from "./exam-workspace/ExamWorkspaceItemTable.vue";
import ExamWorkspacePhoneQuestionBar from "./exam-workspace/ExamWorkspacePhoneQuestionBar.vue";
import ExamWorkspaceQuestionList from "./exam-workspace/ExamWorkspaceQuestionList.vue";
import ExamWorkspaceSheet from "./exam-workspace/ExamWorkspaceSheet.vue";
import { examWorkspaceReadinessByItemId } from "./exam-workspace/examWorkspaceItemReadiness";
import { toExamWorkspaceItemRows } from "./exam-workspace/examWorkspaceRows";
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

const { showDocument } = useExamWorkspaceAddress({ isDirty, openDocument, summary });

const { handleDroppedFiles, handleSelectedFile, sourceFileError } =
  useExamWorkspaceSourceFile(importDocument);

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

// A waiting answer-key proposal is the next thing to decide, so the drawer
// opens by itself for it, in place of the phone question sheet.
watch(
  () => selectedProposal.value?.item_id ?? null,
  (proposalItemId) => {
    if (proposalItemId) {
      questionSheetOpen.value = false;
      detailsOpen.value = true;
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

        <ExamWorkspacePhoneQuestionBar
          v-if="isPhone && mode === 'redigera' && selectedItem"
          :needs-attention="readinessEntries.length > 0"
          :position="selectedPosition"
          :sheet-open="questionSheetOpen"
          :total="items.length"
          @next="stepItem(1)"
          @open-questions="questionSheetOpen = true"
          @previous="stepItem(-1)"
        />
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
            <ExamWorkspaceQuestionList
              v-if="!isPhone"
              :count="items.length"
              :disabled="isBusy"
              @add="handleAddItem"
            >
              <ExamWorkspaceItemTable
                :export-blockers-by-item-id="exportBlockersByItemId"
                :proposal-item-ids="proposalItemIds"
                :readiness-by-item-id="readinessByItemId"
                :rows="itemRows"
                :selected-item-id="selectedItemId"
                @select="selectItem"
              />
            </ExamWorkspaceQuestionList>

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
                    :disabled="isBusy"
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
              <ExamWorkspaceItemDrawer
                v-if="detailsOpen && selectedItem"
                :disabled="isBusy"
                :item="selectedItem"
                :layout="layout"
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
