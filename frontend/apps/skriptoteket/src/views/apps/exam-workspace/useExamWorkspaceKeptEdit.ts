/**
 * Exam workspace kept-edit recovery state.
 *
 * Domain purpose:
 *   A refused edit survives the takeover (TASK-SKRIPT-40-04-14, USER decision
 *   2026-10-19 "Ta över keeps the edit"): when the lease is acquired with a
 *   pending edit, the step document that edit started from is kept here as
 *   its base, together with the refused working copy itself as its edited
 *   snapshot. The recovery routine merges that base and edited snapshot onto
 *   the newest server document, including across a failed reload, a failed
 *   history resync, and a later 409 conflict. Both stay until a merged store
 *   has succeeded, when the exam changes, or when the editor is disposed, so
 *   a failed resync can put the refused working copy back in front of the
 *   teacher and a stale recovery can never merge onto another exam.
 *
 * Relationships:
 *   - Owned by `useExamWorkspaceEditing`, which sets, reads and clears it;
 *     the merge itself stays in `examWorkspaceRefusedEditMerge`.
 */

import type { NativeExamDocument } from "../../../api/examWorkspace";

export type ExamWorkspaceKeptEdit = {
  /** The step document the refused edit started from. */
  base: NativeExamDocument;
  /** The refused working copy, kept until a merged store succeeds. */
  edited: NativeExamDocument;
};

export function useExamWorkspaceKeptEdit() {
  let kept: ExamWorkspaceKeptEdit | null = null;

  /** Keep the refused edit's base and working copy for its recovery. */
  function set(base: NativeExamDocument, edited: NativeExamDocument): void {
    kept = { base, edited };
  }

  /** Drop the recovery: the merged store succeeded or it no longer applies. */
  function clear(): void {
    kept = null;
  }

  /** The kept base and edited snapshot, or null when nothing is recovering. */
  function get(): ExamWorkspaceKeptEdit | null {
    return kept;
  }

  /** Whether a refused edit is waiting for its recovery to finish. */
  function has(): boolean {
    return kept !== null;
  }

  return { clear, get, has, set };
}
