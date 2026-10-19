/**
 * Exam workspace guest sign-in request.
 *
 * Domain purpose:
 *   The one prompt slot lives in `ExamWorkspaceView`: a guest's AI or
 *   import control asks for it here instead of emitting a new event chain.
 *   Signed-in controls never call it.
 *
 * Relationships:
 *   - Provided by `ExamWorkspaceView` and read by the exam-workspace
 *     components that own an AI or import button.
 */

import { inject, type InjectionKey } from "vue";

/** Ask the view to show the guest sign-in prompt for `message`. */
export const EXAM_WORKSPACE_SIGN_IN_KEY: InjectionKey<(message: string) => void> =
  Symbol("exam-workspace-sign-in");

/** The sign-in request the surrounding `ExamWorkspaceView` provided; required, never defaulted. */
export function useExamWorkspaceSignIn(): (message: string) => void {
  const request = inject(EXAM_WORKSPACE_SIGN_IN_KEY);
  if (!request) {
    throw new Error("ExamWorkspaceSignIn was not provided by an ExamWorkspaceView ancestor.");
  }
  return request;
}

/** Inline copy shown when the pending edit cannot be settled before sign-in. */
export const EXAM_WORKSPACE_DEPARTURE_FAILURE_COPY =
  "Det gick inte att spara dina senaste ändringar i webbläsaren. Försök igen.";
