/**
 * Exam workspace editing session.
 *
 * Domain purpose:
 *   Join the open exam, its server-stored undo history and the structure
 *   commands into one editing session: every teacher edit becomes an undo
 *   step through a 900 ms pause or at once, and the step store also writes
 *   the exam file (TASK-SKRIPT-40-04-14, one save model). A stale cursor
 *   reloads the exam. It
 *   owns `selectedParentId` (the part entry the teacher selected) so structural
 *   inserts land after the selected part; the selection composable drives it.
 *
 * Relationships:
 *   - Composes `useExamWorkspaceDocument`, `useExamWorkspaceHistory` and
 *     `useExamWorkspaceStructure`; consumed by `ExamWorkspaceView`.
 */

import { ref } from "vue";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import type { ExamWorkspaceStore } from "./examWorkspaceStore";
import { useExamWorkspaceDocument } from "./useExamWorkspaceDocument";
import { useExamWorkspaceHistory } from "./useExamWorkspaceHistory";
import { useExamWorkspaceStructure } from "./useExamWorkspaceStructure";

export function useExamWorkspaceEditing(store: ExamWorkspaceStore) {
  let noteEdit: (structural: boolean, before: NativeExamDocument | null) => void = () => undefined;
  // The selection composable is built by the view after this session; it registers
  // its part-entry selection here so a new part's instruction opens in the editor.
  let selectParent: (parentId: string) => void = () => undefined;
  // The part entry the teacher selected, shared with the selection composable
  // and the structure commands so Ny del and Ny instruktion land after it.
  const selectedParentId = ref<string | null>(null);
  const document = useExamWorkspaceDocument({
    onEdit: (structural, before) => noteEdit(structural, before),
    store,
  });
  const lineageId = () => document.summary.value?.lineage_id ?? null;
  const reload = () => document.reloadDocument();

  const history = useExamWorkspaceHistory({
    historyCursor: document.historyCursor,
    install: document.installDocument,
    isReplacing: () => document.isReplacing.value,
    // Not `isBusy`: that includes the replacing lock the history's own reads hold.
    isBlocked: () => document.isOperationBusy.value,
    lineageId,
    noteExportBlockers: document.noteExportBlockers,
    noteStored: document.noteStored,
    isGuest: () => store.guest !== null,
    onConflict: reload,
    replaceCopy: document.replaceCopy,
    savedRevision: () => document.savedRevision.value,
    serverDocument: document.serverDocument,
    shared: store.shared,
    workspaceDocument: document.workspaceDocument,
  });
  noteEdit = history.noteEdit;

  const structure = useExamWorkspaceStructure({
    applyCommandResponse: document.applyCommandResponse,
    editDocument: document.editDocument,
    flush: history.flush,
    historyCursor: document.historyCursor,
    isBusy: () => document.isBusy.value || history.storing.value,
    lineageId,
    onConflict: reload,
    replaceCopy: document.replaceCopy,
    savedRevision: () => document.savedRevision.value,
    selectItem: document.selectItem,
    selectParent: (parentId) => selectParent(parentId),
    selectedItemId: document.selectedItemId,
    selectedParentId,
    shared: store.shared,
    workspaceDocument: document.workspaceDocument,
  });

  /**
   * Ctrl/Cmd+S, and the store-first step of Spara som and exports: store the
   * pending edit as an undo step now. The step store also overwrites the
   * exam file, so this is the whole save.
   */
  async function save(): Promise<boolean> {
    return await history.flush(false);
  }

  /** Spara som: store the pending edit, then copy the working exam under `name`. */
  async function saveAs(name: string) {
    await history.flush(false);
    return await document.saveDocumentAs(name);
  }

  return {
    ...document,
    history,
    save,
    saveAs,
    selectedParentId,
    structure,
    /** The view wires its part-entry selection once the selection composable exists. */
    registerSelectParent: (select: (parentId: string) => void) => {
      selectParent = select;
    },
  };
}
