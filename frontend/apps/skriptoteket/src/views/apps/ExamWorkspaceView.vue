<script setup lang="ts">
/**
 * Teacher exam workspace (TASK-SKRIPT-40-04-03).
 *
 * Domain purpose:
 *   One surface for an exam: the header with the exam's title, save state
 *   and tools; the question list; the editor for the selected question or
 *   instruction; and one drawer at a time for Öppna, Exportera and Provets
 *   uppgifter. Desktop (>= 1280 px) docks the drawer as a third column,
 *   tablet floats it over the editor, phone covers the screen with it; on a
 *   phone the list is a layer opened from the question strip and the
 *   header's title and Spara sit in the shell's top bar.
 *
 *   Ctrl/Cmd+S saves (and never the browser's save page), Ctrl/Cmd+Z and
 *   Ctrl/Cmd+Shift+Z step through the autosave history outside text fields,
 *   ↑ and ↓ move between questions outside text fields, and Escape closes
 *   the phone list. Toasts report failures only (user rule 2026-10-17).
 *
 * Relationships:
 *   - Every exam state comes from `useExamWorkspaceEditing` (document,
 *     autosave history, structure commands); address, intake, conversion,
 *     enrichment, exports and content suggestions from their composables.
 *   - Holds only presentation state: the drawer, the phone list, the
 *     selected instruction and the Import box.
 */

import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

import type { ExamWorkspaceExportTarget, NativeExamItemKind } from "../../api/examWorkspace";
import { UiGlyph } from "../../components/ui";
import ExamWorkspaceDetailsDrawer from "./exam-workspace/ExamWorkspaceDetailsDrawer.vue";
import ExamWorkspaceDrawer from "./exam-workspace/ExamWorkspaceDrawer.vue";
import ExamWorkspaceExportDrawer from "./exam-workspace/ExamWorkspaceExportDrawer.vue";
import ExamWorkspaceExportMenu from "./exam-workspace/ExamWorkspaceExportMenu.vue";
import ExamWorkspaceHeader from "./exam-workspace/ExamWorkspaceHeader.vue";
import ExamWorkspaceInstructionEditor from "./exam-workspace/ExamWorkspaceInstructionEditor.vue";
import ExamWorkspaceOpenDrawer from "./exam-workspace/ExamWorkspaceOpenDrawer.vue";
import ExamWorkspacePhoneStrip from "./exam-workspace/ExamWorkspacePhoneStrip.vue";
import ExamWorkspaceQuestionEditor from "./exam-workspace/ExamWorkspaceQuestionEditor.vue";
import ExamWorkspaceQuestionList from "./exam-workspace/ExamWorkspaceQuestionList.vue";
import ExamWorkspaceQuestionTools from "./exam-workspace/ExamWorkspaceQuestionTools.vue";
import ExamWorkspaceSaveAsDialog from "./exam-workspace/ExamWorkspaceSaveAsDialog.vue";
import ExamWorkspaceSharedInstruction from "./exam-workspace/ExamWorkspaceSharedInstruction.vue";
import "./exam-workspace/examWorkspace.css";
import { examWorkspaceSavedAt } from "./exam-workspace/examWorkspaceFormat";
import { examWorkspaceItemReadiness } from "./exam-workspace/examWorkspaceItemReadiness";
import type { ExamWorkspaceReadinessReason } from "./exam-workspace/examWorkspaceItemReadiness";
import { isTeacherReviewed } from "./exam-workspace/examWorkspaceItemEdits";
import type { TeacherItemKind } from "./exam-workspace/examWorkspaceItemEdits";
import {
  examWorkspaceBlockerEntries,
  examWorkspaceFirstPrintedMismatch,
  examWorkspaceListEntries,
  examWorkspaceListTotal,
} from "./exam-workspace/examWorkspaceListEntries";
import type { ExamWorkspaceItemEntry, ExamWorkspaceParentEntry } from "./exam-workspace/examWorkspaceListEntries";
import { bodyText } from "./exam-workspace/examWorkspaceRichText";
import { examWorkspaceDocumentLabel } from "./exam-workspace/examWorkspaceRows";
import { examWorkspaceSharedParagraphs } from "./exam-workspace/examWorkspaceSharedInstruction";
import { examWorkspaceExamPrintedDifference } from "./exam-workspace/examWorkspaceTotals";
import { updateExamListOrdering } from "../../api/examWorkspace";
import type { ExamListOrdering } from "../../api/examWorkspace";
import { useToast } from "../../composables/useToast";
import { useExamWorkspaceAddress } from "./exam-workspace/useExamWorkspaceAddress";
import { useExamWorkspaceContentSuggestions } from "./exam-workspace/useExamWorkspaceContentSuggestions";
import { useExamWorkspaceEditing } from "./exam-workspace/useExamWorkspaceEditing";
import { useExamWorkspaceEnrichment } from "./exam-workspace/useExamWorkspaceEnrichment";
import { EXPORT_FORMAT_NAMES, useExamWorkspaceExports } from "./exam-workspace/useExamWorkspaceExports";
import { useExamWorkspaceLayout } from "./exam-workspace/useExamWorkspaceLayout";
import { useExamWorkspaceSourceFile } from "./exam-workspace/useExamWorkspaceSourceFile";

type DrawerName = "open" | "export" | "details";

const DRAWER_TITLES: Record<DrawerName, string> = {
  details: "Provets uppgifter",
  export: "Exportera",
  open: "Öppna",
};
const DRAWER_OPENERS: Record<DrawerName, string> = {
  details: '[data-test="exam-workspace-title"]',
  export: '[data-test="exam-workspace-export"]',
  open: '[data-test="exam-workspace-open"]',
};

const layout = useExamWorkspaceLayout();
const toast = useToast();
const editing = useExamWorkspaceEditing();
const {
  history,
  structure,
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
  listOrdering,
  loadSavedDocuments,
  notes,
  openDocument,
  openExam,
  reloadDocument,
  renameFailure,
  renameFile,
  retryItem,
  savedDocuments,
  savedRevision,
  selectItem,
  selectedItemId,
  setCourse,
  setParentInstruction,
  setTags,
  setTitle,
  summary,
  workspaceDocument,
} = editing;

const { showDocument } = useExamWorkspaceAddress({ isDirty, openDocument, summary });
const { handleDroppedFiles, handleSelectedFile, sourceFileError } = useExamWorkspaceSourceFile(
  importDocument,
  importBlocked,
);
const exports = useExamWorkspaceExports(summary, workspaceDocument);
const enrichment = useExamWorkspaceEnrichment({
  applySuggestions: applyArrivingSuggestions,
  document: workspaceDocument,
  isOpen,
  openExam,
  savedRevision,
});
const content = useExamWorkspaceContentSuggestions({
  lineageId: () => summary.value?.lineage_id ?? null,
  setTags,
  tags: () => workspaceDocument.value?.header.tags ?? null,
});

const isPhone = computed(() => layout.value === "phone");
const drawer = ref<DrawerName | null>(null);
const listOpen = ref(false);
const importOpen = ref(false);
const saving = ref(false);
const saveAsOpen = ref(false);
const saveAsTaken = ref<string | null>(null);
/** An instruction the teacher selected; its first question stays the document's selection. */
const selectedParentId = ref<string | null>(null);

const disabled = computed(() => isBusy.value || structure.running.value);
const items = computed(() => workspaceDocument.value?.items ?? []);
const readiness = computed<Record<string, ExamWorkspaceReadinessReason[]>>(() =>
  Object.fromEntries(items.value.map((item) => [item.item_id, examWorkspaceItemReadiness(item)])),
);
const entries = computed(() =>
  workspaceDocument.value
    ? examWorkspaceListEntries(workspaceDocument.value, readiness.value, convertingItemIds.value)
    : [],
);
const itemEntries = computed(() =>
  entries.value.filter((entry): entry is ExamWorkspaceItemEntry => entry.kind === "item"),
);
const total = computed(() => examWorkspaceListTotal(entries.value));
const blockers = computed(() =>
  examWorkspaceBlockerEntries(entries.value, readiness.value, exports.exportBlockersByItemId.value),
);
const globalInstructions = computed(() =>
  examWorkspaceSharedParagraphs(workspaceDocument.value?.instructions ?? [], assetUrls.value),
);
const examPrintedTotal = computed(() =>
  workspaceDocument.value ? examWorkspaceExamPrintedDifference(workspaceDocument.value) : null,
);
/** Where "Poängen stämmer inte med provtexten" leads: the first differing part, or the exam total. */
const firstPrintedMismatch = computed(() => examWorkspaceFirstPrintedMismatch(entries.value, examPrintedTotal.value));

const selectedEntryId = computed(() => selectedParentId.value ?? selectedItemId.value);
const selectedEntry = computed(() => entries.value.find((entry) => entry.id === selectedEntryId.value) ?? null);
const selectedItem = computed(() =>
  selectedParentId.value === null ? (items.value.find((item) => item.item_id === selectedItemId.value) ?? null) : null,
);
const selectedParent = computed(
  () => workspaceDocument.value?.parents.find((parent) => parent.parent_id === selectedParentId.value) ?? null,
);
const selectedParentEntry = computed(() =>
  selectedEntry.value?.kind === "parent" ? (selectedEntry.value as ExamWorkspaceParentEntry) : null,
);
const parentChildren = computed(() =>
  itemEntries.value.filter((entry) => entry.parentId === selectedParentId.value),
);
const itemEntry = computed(() =>
  selectedEntry.value?.kind === "item" ? (selectedEntry.value as ExamWorkspaceItemEntry) : null,
);
const itemParent = computed(() => {
  const parentId = itemEntry.value?.parentId ?? null;
  const parent = workspaceDocument.value?.parents.find((entry) => entry.parent_id === parentId);
  const entry = entries.value.find((candidate) => candidate.id === parentId);
  return parent && entry ? { id: parent.parent_id, label: entry.label, text: bodyText(parent.instruction) } : null;
});
const itemChild = computed(() => {
  const item = selectedItem.value;
  const parent = workspaceDocument.value?.parents.find((entry) => entry.item_ids.includes(item?.item_id ?? ""));
  return item && parent ? { index: parent.item_ids.indexOf(item.item_id), count: parent.item_ids.length } : null;
});
/** Until TASK-SKRIPT-39-06-06 stores it, the suggested type is the type the conversion first read. */
const suggestedKind = computed<NativeExamItemKind | null>(() => {
  const item = selectedItem.value;
  const kind = item?.retry_source?.label_kind ?? null;
  return item && kind && kind !== item.kind && item.review.state === "review_required" ? kind : null;
});
const itemNotice = computed(() => {
  const item = selectedItem.value;
  const typeNotice = structure.typeNotice.value;
  if (item && typeNotice && typeNotice.itemId === item.item_id && typeNotice.kind === item.kind) {
    return typeNotice.text;
  }
  return structure.deleteNotice.value;
});
const converting = computed(() => selectedItem.value !== null && convertingItemIds.value.has(selectedItem.value.item_id));
const entryIndex = computed(() => entries.value.findIndex((entry) => entry.id === selectedEntryId.value));
const stripState = computed(() => {
  const entry = selectedEntry.value;
  if (!entry) return null;
  if (entry.kind === "parent") return "instruction" as const;
  return entry.status === "converting" ? ("converting" as const) : entry.status;
});

const saveState = computed(() => (saving.value ? "saving" : isDirty.value ? "dirty" : "saved"));
const canSave = computed(
  () => isDirty.value && !disabled.value && !!workspaceDocument.value?.title.trim(),
);
const courseLabel = computed(() => workspaceDocument.value?.header.course?.name ?? null);
const formattedSavedExports = computed(() =>
  Object.fromEntries(
    Object.entries(exports.savedExports.value).map(([target, iso]) => [target, examWorkspaceSavedAt(iso)]),
  ) as Partial<Record<ExamWorkspaceExportTarget, string>>,
);
const currentExports = computed(() =>
  (Object.keys(exports.savedExports.value) as ExamWorkspaceExportTarget[]).map((target) => EXPORT_FORMAT_NAMES[target]),
);
const zeroPoints = computed(() => items.value.some((item) => item.points === 0));
const enrichmentBusy = computed(() => enrichment.isRequesting.value || enrichment.isEnrichmentPending.value);

function questionLabel(itemId: string): string | null {
  return itemEntries.value.find((entry) => entry.id === itemId)?.label ?? null;
}

async function gotoPrintedMismatch(): Promise<void> {
  const target = firstPrintedMismatch.value;
  if (target === null) return;
  if (target !== "exam") {
    selectEntry(target);
    return;
  }
  if (isPhone.value) listOpen.value = true;
  await nextTick();
  const total = document.getElementById("exam-workspace-exam-points");
  total?.scrollIntoView?.({ block: "nearest" });
  total?.focus();
}

function toggleDrawer(name: DrawerName): void {
  drawer.value = drawer.value === name ? null : name;
}

function selectEntry(id: string): void {
  structure.dismissDeleteNotice();
  importOpen.value = false;
  if (workspaceDocument.value?.parents.some((parent) => parent.parent_id === id)) {
    selectedParentId.value = id;
  } else {
    selectedParentId.value = null;
    selectItem(id);
  }
  listOpen.value = false;
}

function step(delta: -1 | 1): void {
  const target = entries.value[entryIndex.value + delta];
  if (target) selectEntry(target.id);
}

function gotoItem(itemId: string): void {
  selectEntry(itemId);
  if (!isPhone.value && drawer.value === "export") return;
  drawer.value = null;
}

// A command that selects a question (add, delete, a new exam) leaves the instruction.
watch(selectedItemId, () => {
  selectedParentId.value = null;
  importOpen.value = false;
});

watch(
  () => summary.value?.lineage_id ?? null,
  (lineageId, previous) => {
    showDocument(lineageId);
    if (lineageId === null) {
      drawer.value = "open";
    } else if (lineageId !== previous && !(layout.value === "desktop" && drawer.value === "open")) {
      drawer.value = null;
    }
  },
);

watch(isPhone, (phone) => {
  if (!phone) listOpen.value = false;
});

async function handleSave(): Promise<void> {
  if (!canSave.value) return;
  saving.value = true;
  try {
    await editing.save();
  } finally {
    saving.value = false;
  }
}

function openSaveAs(): void {
  saveAsTaken.value = null;
  saveAsOpen.value = true;
}

async function handleSaveAs(name: string): Promise<void> {
  const outcome = await editing.saveAs(name);
  if (outcome === "saved") {
    saveAsOpen.value = false;
  } else if (outcome === "name_taken") {
    saveAsTaken.value = name;
  }
}

async function setOrdering(ordering: ExamListOrdering): Promise<void> {
  const previous = listOrdering.value;
  listOrdering.value = ordering;
  try {
    await updateExamListOrdering(ordering);
  } catch {
    listOrdering.value = previous;
    toast.failure("Ordningen kunde inte sparas. Försök igen.");
  }
}

function runExport(target: ExamWorkspaceExportTarget, destination: "download" | "files"): void {
  if (disabled.value) return;
  void (destination === "files" ? exports.saveExportToFiles(target) : exports.exportDocument(target));
}

function toggleReviewed(): void {
  const item = selectedItem.value;
  if (!item) return;
  if (isTeacherReviewed(item)) {
    editing.unmarkItemReviewed(item.item_id);
  } else {
    editing.markItemReviewed(item.item_id);
  }
}

function addEntry(kind: TeacherItemKind | "instruction"): void {
  listOpen.value = false;
  if (kind === "instruction") {
    void structure.addInstruction();
  } else {
    structure.addItem(kind);
  }
}

function addChild(kind: TeacherItemKind): void {
  if (selectedParentId.value) void structure.addChild(selectedParentId.value, kind);
}

function moveSelected(delta: -1 | 1): void {
  const item = selectedItem.value;
  const parentId = itemEntry.value?.parentId;
  if (item && parentId) void structure.moveChild(parentId, item.item_id, delta);
}

function isEditable(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLElement &&
    (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))
  );
}

function handleKeydown(event: KeyboardEvent): void {
  const modifier = event.metaKey || event.ctrlKey;
  const key = event.key.toLowerCase();
  if (modifier && key === "s") {
    // The browser's save page never opens over the workspace.
    event.preventDefault();
    void handleSave();
    return;
  }
  if (modifier && key === "z" && !isEditable(event.target)) {
    event.preventDefault();
    void (event.shiftKey ? history.redo() : history.undo());
    return;
  }
  if (event.key === "Escape" && listOpen.value) {
    listOpen.value = false;
    return;
  }
  if (
    (event.key === "ArrowDown" || event.key === "ArrowUp") &&
    !modifier &&
    !event.defaultPrevented &&
    !isEditable(event.target) &&
    !(event.target instanceof HTMLElement && event.target.closest('[role="menu"], [role="dialog"], select'))
  ) {
    event.preventDefault();
    step(event.key === "ArrowDown" ? 1 : -1);
  }
}

onMounted(() => {
  window.addEventListener("keydown", handleKeydown);
  void loadSavedDocuments();
  if (!summary.value) drawer.value = "open";
});

onBeforeUnmount(() => {
  window.removeEventListener("keydown", handleKeydown);
});
</script>

<template>
  <main
    class="xw-root ws"
    :class="{ 'ws--drawer': drawer !== null }"
    aria-label="Provredigering"
    :data-layout="layout"
    data-test="exam-workspace-frame"
  >
    <ExamWorkspaceHeader
      :title="workspaceDocument ? workspaceDocument.title || (summary ? examWorkspaceDocumentLabel(summary.name) : '') : null"
      :save-state="saveState"
      :saved-at="summary ? examWorkspaceSavedAt(summary.saved_at) : null"
      :course-label="courseLabel"
      :total="total"
      :details-open="drawer === 'details'"
      :open-drawer-open="drawer === 'open'"
      :can-undo="history.canUndo.value && !disabled"
      :can-redo="history.canRedo.value && !disabled"
      :can-save="canSave"
      :can-save-as="workspaceDocument !== null && !disabled"
      :suggest-busy="enrichmentBusy"
      :suggest-disabled="workspaceDocument === null || disabled"
      :is-phone="isPhone"
      @toggle-details="toggleDrawer('details')"
      @toggle-open="toggleDrawer('open')"
      @save="handleSave"
      @save-as="openSaveAs"
      @reload="reloadDocument"
      @suggest-all="enrichment.requestSuggestionsForAll"
      @undo="history.undo"
      @redo="history.redo"
    >
      <template #export>
        <ExamWorkspaceExportMenu
          :blockers="blockers"
          :disabled="workspaceDocument === null"
          :dirty="isDirty"
          :exporting-target="exports.exportingTarget.value"
          :saved-exports="formattedSavedExports"
          :result="exports.exportResult.value"
          :checklist-count="exports.exportChecklist.value.length"
          :zero-points="zeroPoints"
          :is-phone="isPhone"
          @download="(target) => runExport(target, 'download')"
          @save-to-files="(target) => runExport(target, 'files')"
          @more="drawer = 'export'"
          @goto="gotoItem"
        />
      </template>
    </ExamWorkspaceHeader>

    <button
      v-if="firstPrintedMismatch !== null"
      type="button"
      class="ws__points"
      data-test="exam-workspace-points-warning"
      @click="gotoPrintedMismatch"
    >
      <UiGlyph
        meaning="status-warning"
        :size="16"
      />Poängen stämmer inte med provtexten
    </button>
    <p
      v-if="conflictNotice"
      class="xw-notice xw-notice--error ws__bar"
      role="status"
      data-test="exam-workspace-conflict-notice"
    >
      {{ conflictNotice }}
    </p>
    <div
      v-if="enrichment.enrichmentMessage.value || enrichment.enrichmentLookupError.value"
      class="xw-notice xw-notice--info ws__bar"
      role="status"
      data-test="exam-workspace-enrichment"
    >
      <span
        v-if="enrichment.enrichmentLookupError.value"
        class="xw-grow"
        data-test="exam-workspace-enrichment-lookup-error"
      >{{ enrichment.enrichmentLookupError.value }}</span>
      <span
        v-else
        class="xw-grow"
        data-test="exam-workspace-enrichment-message"
      >{{ enrichment.enrichmentMessage.value }}</span>
      <button
        v-if="enrichment.enrichmentLookupError.value"
        type="button"
        class="xw-btn xw-btn--compact"
        data-test="exam-workspace-enrichment-lookup-retry"
        @click="enrichment.retryEnrichmentLookup"
      >
        Försök igen
      </button>
    </div>

    <ExamWorkspacePhoneStrip
      v-if="isPhone && workspaceDocument"
      :label="selectedEntry?.label ?? null"
      :state="stripState"
      :can-previous="entryIndex > 0"
      :can-next="entryIndex >= 0 && entryIndex < entries.length - 1"
      :list-open="listOpen"
      @previous="step(-1)"
      @next="step(1)"
      @open-list="listOpen = true"
    >
      <ExamWorkspaceQuestionTools
        v-if="selectedItem"
        :has-import="selectedItem.import_record !== null"
        :import-open="importOpen"
        :reviewed="isTeacherReviewed(selectedItem)"
        :disabled="disabled || converting"
        @toggle-import="importOpen = !importOpen"
        @toggle-reviewed="toggleReviewed"
      />
    </ExamWorkspacePhoneStrip>

    <div
      class="ws__body"
      :class="{ 'ws__body--empty': !workspaceDocument }"
    >
      <ExamWorkspaceQuestionList
        v-if="workspaceDocument"
        :entries="entries"
        :selected-id="selectedEntryId"
        :question-count="itemEntries.length"
        :total="total"
        :printed-total="examPrintedTotal"
        :can-add="!disabled"
        :overlay="isPhone && listOpen"
        @select="selectEntry"
        @add="addEntry"
        @close="listOpen = false"
      >
        <template #intro>
          <ExamWorkspaceSharedInstruction
            v-if="globalInstructions.length > 0"
            :paragraphs="globalInstructions"
            class="ws__shared"
            data-test="exam-workspace-global-instruction"
          />
        </template>
      </ExamWorkspaceQuestionList>

      <div
        class="ws__editor"
        data-test="exam-workspace-workspace"
      >
        <div
          v-if="!workspaceDocument"
          class="ws__empty"
          data-test="exam-workspace-empty"
        >
          <h2>Inget prov öppet</h2>
          <p>Importera ett prov från Word eller DigiExam, eller öppna ett sparat prov.</p>
          <button
            v-if="drawer !== 'open'"
            type="button"
            class="xw-btn"
            data-test="exam-workspace-empty-open"
            @click="drawer = 'open'"
          >
            Öppna
          </button>
        </div>
        <div
          v-else
          class="ws__in"
        >
          <ExamWorkspaceInstructionEditor
            v-if="selectedParent && selectedParentEntry"
            :parent="selectedParent"
            :label="selectedParentEntry.label"
            :children="parentChildren"
            :subtotal="selectedParentEntry.points"
            :printed-total="selectedParentEntry.printedTotal"
            :disabled="disabled"
            :delete-ready="structure.parentDeleteReady"
            @update-instruction="(body) => setParentInstruction(selectedParent!.parent_id, body)"
            @goto-child="selectEntry"
            @move-child="(itemId, delta) => structure.moveChild(selectedParent!.parent_id, itemId, delta)"
            @delete-child="structure.deleteItem"
            @add-child="addChild"
            @delete-parent="(mode) => structure.deleteParent(selectedParent!.parent_id, mode)"
          />
          <ExamWorkspaceQuestionEditor
            v-else-if="selectedItem && itemEntry"
            :item="selectedItem"
            :label="itemEntry.label"
            :origin="workspaceDocument.origin.kind"
            :parent="itemParent"
            :child="itemChild"
            :suggested-kind="suggestedKind"
            :converting="converting"
            :disabled="disabled"
            :notice="itemNotice"
            :import-open="importOpen"
            :last-child-deletable="structure.parentDeleteReady"
            :asset-urls="assetUrls"
            @change-type="(kind) => structure.changeType(selectedItem!.item_id, kind)"
            @move="moveSelected"
            @remove="structure.deleteItem(selectedItem!.item_id)"
            @toggle-import="importOpen = !importOpen"
            @toggle-reviewed="toggleReviewed"
            @retry="(kind) => retryItem(selectedItem!.item_id, kind)"
            @goto-parent="selectEntry"
            @dismiss-notice="itemNotice === structure.deleteNotice.value ? structure.dismissDeleteNotice() : structure.dismissTypeNotice()"
            @undo-interpretation="editing.undoItemInterpretation"
            @remove-automatic-value="editing.removeItemAutomaticValue"
            @show-gap-as-text="editing.showItemGapAsText"
            @update-choice-body="editing.updateItemChoiceBody"
            @update-correct-choices="editing.updateItemCorrectChoices"
            @update-criteria="editing.updateItemCriteria"
            @update-gap-values="editing.updateItemGapValues"
            @update-match-entry-body="editing.updateItemMatchEntryBody"
            @update-match-pairs="editing.updateItemMatchPairs"
            @update-paragraph-segments="editing.updateItemParagraphSegments"
            @update-paragraph-heading="editing.updateItemParagraphHeading"
            @update-points="editing.updateItemPoints"
            @update-tick-points="editing.updateItemTickPoints"
          />
          <p
            v-else
            class="xw-muted"
          >
            Välj en fråga i listan.
          </p>
        </div>
      </div>

      <ExamWorkspaceDrawer
        v-if="drawer"
        :key="drawer"
        :title="DRAWER_TITLES[drawer]"
        :layout="layout"
        :opener-selector="DRAWER_OPENERS[drawer]"
        :test-id="`exam-workspace-drawer-${drawer}`"
        @close="drawer = null"
      >
        <ExamWorkspaceOpenDrawer
          v-if="drawer === 'open'"
          :documents="savedDocuments"
          :current-lineage-id="summary?.lineage_id ?? null"
          :ordering="listOrdering"
          :import-blocked="importBlocked"
          :is-busy="isBusy"
          :is-dirty="isDirty"
          :source-file-error="sourceFileError"
          :conversion-message="conversionMessage"
          :conversion-error="conversionError"
          :conversion-progress="conversionProgress"
          :is-converting="isConverting"
          :notes="notes"
          :current-exports="currentExports"
          @select-file="handleSelectedFile"
          @drop-files="handleDroppedFiles"
          @open="openDocument"
          @set-ordering="setOrdering"
          @retry-conversion="retryConversionStatus"
        />
        <ExamWorkspaceExportDrawer
          v-else-if="drawer === 'export' && workspaceDocument"
          :blockers="blockers"
          :dirty="isDirty"
          :busy="disabled"
          :exporting-target="exports.exportingTarget.value"
          :saved-exports="formattedSavedExports"
          :checklist="exports.exportChecklist.value"
          :notice="exports.exportNotice.value"
          :result="exports.exportResult.value"
          :zero-points="zeroPoints"
          @run="runExport"
          @goto="gotoItem"
        />
        <ExamWorkspaceDetailsDrawer
          v-else-if="drawer === 'details' && workspaceDocument && summary"
          :document="workspaceDocument"
          :summary="summary"
          :rename-file="renameFile"
          :rename-failure="renameFailure"
          :disabled="disabled"
          :dirty="isDirty"
          :content-busy="content.busy.value"
          :content-message="content.message.value"
          :question-label="questionLabel"
          @update:title="setTitle"
          @update:course="setCourse"
          @set-tags="setTags"
          @suggest-content="content.suggest"
        />
      </ExamWorkspaceDrawer>
    </div>

    <ExamWorkspaceSaveAsDialog
      v-if="saveAsOpen && summary"
      :current-name="examWorkspaceDocumentLabel(summary.name)"
      :busy="isBusy"
      :taken-name="saveAsTaken"
      @save="handleSaveAs"
      @close="saveAsOpen = false"
    />
  </main>
</template>

<style scoped>
.ws {
  display: flex; flex-direction: column; flex: 1; min-height: 0; min-width: 0;
  background: var(--huleedu-canvas); color: var(--huleedu-navy);
}
.ws__bar { margin: var(--huleedu-space-2) var(--huleedu-space-6) 0; }
.ws__points {
  all: unset; box-sizing: border-box; display: flex; align-items: flex-start; gap: var(--huleedu-space-1-5); align-self: flex-start;
  min-height: var(--xw-ctl-fine); margin: var(--huleedu-space-1) var(--huleedu-space-6) 0; padding: var(--huleedu-space-1-5) 0; cursor: pointer;
  font-size: var(--huleedu-text-sm); color: var(--huleedu-warning); overflow-wrap: anywhere;
}
.ws__points svg { flex: none; margin-top: 2px; }
.ws__points:focus-visible { outline: 2px solid var(--huleedu-action-40); }
@media (hover: hover) { .ws__points:hover { text-decoration: underline; } }
@media (pointer: coarse) { .ws__points { min-height: var(--xw-ctl); } }
.ws__body {
  position: relative; flex: 1; min-height: 0; display: grid;
  grid-template-columns: var(--xw-list) minmax(0, 1fr);
}
.ws--drawer .ws__body { grid-template-columns: var(--xw-list) minmax(0, 1fr) var(--xw-drawer); }
.ws__body--empty, .ws--drawer .ws__body--empty { grid-template-columns: minmax(0, 1fr); }
.ws--drawer .ws__body--empty { grid-template-columns: minmax(0, 1fr) var(--xw-drawer); }
.ws__editor { min-width: 0; min-height: 0; overflow-y: auto; }
.ws__in { max-width: 860px; margin: 0 auto; padding: var(--huleedu-space-6) var(--huleedu-space-8) var(--huleedu-space-12); }
.ws__shared { padding: var(--huleedu-space-2) var(--huleedu-space-6); border-bottom: 1px solid var(--huleedu-surface-divider); }
.ws__empty {
  height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: var(--huleedu-space-2);
  padding: var(--huleedu-space-8); text-align: center; color: var(--huleedu-navy-70);
}
.ws__empty h2 { margin: 0; font-size: var(--huleedu-text-xl); color: var(--huleedu-navy); }
.ws__empty p { max-width: 360px; margin: 0 0 var(--huleedu-space-4); font-size: var(--huleedu-text-sm); }
@media (max-width: 1279px) {
  .ws__body, .ws--drawer .ws__body { grid-template-columns: 280px minmax(0, 1fr); }
  .ws__body--empty, .ws--drawer .ws__body--empty { grid-template-columns: minmax(0, 1fr); }
  .ws__in { padding: var(--huleedu-space-4) var(--huleedu-space-5) var(--huleedu-space-12); }
  .ws__bar { margin: var(--huleedu-space-2) var(--huleedu-space-4) 0; }
  .ws__points { margin: var(--huleedu-space-1) var(--huleedu-space-4) 0; }
  .ws__shared { padding: var(--huleedu-space-2) var(--huleedu-space-4); }
}
@media (max-width: 767px) {
  .ws__body, .ws--drawer .ws__body { grid-template-columns: minmax(0, 1fr); }
  .ws__in { padding: var(--huleedu-space-3) var(--huleedu-space-4) var(--huleedu-space-12); }
}
</style>
