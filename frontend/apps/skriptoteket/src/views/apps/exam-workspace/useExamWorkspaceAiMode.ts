/**
 * Exam workspace AI mode.
 *
 * Domain purpose:
 *   One structural rule for what an AI control may do: a guest's control
 *   stays enabled and asks for sign-in, a signed-in admin's control runs,
 *   and any other signed-in control follows the admin-only gate. Guest mode
 *   is structural (the teacher half is null); the admin gate is the
 *   temporary `useAiAccess` role check.
 *
 * Relationships:
 *   - Read by the exam-workspace components that own an AI button
 *     (header, export blockers, details drawer, import box); each keeps its
 *     own derived booleans and its own sign-in request or emit.
 */

import { computed, type ComputedRef } from "vue";

import { useAiAccess } from "../../../composables/useAiAccess";
import { useInjectedExamWorkspaceStore } from "./examWorkspaceStore";

/** What an AI control may do: ask for sign-in, run, or follow the admin gate. */
export type ExamWorkspaceAiMode = "guest" | "allowed" | "admin_only";

/** The AI mode of the surrounding `ExamWorkspaceView`; required store, never defaulted. */
export function useExamWorkspaceAiMode(): ComputedRef<ExamWorkspaceAiMode> {
  const store = useInjectedExamWorkspaceStore();
  const { canUseAi } = useAiAccess();
  return computed(() =>
    store.teacher === null ? "guest" : canUseAi.value ? "allowed" : "admin_only",
  );
}
