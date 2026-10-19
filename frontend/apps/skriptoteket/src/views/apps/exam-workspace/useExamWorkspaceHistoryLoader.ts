/**
 * Exam workspace history step-list loader (TASK-SKRIPT-40-04-14, G1b).
 *
 * Domain purpose:
 *   Reload the server step list for the sync gate: the step the editor
 *   stands on becomes `base`, the fresh server copy the gate read, so a
 *   working copy that differs from it is a pending edit. The gate's
 *   generation replaces any join or token logic: an older load never runs,
 *   and a transport failure throws so the gate keeps `loading` and retries.
 */

import type { Ref } from "vue";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import type { ExamWorkspaceHistoryDeps } from "./useExamWorkspaceHistory";

export type ExamWorkspaceHistoryLoaderState = {
  baselineId: Ref<string | null>;
  position: Ref<string | null>;
  stepDocument: Ref<NativeExamDocument | null>;
  stepIds: Ref<string[]>;
};

export function createHistoryLoader(
  deps: Pick<ExamWorkspaceHistoryDeps, "lineageId" | "shared">,
  state: ExamWorkspaceHistoryLoaderState,
  reset: () => void,
): { load: (lineageId: string, base: NativeExamDocument | null) => Promise<void> } {
  /**
   * Reload the step list, standing the editor on `base`. A lineage move
   * meanwhile applies nothing; a read failure resets the list and throws so
   * the gate retries the whole fresh load.
   */
  async function load(lineageId: string, base: NativeExamDocument | null): Promise<void> {
    let history: Awaited<ReturnType<typeof deps.shared.getExamWorkspaceHistory>>;
    try {
      history = await deps.shared.getExamWorkspaceHistory(lineageId);
    } catch (error) {
      reset();
      throw error;
    }
    if (deps.lineageId() !== lineageId) {
      return;
    }
    state.baselineId.value = history.baseline_step_id;
    state.stepIds.value = [...history.step_ids];
    state.position.value = history.position_step_id;
    state.stepDocument.value = base;
  }

  return { load };
}
