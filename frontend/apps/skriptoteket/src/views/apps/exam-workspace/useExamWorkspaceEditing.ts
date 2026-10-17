/**
 * Exam workspace editing session.
 *
 * Domain purpose:
 *   Join the open exam, its server-stored undo history and the structure
 *   commands into one editing session: every teacher edit becomes an undo
 *   step, Spara stores the pending edit before it overwrites the exam file,
 *   and a stale cursor reloads the exam (TASK-SKRIPT-39-04-08, 40-04-03).
 *
 * Relationships:
 *   - Composes `useExamWorkspaceDocument`, `useExamWorkspaceHistory` and
 *     `useExamWorkspaceStructure`; consumed by `ExamWorkspaceView`.
 */

import { useExamWorkspaceDocument } from "./useExamWorkspaceDocument";
import { useExamWorkspaceHistory } from "./useExamWorkspaceHistory";
import { useExamWorkspaceStructure } from "./useExamWorkspaceStructure";

export function useExamWorkspaceEditing() {
  let noteEdit: (structural: boolean) => void = () => undefined;
  const document = useExamWorkspaceDocument({ onEdit: (structural) => noteEdit(structural) });
  const lineageId = () => document.summary.value?.lineage_id ?? null;
  const reload = () => document.reloadDocument();

  const history = useExamWorkspaceHistory({
    historyCursor: document.historyCursor,
    install: document.installDocument,
    isReplacing: () => document.isReplacing.value,
    // Not `isBusy`: that includes the replacing lock the history's own reads hold.
    isBlocked: () => document.isOperationBusy.value,
    lineageId,
    onConflict: reload,
    replaceCopy: document.replaceCopy,
    savedRevision: () => document.savedRevision.value,
    serverDocument: document.serverDocument,
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
    selectedItemId: document.selectedItemId,
    workspaceDocument: document.workspaceDocument,
  });

  /**
   * Spara: store the pending edit as an undo step, then overwrite the exam file.
   * Spara writes the copy itself, so it proceeds when the step write failed: it
   * sends the editor's position, and the server retains the saved copy as the
   * step after it, so undo and redo stay available at once.
   */
  async function save(): Promise<boolean> {
    await history.flush(false);
    return await document.saveDocument(history.position.value);
  }

  /** Spara som: store the pending edit, then copy the working exam under `name`. */
  async function saveAs(name: string) {
    await history.flush(false);
    return await document.saveDocumentAs(name);
  }

  return { ...document, history, save, saveAs, structure };
}
