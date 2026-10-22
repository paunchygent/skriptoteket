/**
 * Exam workspace AI mode.
 *
 * Domain purpose:
 *   One structural rule for what an AI control may do: a guest's control
 *   stays enabled and asks for sign-in, and every signed-in user's control
 *   runs. Guest mode is structural (the teacher half is null); every
 *   signed-in user runs AI.
 *
 * Relationships:
 *   - Read by the exam-workspace components that own an AI button
 *     (header, export blockers, details drawer, import box); each keeps its
 *     own derived booleans and its own sign-in request or emit.
 */

import { computed, type ComputedRef } from "vue";

import { useInjectedExamWorkspaceStore } from "./examWorkspaceStore";

/** What an AI control may do: ask for sign-in, or run. */
export type ExamWorkspaceAiMode = "guest" | "allowed";

/** The AI mode of the surrounding `ExamWorkspaceView`; required store, never defaulted. */
export function useExamWorkspaceAiMode(): ComputedRef<ExamWorkspaceAiMode> {
  const store = useInjectedExamWorkspaceStore();
  return computed(() => (store.teacher === null ? "guest" : "allowed"));
}
