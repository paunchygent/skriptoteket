/**
 * A named double of the server's undo-step store for view specs.
 *
 * Spara sends the history position the editor stands on, so a view that
 * saves needs a loaded step list. This double keeps an import baseline and
 * the steps its autosaves store; it models no conflicts and no Spara
 * retention, which `useExamWorkspaceEditing.history.spec.ts` covers.
 */

import type { Mock } from "vitest";

import type { NativeExamDocument } from "../../api/examWorkspace";

export const HISTORY_BASELINE_STEP_ID = "history-step-0";

type HistoryApiMocks = {
  getExamWorkspaceHistory: Mock;
  getExamWorkspaceHistoryStep: Mock;
  storeExamWorkspaceUndoStep: Mock;
};

type StoreRequest = { afterStepId: string | null; document: NativeExamDocument };

export function arrangeStepHistory(api: HistoryApiMocks) {
  let counter = 0;
  const documents = new Map<string, NativeExamDocument>();
  const state = { position: HISTORY_BASELINE_STEP_ID, steps: [] as string[] };
  const history = () => ({
    baseline_step_id: HISTORY_BASELINE_STEP_ID,
    cursor: state.position,
    position_step_id: state.position,
    step_ids: [...state.steps],
  });
  api.getExamWorkspaceHistory.mockImplementation(async () => history());
  api.getExamWorkspaceHistoryStep.mockImplementation(async (_lineage: string, stepId: string) => {
    const document = documents.get(stepId);
    if (!document) {
      throw new Error(`The history double holds no document for ${stepId}.`);
    }
    return { document, step_id: stepId };
  });
  api.storeExamWorkspaceUndoStep.mockImplementation(async (_lineage: string, request: StoreRequest) => {
    const after = request.afterStepId ?? state.position;
    state.steps = state.steps.slice(0, [HISTORY_BASELINE_STEP_ID, ...state.steps].indexOf(after));
    const stepId = `history-step-${++counter}`;
    documents.set(stepId, request.document);
    state.steps = [...state.steps, stepId].slice(-10);
    state.position = stepId;
    return { document: request.document, export_blockers: [], history: history() };
  });
  return { documents, state };
}
