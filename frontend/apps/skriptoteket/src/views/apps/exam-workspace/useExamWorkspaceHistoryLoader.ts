/**
 * Exam workspace history step-list loader (TASK-SKRIPT-40-04-14).
 *
 * Domain purpose:
 *   Reload the server step list after the document owner replaced the copy:
 *   the step the editor stands on becomes the fresh server copy, so a working
 *   copy that differs from it is a pending edit. A lineage move, a newer load
 *   or a read failure resolves false; a read failure also resets the list, so
 *   no step can be stored until the list is read again.
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
  deps: Pick<ExamWorkspaceHistoryDeps, "lineageId" | "serverDocument" | "shared">,
  state: ExamWorkspaceHistoryLoaderState,
  reset: () => void,
): { load: (lineageId: string) => Promise<boolean> } {
  let loadToken = 0;
  /** The read in flight, if any, with the lineage and server document it captured. */
  let inFlight: {
    base: NativeExamDocument | null;
    lineageId: string;
    promise: Promise<boolean>;
    token: number;
  } | null = null;

  /** Reload the step list; true when it matches the fresh server copy, false
   * when the lineage moved on, a newer load started, or the read failed. A
   * load for the same lineage and server document as the read in flight
   * shares it instead of sending a second read. */
  async function load(lineageId: string): Promise<boolean> {
    const base = deps.serverDocument.value;
    const running = inFlight;
    if (running !== null && running.lineageId === lineageId && running.base === base) {
      return running.promise;
    }
    const token = ++loadToken;
    const pending = read(lineageId, base, token);
    inFlight = { base, lineageId, promise: pending, token };
    try {
      return await pending;
    } finally {
      if (inFlight !== null && inFlight.token === token) {
        inFlight = null;
      }
    }
  }

  async function read(lineageId: string, base: NativeExamDocument | null, token: number): Promise<boolean> {
    try {
      const history = await deps.shared.getExamWorkspaceHistory(lineageId);
      if (token !== loadToken || deps.lineageId() !== lineageId) {
        return false;
      }
      state.baselineId.value = history.baseline_step_id;
      state.stepIds.value = [...history.step_ids];
      state.position.value = history.position_step_id;
      state.stepDocument.value = base;
      return state.stepDocument.value === deps.serverDocument.value;
    } catch {
      if (token === loadToken) {
        reset();
      }
      return false;
    }
  }

  return { load };
}
