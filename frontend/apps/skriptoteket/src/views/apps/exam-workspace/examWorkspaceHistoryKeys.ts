/**
 * Exam workspace history keys.
 *
 * Domain purpose:
 *   The workspace's Ångra and Gör om as the keyboard reaches them from inside
 *   an exam text editor. Ctrl/Cmd+Z in a text field runs the workspace's
 *   server-side history, never an editor-local undo, so a gap or picture
 *   record returns together with the text (TASK-SKRIPT-40-04-06 D2). The
 *   workspace view provides the pair once; every editor below it calls it.
 *
 * Relationships:
 *   - `ExamWorkspaceRichTextEditor` injects the pair and forwards its undo
 *     and redo shortcuts to it; with no provider the shortcuts do nothing
 *     but are still swallowed.
 *   - `ExamWorkspaceView` provides the pair with the history's own
 *     availability, so the top-bar pair and the future question toolbar
 *     pair disable on the same value without computing a second one.
 */

import { inject, provide } from "vue";
import type { InjectionKey, Ref } from "vue";

export type ExamWorkspaceHistoryKeys = {
  undo(): void;
  redo(): void;
  /** The top-bar Ångra's availability, for the question toolbar pair to disable on. */
  canUndo: Readonly<Ref<boolean>>;
  /** The top-bar Gör om's availability, for the question toolbar pair to disable on. */
  canRedo: Readonly<Ref<boolean>>;
};

const HISTORY_KEYS: InjectionKey<ExamWorkspaceHistoryKeys> = Symbol("exam-workspace-history-keys");

/** Provide the workspace's Ångra and Gör om to every exam text editor below the caller. */
export function provideExamWorkspaceHistoryKeys(keys: ExamWorkspaceHistoryKeys): void {
  provide(HISTORY_KEYS, keys);
}

/** The provided Ångra and Gör om, or null when no workspace provides them. */
export function useExamWorkspaceHistoryKeys(): ExamWorkspaceHistoryKeys | null {
  return inject(HISTORY_KEYS, null);
}
