/**
 * Exam workspace kept-edit recovery state.
 *
 * Domain purpose:
 *   A refused edit survives the takeover (TASK-SKRIPT-40-04-14, USER decision
 *   2026-10-19 "Ta över keeps the edit"): when the lease is acquired with a
 *   pending edit, the step document that edit started from is kept here as
 *   its base. The recovery routine merges that base and the captured working
 *   copy onto the newest server document, including across a failed reload
 *   and a later 409 conflict. The base clears only after a merged store has
 *   succeeded, when the exam changes, or when the editor is disposed, so a
 *   stale recovery can never merge onto another exam.
 *
 * Relationships:
 *   - Owned by `useExamWorkspaceEditing`, which sets, reads and clears it;
 *     the merge itself stays in `examWorkspaceRefusedEditMerge`.
 */

import type { NativeExamDocument } from "../../../api/examWorkspace";

export function useExamWorkspaceKeptEdit() {
  let base: NativeExamDocument | null = null;

  /** Keep the step document a refused edit started from. */
  function set(document: NativeExamDocument): void {
    base = document;
  }

  /** Drop the recovery: the merged store succeeded or it no longer applies. */
  function clear(): void {
    base = null;
  }

  /** The kept step document, or null when no refused edit is recovering. */
  function get(): NativeExamDocument | null {
    return base;
  }

  /** Whether a refused edit is waiting for its recovery to finish. */
  function has(): boolean {
    return base !== null;
  }

  return { clear, get, has, set };
}
