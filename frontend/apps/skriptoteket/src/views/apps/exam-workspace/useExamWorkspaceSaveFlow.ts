/**
 * Exam workspace save flow.
 *
 * Domain purpose:
 *   Spara and Spara som, the save state the header shows, an export that
 *   saves unsaved changes first, and the red export-blocker panel's jump to a
 *   blocking field and its in-place fixes.
 *
 * Relationships:
 *   - Saves through `useExamWorkspaceEditing`; exports through
 *     `useExamWorkspaceExports`; a suggested answer key through
 *     `useExamWorkspaceEnrichment`.
 *   - Jumps through the selection's `gotoItem`; the view owns the frame
 *     element the blocker's field is found in.
 *   - Consumed by `ExamWorkspaceView` and, as the `saveFirst` callback,
 *     by the exports composable.
 */

import { computed, nextTick, ref } from "vue";
import type { Ref } from "vue";

import type { ExamWorkspaceExportTarget } from "../../../api/examWorkspaceExports";
import type { ExamWorkspaceBlockerEntry } from "./examWorkspaceBlockers";
import { openBlockerField } from "./examWorkspaceGapOpenRequest";
import type { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import type { useExamWorkspaceEnrichment } from "./useExamWorkspaceEnrichment";
import type { useExamWorkspaceExports } from "./useExamWorkspaceExports";

export interface ExamWorkspaceSaveFlowDeps {
  editing: ReturnType<typeof useExamWorkspaceEditing>;
  enrichment: ReturnType<typeof useExamWorkspaceEnrichment>;
  exports: ReturnType<typeof useExamWorkspaceExports>;
  blockers: Readonly<Ref<readonly ExamWorkspaceBlockerEntry[]>>;
  /** True while the exam is busy or a structure command runs. */
  disabled: Readonly<Ref<boolean>>;
  frame: Ref<HTMLElement | null>;
  gotoItem: (itemId: string) => void;
  /** Open Provets uppgifter, which holds the title field. */
  openDetails: () => void;
}

/** Ticks `gotoBlocker` waits for a field that mounts after its question opens. */
const FOCUS_TARGET_MAX_TICKS = 5;

export function useExamWorkspaceSaveFlow({
  editing,
  enrichment,
  exports,
  blockers,
  disabled,
  frame,
  gotoItem,
  openDetails,
}: ExamWorkspaceSaveFlowDeps) {
  const { isDirty, workspaceDocument } = editing;

  const saving = ref(false);
  const saveAsOpen = ref(false);
  const saveAsTaken = ref<string | null>(null);

  const saveState = computed(() => (saving.value ? "saving" : isDirty.value ? "dirty" : "saved"));
  // Spara stays available on a clean exam too, where it writes nothing; it is unavailable only while nothing can be written.
  const canSave = computed(() => !disabled.value && workspaceDocument.value !== null);

  async function handleSave(): Promise<void> {
    if (!canSave.value || !isDirty.value) return;
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

  /** An export saves unsaved changes first, through Spara; a failed save has toasted why. */
  async function saveBeforeExport(): Promise<boolean> {
    if (!isDirty.value) return true;
    saving.value = true;
    try {
      return await editing.save();
    } finally {
      saving.value = false;
    }
  }

  function runExport(target: ExamWorkspaceExportTarget, destination: "download" | "files"): void {
    if (disabled.value || blockers.value.length > 0) return;
    void (destination === "files" ? exports.saveExportToFiles(target) : exports.exportDocument(target));
  }

  /** Lead to the question, or to the title, and the field that stops its export; a gap chip opens its popover. */
  async function gotoBlocker(blocker: ExamWorkspaceBlockerEntry): Promise<void> {
    if (blocker.itemId === null) {
      openDetails();
    } else {
      gotoItem(blocker.itemId);
    }
    if (!blocker.focus) return;
    // The question opens after one tick; a rich-text surface mounts a few ticks later.
    await nextTick();
    let field = frame.value?.querySelector<HTMLElement>(blocker.focus);
    for (let tick = 0; !field && tick < FOCUS_TARGET_MAX_TICKS; tick += 1) {
      await nextTick();
      field = frame.value?.querySelector<HTMLElement>(blocker.focus);
    }
    if (field) openBlockerField(field);
  }

  function fixBlocker(blocker: ExamWorkspaceBlockerEntry): void {
    if (blocker.itemId === null) return;
    switch (blocker.fix) {
      case "review":
      case "approve":
        editing.markItemReviewed(blocker.itemId);
        return;
      case "suggest_key":
        void enrichment.requestSuggestionForItem(blocker.itemId);
        return;
      case "remove_empty":
        editing.removeItemEmptyOptions(blocker.itemId);
        return;
      case "strip_headings":
        editing.removeItemOptionHeadings(blocker.itemId);
        return;
      case null:
        return;
    }
  }

  return {
    canSave,
    fixBlocker,
    gotoBlocker,
    handleSave,
    handleSaveAs,
    openSaveAs,
    runExport,
    saveAsOpen,
    saveAsTaken,
    saveBeforeExport,
    saveState,
  };
}
