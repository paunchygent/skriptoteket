/**
 * Exam workspace history step-list reader (TASK-SKRIPT-40-04-14, F1).
 *
 * Domain purpose:
 *   Reload the server step list as a pure read: it returns the parsed step
 *   list and never writes state or calls reset. The sync gate settles the
 *   read through the fence and only then applies or resets the history
 *   through a fenced step, so an abandoned read changes nothing: no reset,
 *   toast, retry timer or status.
 */

import type { ExamWorkspaceSharedStore } from "./examWorkspaceStore";

/** The parsed step list: the baseline, the step ids in order, and the standing step. */
export type ExamWorkspaceStepListRead = {
  baselineId: string;
  stepIds: string[];
  position: string | null;
};

export async function readStepList(
  shared: ExamWorkspaceSharedStore,
  lineageId: string,
): Promise<ExamWorkspaceStepListRead> {
  const history = await shared.getExamWorkspaceHistory(lineageId);
  return {
    baselineId: history.baseline_step_id,
    position: history.position_step_id,
    stepIds: [...history.step_ids],
  };
}
