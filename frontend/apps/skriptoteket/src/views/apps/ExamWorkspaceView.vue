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
 *   header's title sits in the shell's top bar.
 *
 *   Ctrl/Cmd+S stores a pending edit at once (and never the browser's save
 *   page), Ctrl/Cmd+Z and Ctrl/Cmd+Shift+Z step through the autosave history
 *   outside text fields, ↑ and ↓ move between questions outside text fields,
 *   and Escape closes the phone list. Toasts report failures only (user rule
 *   2026-10-17).
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

import { useToast } from "../../composables/useToast";
import ExamWorkspaceDrawers from "./exam-workspace/ExamWorkspaceDrawers.vue";
import ExamWorkspaceEditLeaseNotice from "./exam-workspace/ExamWorkspaceEditLeaseNotice.vue";
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
import { provideExamWorkspaceHistoryKeys } from "./exam-workspace/examWorkspaceHistoryKeys";
import { isTeacherReviewed } from "./exam-workspace/examWorkspaceItemEdits";
import { examWorkspaceDocumentLabel } from "./exam-workspace/examWorkspaceRows";
import { examWorkspacePrintedTotalMismatches } from "./exam-workspace/examWorkspaceTotals";
import { EXAM_WORKSPACE_STORE_KEY } from "./exam-workspace/examWorkspaceStore";
import type { ExamWorkspaceStore } from "./exam-workspace/examWorkspaceStore";
import { useExamWorkspaceAddress } from "./exam-workspace/useExamWorkspaceAddress";
import { useExamWorkspaceColumnLayout } from "./exam-workspace/useExamWorkspaceColumnLayout";
import { useExamWorkspaceContentSuggestions } from "./exam-workspace/useExamWorkspaceContentSuggestions";
import { useExamWorkspaceDrawerState } from "./exam-workspace/useExamWorkspaceDrawerState";
import { useExamWorkspaceListActions } from "./exam-workspace/useExamWorkspaceListActions";
import { useExamWorkspaceViewLabels } from "./exam-workspace/useExamWorkspaceViewLabels";
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
const editing = useExamWorkspaceEditing(props.store);
const {
  history,
  structure,
  applyArrivingSuggestions,
  historyCursor,
  isBusy,
  isDirty,
  isOpen,
  loadSavedDocuments,
  openDocument,
  openExam,
  importDocument,
  importBlocked,
  leaseReadOnly,
  editingLocked,
  requestTakeover,
  savedRevision,
  setTags,
  summary,
  takeoverWaiting,
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
const { closeAfterGoto, consumeImportPick, drawer, importPickPending, requestImportPick, toggleDrawer } =
  useExamWorkspaceDrawerState({ isExamOpen: () => Boolean(summary.value), layout });
const {
  importOpen,
  isPhone,
  listOpen,
  previewBlocked,
  previewLoading,
  previewMessage,
  previewOpen,
  previewPages,
  previewQuestionPages,
  togglePreview,
} = useExamWorkspaceSideColumns({
  drawer,
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
  historyPosition: editing.history.position,
  noteBlockers: editing.noteExportBlockers,
  readLatest: editing.reloadDocument,
  saveFirst: () => saveFlow.saveBeforeExport(),
  savedVersion: () => editing.savedRevision.value,
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
  afterGoto: closeAfterGoto,
});
const {
  canStep, converting, dismissItemNotice, entries, examInstructionsSelected, gotoItem, itemChild, itemEntries,
  itemEntry, itemNotice, itemParent, items, moveSelected, parentChildren, questionLabel, readiness, selectedEntry,
  selectedEntryId, selectedItem, selectedParent, selectedParentEntry, selectEntry, step, stripState,
  total,
} = selection;
editing.registerSelectParent(selectEntry);

const disabled = computed(() => isBusy.value || structure.running.value || editingLocked.value);
const blockers = computed(() => [
  ...examWorkspaceTitleBlockerEntries(titleWithoutText.value),
  ...examWorkspaceBlockerEntries(entries.value, items.value, readiness.value, exports.exportBlockersByItemId.value),
]);

/**
 * The width owner's side state and the remembered column widths (TASK-SKRIPT-41-02-04),
 * owned by `useExamWorkspaceColumnLayout`: on desktop the root carries the widths
 * as inline custom properties and the list state as `data-list`; tablet and
 * phone render without either.
 */
const {
  isDesktop,
  listRailCollapsed,
  resetWidth,
  rootColumnStyle,
  rootListState,
  setListWidth,
  setWidth,
  side,
  toggleListCollapsed,
} = useExamWorkspaceColumnLayout(layout, {
  drawer,
  isPhone,
  previewOpen,
  store: props.store,
  workspaceDocument,
});
const saveFlow = useExamWorkspaceSaveFlow({
  editing, enrichment, exports, blockers, disabled, frame, gotoItem,
  isGuest: props.store.guest !== null,
  openDetails: () => { drawer.value = "details"; },
});
const { fixBlocker, gotoBlocker, handleSave, handleSaveAs, openSaveAs, runExport, saveAsOpen, saveAsTaken, saveState, saveText, saveTitle } =
  saveFlow;
useExamWorkspaceKeyboard({ save: handleSave, undo: history.undo, redo: history.redo, step, listOpen });
// Ctrl/Cmd+Z inside an exam text editor is the same Ångra / Gör om the buttons run.
provideExamWorkspaceHistoryKeys({
  undo: () => void history.undo(),
  redo: () => void history.redo(),
  canUndo: history.canUndo,
  canRedo: history.canRedo,
});

/**
 * The derived labels (TASK-SKRIPT-41-02-04), owned by
 * `useExamWorkspaceViewLabels`: the instruction preview, the course label,
 * the formatted saved exports, and the zero-points flag.
 */
const { courseLabel, examInstructionsPreview, formattedSavedExports, zeroPoints } =
  useExamWorkspaceViewLabels({
    items,
    savedExports: exports.savedExports,
    workspaceDocument,
  });
/** One entry per printed total that differs from its questions' sum, for the list's note lines. */
const printedMismatches = computed(() =>
  workspaceDocument.value ? examWorkspacePrintedTotalMismatches(workspaceDocument.value) : [],
);
const enrichmentBusy = computed(() => enrichment.isRequesting.value || enrichment.isEnrichmentPending.value);

/**
 * The question-list commands (TASK-SKRIPT-41-02-04), owned by
 * `useExamWorkspaceListActions`: saving the list ordering, marking questions
 * reviewed, and adding entries and children.
 */
const { addChild, addEntry, setOrdering, toggleReviewed } = useExamWorkspaceListActions({
  editing,
  listOpen,
  listOrdering: editing.listOrdering,
  selectedItem,
  selectedParentId: selection.selectedParentId,
  store: props.store,
  structure,
  toast: useToast(),
});

onMounted(() => void loadSavedDocuments());
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
      :save-text="saveText"
      :save-title="saveTitle"
      :course-label="courseLabel"
      :total="total"
      :details-open="drawer === 'details'"
      :open-drawer-open="drawer === 'open'"
      :can-rename="workspaceDocument !== null && !disabled"
      :can-save-as="workspaceDocument !== null && !disabled"
      :suggest-busy="enrichmentBusy"
      :suggest-disabled="workspaceDocument === null || disabled"
      :is-phone="isPhone"
      :preview-open="previewOpen"
      @toggle-details="toggleDrawer('details')"
      @toggle-open="toggleDrawer('open')"
      @save-as="openSaveAs"
      @import-file="requestImportPick"
      @rename-title="editing.setTitle"
      @suggest-all="enrichment.requestSuggestionsForAll"
      @toggle-preview="togglePreview"
    >
      <template #export>
        <ExamWorkspaceExportMenu
          :blockers="blockers"
          :disabled="workspaceDocument === null"
          :fix-disabled="disabled"
          :suggest-busy="enrichmentBusy"
          :exporting-target="exports.exportingTarget.value"
          :exporting-destination="exports.exportingDestination.value"
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

    <ExamWorkspaceSignInBar
      v-if="signInPrompt"
      :message="signInPrompt"
      :depart="depart"
      @dismiss="dismissSignInPrompt"
    />
    <ExamWorkspaceEditLeaseNotice
      v-if="leaseReadOnly && workspaceDocument"
      :waiting="takeoverWaiting"
      @takeover="requestTakeover"
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
        :mismatches="printedMismatches"
        :can-add="!disabled"
        :disabled="disabled"
        :overlay="isPhone && listOpen"
        :collapsed="listRailCollapsed"
        :handle="isDesktop"
        @select="selectEntry"
        @add="addEntry"
        @group="(itemIds) => structure.groupItems(itemIds)"
        @clear-printed-total="editing.clearPrintedTotal"
        @close="listOpen = false"
        @set="setListWidth"
        @reset="resetWidth('list')"
        @toggle-collapse="toggleListCollapsed()"
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
        @set="(px) => setWidth('preview', px)"
        @reset="resetWidth('preview')"
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
        :import-pick-pending="importPickPending"
        @close="drawer = null"
        @import-pick-consumed="consumeImportPick"
        @run="runExport"
        @goto="gotoBlocker"
        @fix="fixBlocker"
        @set-ordering="setOrdering"
        @set="(px) => setWidth('drawer', px)"
        @reset="resetWidth('drawer')"
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
@media (max-width: 1279px) {
  .ws__bar { margin: var(--huleedu-space-2) var(--huleedu-space-4) 0; }
}
</style>

<style scoped src="./exam-workspace/examWorkspaceGrid.css"></style>
