/**
 * Exam workspace guest sign-in prompt state.
 *
 * Domain purpose:
 *   Own the one guest sign-in prompt slot: a guest's AI or import control
 *   asks for it through the sign-in key, the sign-in bar renders it, and
 *   following the login link first settles the pending edit so signing in
 *   never abandons the working copy before its autosave.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceView`, which keeps `defineExpose({ settleForDeparture })`
 *     and clears the prompt from its open-document watcher.
 *   - Provides `EXAM_WORKSPACE_SIGN_IN_KEY` for the exam-workspace
 *     components that own an AI or import button.
 *   - Rendered through `ExamWorkspaceSignInBar`.
 */

import { computed, provide, ref } from "vue";
import type { ComputedRef, Ref } from "vue";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import { EXAM_WORKSPACE_SIGN_IN_KEY } from "./examWorkspaceSignIn";
import type { ExamWorkspaceStore } from "./examWorkspaceStore";

export type ExamWorkspaceGuestSignInParams = {
  /** The undo history whose pending edit a sign-in exit settles first. */
  history: { flush: (settle?: boolean) => Promise<boolean> };
  /** The workspace store; a missing teacher half means guest mode. */
  store: ExamWorkspaceStore;
  /** The exam in front of the guest; null while none is open. */
  workspaceDocument: Readonly<Ref<NativeExamDocument | null>>;
};

export function useExamWorkspaceGuestSignIn(params: ExamWorkspaceGuestSignInParams) {
  /** Guest mode is the store without the teacher half; signed-in controls never prompt. */
  const isGuest: ComputedRef<boolean> = computed(() => params.store.teacher === null);
  /** The one guest sign-in prompt; components request it through the sign-in key. */
  const signInPrompt: Ref<string | null> = ref(null);

  function requestSignIn(message: string): void {
    signInPrompt.value = message;
  }

  function dismissSignInPrompt(): void {
    signInPrompt.value = null;
  }

  provide(EXAM_WORKSPACE_SIGN_IN_KEY, requestSignIn);

  /**
   * Safe departure for every sign-in exit: store the pending edit as an undo
   * step first, through the same flush the structural commands use, so signing
   * in never abandons the working copy before its autosave. With no open
   * document there is nothing to settle. Resolves the flush result: false
   * keeps the working copy mounted instead of leaving.
   */
  async function settleForDeparture(): Promise<boolean> {
    if (params.workspaceDocument.value === null) {
      return true;
    }
    return params.history.flush(true);
  }

  return { dismissSignInPrompt, isGuest, settleForDeparture, signInPrompt };
}
