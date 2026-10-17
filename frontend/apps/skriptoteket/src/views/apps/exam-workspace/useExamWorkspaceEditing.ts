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
    isBlocked: () => document.isBusy.value,
    lineageId,
    onConflict: reload,
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
    savedRevision: () => document.savedRevision.value,
    selectItem: document.selectItem,
    selectedItemId: document.selectedItemId,
    workspaceDocument: document.workspaceDocument,
  });

  /** Spara: store the pending edit as an undo step, then overwrite the exam file. */
  async function save(): Promise<boolean> {
    await history.flush(false);
    return await document.saveDocument();
  }

  return { ...document, history, save, structure };
}
