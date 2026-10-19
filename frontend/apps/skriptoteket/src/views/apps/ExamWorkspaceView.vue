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
 *   - Selection and navigation, the save flow and the keyboard shortcuts
 *     come from their own composables; the editor column and the open
 *     drawer are `ExamWorkspaceEditorPane` and `ExamWorkspaceDrawers`.
 *   - Composes them and holds only presentation state: the drawer, the
 *     phone list and the Import box.
 */

import { computed, onMounted, provide, ref } from "vue";

import type { ExamListOrdering } from "../../api/examWorkspace";
import type { ExamWorkspaceExportTarget } from "../../api/examWorkspaceExports";
import { useToast } from "../../composables/useToast";
import ExamWorkspaceDrawers from "./exam-workspace/ExamWorkspaceDrawers.vue";
import ExamWorkspaceEditorPane from "./exam-workspace/ExamWorkspaceEditorPane.vue";
import ExamWorkspaceExportMenu from "./exam-workspace/ExamWorkspaceExportMenu.vue";
import ExamWorkspaceHeader from "./exam-workspace/ExamWorkspaceHeader.vue";
import ExamWorkspacePhoneStrip from "./exam-workspace/ExamWorkspacePhoneStrip.vue";
import ExamWorkspacePrintPreviewPanel from "./exam-workspace/ExamWorkspacePrintPreviewPanel.vue";
import ExamWorkspaceQuestionList from "./exam-workspace/ExamWorkspaceQuestionList.vue";
import ExamWorkspaceQuestionTools from "./exam-workspace/ExamWorkspaceQuestionTools.vue";
import ExamWorkspaceSaveAsDialog from "./exam-workspace/ExamWorkspaceSaveAsDialog.vue";
import ExamWorkspaceSignInBar from "./exam-workspace/ExamWorkspaceSignInBar.vue";
import "./exam-workspace/examWorkspace.css";
import { examWorkspaceBlockerEntries, examWorkspaceTitleBlockerEntries } from "./exam-workspace/examWorkspaceBlockers";
import { examWorkspaceSavedAt } from "./exam-workspace/examWorkspaceFormat";
import { provideExamWorkspaceHistoryKeys } from "./exam-workspace/examWorkspaceHistoryKeys";
import { isTeacherReviewed } from "./exam-workspace/examWorkspaceItemEdits";
import type { TeacherItemKind } from "./exam-workspace/examWorkspaceItemEdits";
import { examWorkspaceDocumentLabel } from "./exam-workspace/examWorkspaceRows";
import { bodyText } from "./exam-workspace/examWorkspaceRichText";
import { isEmptyBody } from "./exam-workspace/examWorkspaceRichTextDocument";
import { examWorkspaceExamPrintedDifference } from "./exam-workspace/examWorkspaceTotals";
import { EXAM_WORKSPACE_STORE_KEY } from "./exam-workspace/examWorkspaceStore";
import type { ExamWorkspaceStore } from "./exam-workspace/examWorkspaceStore";
import { useExamWorkspaceAddress } from "./exam-workspace/useExamWorkspaceAddress";
import { useExamWorkspaceColumnSizes } from "./exam-workspace/useExamWorkspaceColumnSizes";
import { useExamWorkspaceContentSuggestions } from "./exam-workspace/useExamWorkspaceContentSuggestions";
import { useExamWorkspaceEditing } from "./exam-workspace/useExamWorkspaceEditing";
import { useExamWorkspaceEnrichment } from "./exam-workspace/useExamWorkspaceEnrichment";
import { useExamWorkspaceExports } from "./exam-workspace/useExamWorkspaceExports";
import { useExamWorkspaceGuestSignIn } from "./exam-workspace/useExamWorkspaceGuestSignIn";
import { useExamWorkspaceKeyboard } from "./exam-workspace/useExamWorkspaceKeyboard";
import { useExamWorkspaceLayout } from "./exam-workspace/useExamWorkspaceLayout";
import { useExamWorkspaceSaveFlow } from "./exam-workspace/useExamWorkspaceSaveFlow";
import { useExamWorkspaceSelection } from "./exam-workspace/useExamWorkspaceSelection";
import { useExamWorkspaceSideColumns } from "./exam-workspace/useExamWorkspaceSideColumns";
import { useExamWorkspaceSourceFile } from "./exam-workspace/useExamWorkspaceSourceFile";

const props = defineProps<{ store: ExamWorkspaceStore }>();

provide(EXAM_WORKSPACE_STORE_KEY, props.store);

const layout = useExamWorkspaceLayout();
const toast = useToast();
const editing = useExamWorkspaceEditing(props.store);
const {
  history,
  structure,
  applyArrivingSuggestions,
  conflictNotice,
  historyCursor,
  isBusy,
  isDirty,
  isOpen,
  listOrdering,
  loadSavedDocuments,
  openDocument,
  openExam,
  importDocument,
  importBlocked,
  savedRevision,
  setTags,
  summary,
  titleWithoutText,
  workspaceDocument,
} = editing;

const { depart, dismissSignInPrompt, signInPrompt } = useExamWorkspaceGuestSignIn({
  history,
  store: props.store,
  workspaceDocument,
});

defineExpose({ depart });

const frame = ref<HTMLElement | null>(null);
const { showDocument } = useExamWorkspaceAddress({ isDirty, openDocument, summary });
const {
  drawer,
  importOpen,
  isPhone,
  listOpen,
  previewBlocked,
  previewLoading,
  previewMessage,
  previewOpen,
  previewPages,
  previewQuestionPages,
  toggleDrawer,
  togglePreview,
} = useExamWorkspaceSideColumns({
  historyCursor,
  historyPosition: history.position,
  layout,
  lineageId: computed(() => summary.value?.lineage_id ?? null),
  savedRevision,
  selectedItemId: editing.selectedItemId,
  store: props.store,
  onLineage: (lineageId) => {
    showDocument(lineageId);
    dismissSignInPrompt();
  },
});

const sourceFile = useExamWorkspaceSourceFile(importDocument, importBlocked);
// Spara before an export is the save flow's, which is built after the exports it feeds.
const exports = useExamWorkspaceExports(summary, workspaceDocument, {
  noteBlockers: editing.noteExportBlockers,
  readLatest: editing.reloadDocument,
  saveFirst: () => saveFlow.saveBeforeExport(),
  store: props.store,
});
const enrichment = useExamWorkspaceEnrichment({
  applySuggestions: applyArrivingSuggestions,
  document: workspaceDocument,
  isOpen,
  openExam,
  savedRevision,
  teacher: props.store.teacher,
});
const content = useExamWorkspaceContentSuggestions({
  document: () => workspaceDocument.value,
  isOpen,
  openExam: () => openExam.value,
  savedRevision: () => savedRevision.value,
  setTags,
  teacher: props.store.teacher,
});

const selection = useExamWorkspaceSelection({
  editing,
  importOpen,
  listOpen,
  afterGoto: () => {
    if (!isPhone.value && drawer.value === "export") return;
    drawer.value = null;
  },
});
const {
  canStep, converting, dismissItemNotice, entries, examInstructionsSelected, gotoItem, itemChild, itemEntries,
  itemEntry, itemNotice, itemParent, items, moveSelected, parentChildren, questionLabel, readiness, selectedEntry,
  selectedEntryId, selectedItem, selectedParent, selectedParentEntry, selectedParentId, selectEntry, step, stripState,
  total,
} = selection;
editing.registerSelectParent(selectEntry);

const disabled = computed(() => isBusy.value || structure.running.value);
const blockers = computed(() => [
  ...examWorkspaceTitleBlockerEntries(titleWithoutText.value),
  ...examWorkspaceBlockerEntries(entries.value, items.value, readiness.value, exports.exportBlockersByItemId.value),
]);

/**
 * The width owner's side state (TASK-SKRIPT-41-02-04): the open drawer wins,
 * else the rendered print preview, else no side column. The `.ws__body` grid
 * keys one rule per state off `data-side`.
 */
const side = computed(() => {
  if (drawer.value !== null) return drawer.value;
  if (previewOpen.value && workspaceDocument.value && !isPhone.value && props.store.teacher !== null) {
    return "preview";
  }
  return "none";
});

/**
 * The remembered column widths and list-collapsed state (TASK-SKRIPT-41-02-04):
 * on desktop the root carries them as inline custom properties and the list
 * state as `data-list`; tablet and phone render without either. A first width
 * set on the collapsed list's draggable edge widens and expands it.
 */
const columnSizes = useExamWorkspaceColumnSizes();
const isDesktop = computed(() => layout.value === "desktop");
const rootColumnStyle = computed<Record<string, string> | undefined>(() =>
  isDesktop.value ? columnSizes.rootStyle.value : undefined,
);
const rootListState = computed<"collapsed" | "open" | undefined>(() => {
  if (!isDesktop.value) return undefined;
  return columnSizes.listCollapsed.value ? "collapsed" : "open";
});
const listRailCollapsed = computed(() => isDesktop.value && columnSizes.listCollapsed.value);

function setListWidth(px: number): void {
  columnSizes.setWidth("list", px);
  if (columnSizes.listCollapsed.value) {
    columnSizes.toggleListCollapsed();
  }
}
const saveFlow = useExamWorkspaceSaveFlow({
  editing, enrichment, exports, blockers, disabled, frame, gotoItem,
  openDetails: () => { drawer.value = "details"; },
});
const { canSave, fixBlocker, gotoBlocker, handleSave, handleSaveAs, openSaveAs, runExport, saveAsOpen, saveAsTaken, saveState } =
  saveFlow;
useExamWorkspaceKeyboard({ save: handleSave, undo: history.undo, redo: history.redo, step, listOpen });
// Ctrl/Cmd+Z inside an exam text editor is the same Ångra / Gör om the buttons run.
provideExamWorkspaceHistoryKeys({
  undo: () => void history.undo(),
  redo: () => void history.redo(),
});

/**
 * The list's "Instruktioner" preview: the text, or "Bild" for an instruction
 * of pictures without visible text; `null` for an instruction that prints nothing.
 */
const examInstructionsPreview = computed(() => {
  const instructions = workspaceDocument.value?.instructions ?? [];
  return isEmptyBody(instructions) ? null : bodyText(instructions) || "Bild";
});
const examPrintedTotal = computed(() =>
  workspaceDocument.value ? examWorkspaceExamPrintedDifference(workspaceDocument.value) : null,
);
const courseLabel = computed(() => workspaceDocument.value?.header.course?.name ?? null);
const formattedSavedExports = computed(() =>
  Object.fromEntries(
    Object.entries(exports.savedExports.value).map(([target, iso]) => [target, examWorkspaceSavedAt(iso)]),
  ) as Partial<Record<ExamWorkspaceExportTarget, string>>,
);
const zeroPoints = computed(() => items.value.some((item) => item.points === 0));
const enrichmentBusy = computed(() => enrichment.isRequesting.value || enrichment.isEnrichmentPending.value);

async function setOrdering(ordering: ExamListOrdering): Promise<void> {
  const teacher = props.store.teacher;
  if (!teacher) return;
  const previous = listOrdering.value;
  listOrdering.value = ordering;
  try {
    await teacher.updateExamListOrdering(ordering);
  } catch {
    listOrdering.value = previous;
    toast.failure("Ordningen kunde inte sparas. Försök igen.");
  }
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

function addEntry(kind: TeacherItemKind | "instruction" | "part"): void {
  listOpen.value = false;
  if (kind === "instruction") {
    void structure.addInstruction();
  } else if (kind === "part") {
    void structure.addEmptyPart();
  } else {
    structure.addItem(kind);
  }
}

function addChild(kind: TeacherItemKind): void {
  if (selectedParentId.value) void structure.addChild(selectedParentId.value, kind);
}

onMounted(() => {
  void loadSavedDocuments();
  if (!summary.value) drawer.value = "open";
});
</script>

<template>
  <main
    ref="frame"
    class="xw-root ws"
    :data-side="side"
    :data-list="rootListState"
    :style="rootColumnStyle"
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
      :preview-open="previewOpen"
      @toggle-details="toggleDrawer('details')"
      @toggle-open="toggleDrawer('open')"
      @save="handleSave"
      @save-as="openSaveAs"
      @suggest-all="enrichment.requestSuggestionsForAll"
      @undo="history.undo"
      @redo="history.redo"
      @toggle-preview="togglePreview"
    >
      <template #export>
        <ExamWorkspaceExportMenu
          :blockers="blockers"
          :disabled="workspaceDocument === null"
          :fix-disabled="disabled"
          :suggest-busy="enrichmentBusy"
          :exporting-target="exports.exportingTarget.value"
          :saved-exports="formattedSavedExports"
          :result="exports.exportResult.value"
          :checklist-count="exports.exportChecklist.value.length"
          :zero-points="zeroPoints"
          :is-phone="isPhone"
          @download="(target) => runExport(target, 'download')"
          @save-to-files="(target) => runExport(target, 'files')"
          @more="drawer = 'export'"
          @goto="gotoBlocker"
          @fix="fixBlocker"
          @suggest-all="enrichment.requestSuggestionsForAll"
        />
      </template>
    </ExamWorkspaceHeader>

    <p
      v-if="conflictNotice"
      class="xw-notice xw-notice--error ws__bar"
      role="status"
      data-test="exam-workspace-conflict-notice"
    >
      {{ conflictNotice }}
    </p>
    <ExamWorkspaceSignInBar
      v-if="signInPrompt"
      :message="signInPrompt"
      :depart="depart"
      @dismiss="dismissSignInPrompt"
    />
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
      :heading="examInstructionsSelected ? 'Instruktioner' : null"
      :state="stripState"
      :can-previous="canStep(-1)"
      :can-next="canStep(1)"
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
        id="exam-workspace-question-list"
        :entries="entries"
        :selected-id="selectedEntryId"
        :exam-instructions-preview="examInstructionsPreview"
        :question-count="itemEntries.length"
        :total="total"
        :printed-total="examPrintedTotal"
        :can-add="!disabled"
        :disabled="disabled"
        :overlay="isPhone && listOpen"
        :collapsed="listRailCollapsed"
        :handle="isDesktop"
        @select="selectEntry"
        @add="addEntry"
        @group="(itemIds) => structure.groupItems(itemIds)"
        @accept-exam-total="editing.acceptExamPrintedTotal"
        @accept-part-total="editing.acceptPartPrintedTotal"
        @accept-all-totals="editing.acceptAllPrintedTotals"
        @close="listOpen = false"
        @set="setListWidth"
        @reset="columnSizes.resetWidth('list')"
        @toggle-collapse="columnSizes.toggleListCollapsed()"
      />

      <ExamWorkspaceEditorPane
        :editing="editing"
        :workspace-document="workspaceDocument"
        :exam-instructions-selected="examInstructionsSelected"
        :selected-parent="selectedParent"
        :selected-parent-entry="selectedParentEntry"
        :parent-children="parentChildren"
        :entries="entries"
        :selected-item="selectedItem"
        :item-entry="itemEntry"
        :item-parent="itemParent"
        :item-child="itemChild"
        :item-notice="itemNotice"
        :converting="converting"
        :disabled="disabled"
        :import-open="importOpen"
        :open-drawer-shown="drawer === 'open'"
        @open-drawer="drawer = 'open'"
        @select="selectEntry"
        @add-child="addChild"
        @move-selected="moveSelected"
        @toggle-import="importOpen = !importOpen"
        @toggle-reviewed="toggleReviewed"
        @dismiss-item-notice="dismissItemNotice"
      />

      <ExamWorkspacePrintPreviewPanel
        v-if="previewOpen && workspaceDocument && !isPhone && props.store.teacher !== null"
        id="exam-workspace-side-panel"
        :pages="previewPages"
        :question-pages="previewQuestionPages"
        :loading="previewLoading"
        :blocked="previewBlocked"
        :message="previewMessage"
        :selected-item-id="selectedItem?.item_id ?? null"
        :handle="isDesktop"
        @close="previewOpen = false"
        @set="(px) => columnSizes.setWidth('preview', px)"
        @reset="columnSizes.resetWidth('preview')"
        @toggle-collapse="previewOpen = false"
      />

      <ExamWorkspaceDrawers
        v-if="drawer"
        id="exam-workspace-side-panel"
        :drawer="drawer"
        :layout="layout"
        :editing="editing"
        :exports="exports"
        :enrichment="enrichment"
        :content="content"
        :source-file="sourceFile"
        :blockers="blockers"
        :disabled="disabled"
        :enrichment-busy="enrichmentBusy"
        :zero-points="zeroPoints"
        :formatted-saved-exports="formattedSavedExports"
        :question-label="questionLabel"
        :handle="isDesktop"
        @close="drawer = null"
        @run="runExport"
        @goto="gotoBlocker"
        @fix="fixBlocker"
        @set-ordering="setOrdering"
        @set="(px) => columnSizes.setWidth('drawer', px)"
        @reset="columnSizes.resetWidth('drawer')"
        @toggle-collapse="drawer = null"
      />
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
.ws__body {
  position: relative; flex: 1; min-height: 0; display: grid;
  grid-template-columns: min(var(--xw-list-size), max(0px, 100% - var(--xw-editor-min))) minmax(0, 1fr);
}
.ws__body--empty { grid-template-columns: minmax(0, 1fr); }
/* The side track squeezes first, then the list, the editor last (TASK-SKRIPT-41-02-04). */
.ws[data-side="open"],
.ws[data-side="export"],
.ws[data-side="details"] { --xw-side-size: var(--xw-drawer-size); }
.ws[data-side="preview"] { --xw-side-size: var(--xw-preview-size); }
/* The collapsed list is a fixed 44px rail; the rail counts as the list's width. */
.ws[data-list="collapsed"] .ws__body:not(.ws__body--empty) {
  grid-template-columns: 44px minmax(0, 1fr);
}
@media (min-width: 1280px) {
  .ws[data-side="open"] .ws__body,
  .ws[data-side="export"] .ws__body,
  .ws[data-side="details"] .ws__body,
  .ws[data-side="preview"] .ws__body {
    grid-template-columns:
      min(var(--xw-list-size), max(0px, 100% - var(--xw-editor-min)))
      minmax(0, 1fr)
      min(var(--xw-side-size), max(0px, 100% - var(--xw-list-size) - var(--xw-editor-min)));
  }
  .ws[data-list="collapsed"][data-side="open"] .ws__body:not(.ws__body--empty),
  .ws[data-list="collapsed"][data-side="export"] .ws__body:not(.ws__body--empty),
  .ws[data-list="collapsed"][data-side="details"] .ws__body:not(.ws__body--empty),
  .ws[data-list="collapsed"][data-side="preview"] .ws__body:not(.ws__body--empty) {
    grid-template-columns:
      44px
      minmax(0, 1fr)
      min(var(--xw-side-size), max(0px, 100% - 44px - var(--xw-editor-min)));
  }
  .ws[data-side="open"] .ws__body--empty,
  .ws[data-side="export"] .ws__body--empty,
  .ws[data-side="details"] .ws__body--empty {
    grid-template-columns: minmax(0, 1fr) min(var(--xw-side-size), 100%);
  }
}
@media (max-width: 1279px) {
  .ws__body { grid-template-columns: 280px minmax(0, 1fr); }
  .ws__body--empty { grid-template-columns: minmax(0, 1fr); }
  .ws__bar { margin: var(--huleedu-space-2) var(--huleedu-space-4) 0; }
}
@media (max-width: 767px) {
  .ws__body { grid-template-columns: minmax(0, 1fr); }
}
</style>
