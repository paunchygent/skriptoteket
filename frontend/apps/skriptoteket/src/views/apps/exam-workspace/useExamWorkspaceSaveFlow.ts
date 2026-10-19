/**
 * Exam workspace save flow.
 *
 * Domain purpose:
 *   Spara som, the save status the header shows (TASK-SKRIPT-40-04-14, item
 *   6: `Sparar …`, `Sparat HH:MM`, `Inte sparat` with the reason), an export
 *   that stores a pending edit first, and the red export-blocker panel's jump
 *   to a blocking field and its in-place fixes. There is no Spara button:
 *   every stored history step also writes the exam file, so the history's
 *   status is the save state.
 *
 * Relationships:
 *   - Status and storing through `useExamWorkspaceEditing`; exports through
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
  /** True for a guest exam, whose saved status names the browser instead of Mina filer. */
  isGuest: boolean;
  frame: Ref<HTMLElement | null>;
  gotoItem: (itemId: string) => void;
  /** Open Provets uppgifter, which holds the title field. */
  openDetails: () => void;
}

/** Ticks `gotoBlocker` waits for a field that mounts after its question opens. */
const FOCUS_TARGET_MAX_TICKS = 5;

/** The saved exam file holds every confirmed edit. */
const SAVED_TITLE = "Provet i Mina filer har alla ändringar";

export function useExamWorkspaceSaveFlow({
  editing,
  enrichment,
  exports,
  blockers,
  disabled,
  isGuest,
  frame,
  gotoItem,
  openDetails,
}: ExamWorkspaceSaveFlowDeps) {
  const saveAsOpen = ref(false);
  const saveAsTaken = ref<string | null>(null);

  /** The one save status, straight from the history's confirmed snapshots. */
  const saveState = computed(() => editing.history.saveStatus.value.state);
  /** The header's status text: `Sparar …`, `Sparat HH:MM` (guest: `Sparat i webbläsaren HH:MM`), or `Inte sparat`. */
  const saveText = computed(() => editing.history.saveText.value);
  /** The status tooltip: the `Inte sparat` reason, or the saved confirmation. */
  const saveTitle = computed(() => {
    const status = editing.history.saveStatus.value;
    if (status.state === "unsaved") {
      return status.detail;
    }
    if (status.state === "saved" && !isGuest) {
      return SAVED_TITLE;
    }
    return null;
  });

  /** Ctrl/Cmd+S: store a pending edit at once. */
  async function handleSave(): Promise<void> {
    await editing.save();
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

  /** An export stores a pending edit first; a failed store stops it. */
  async function saveBeforeExport(): Promise<boolean> {
    return await editing.save();
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
    field?.scrollIntoView?.({ block: "center" });
    if (field?.hasAttribute("data-gap-id")) {
      field.click();
    } else {
      field?.focus();
    }
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
    saveText,
    saveTitle,
  };
}
