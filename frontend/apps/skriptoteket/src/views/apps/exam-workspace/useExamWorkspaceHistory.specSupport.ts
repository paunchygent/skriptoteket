/**
 * Shared setup for the useExamWorkspaceHistory responsibility specs
 * (TASK-SKRIPT-40-04-14, rereview T3).
 *
 * The fake server's stored step state plus the gate-backed history harness:
 * the server's step store with the same truncation and pruning rules as
 * exam_workspace_undo_steps.py, and a production history opened on it
 * through the gate harness. Each responsibility spec keeps its own api
 * doubles and calls `setupHistory`; nothing here is duplicated per spec.
 */

import type { Mock } from "vitest";
import { vi } from "vitest";

import { ApiError } from "../../../api/client";
import type { NativeExamDocument } from "../../../api/examWorkspace";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import type { ExamWorkspaceSharedStore } from "./examWorkspaceStore";
import { openGateHistory } from "./useExamWorkspaceEditing.history.specSupport";

/** The api double each history spec mocks "../../../api/examWorkspace" with. */
export type HistoryApiMocks = {
  getExamWorkspaceDocument: Mock;
  getExamWorkspaceHistory: Mock;
  getExamWorkspaceHistoryStep: Mock;
  moveExamWorkspaceHistoryPosition: Mock;
  storeExamWorkspaceUndoStep: Mock;
};

export type HistorySetupHooks = {
  leaseHeld?: boolean;
  onLeaseLost?: () => void;
  shared?: ExamWorkspaceSharedStore;
};

const MAX_STEPS = 10;

/** The fake server's stored step state: baseline plus retained undo steps. */
export type FakeHistoryServerState = {
  baseline: string;
  steps: string[];
  cursor: string;
  position: string | null;
};

function conflict(): ApiError {
  return new ApiError({ code: "CONFLICT", message: "Dokumentet har ändrats sedan det öppnades.", status: 409 });
}

export function validationError(): ApiError {
  return new ApiError({
    code: "VALIDATION_ERROR", message: "Validation error", details: [], correlationId: null, status: 422,
  });
}

export function leaseHeldError(): ApiError {
  return new ApiError({
    code: "EDIT_LEASE_HELD",
    message: "Provet redigeras i en annan flik.",
    status: 409,
  });
}

/** The server's step store: same truncation and pruning rules as exam_workspace_undo_steps.py. */
export function fakeHistoryServer(api: HistoryApiMocks, baseline: NativeExamDocument): FakeHistoryServerState {
  let counter = 0;
  const documents = new Map<string, NativeExamDocument>([["step-0", baseline]]);
  const state: FakeHistoryServerState = {
    baseline: "step-0",
    steps: [],
    cursor: "step-0",
    position: "step-0",
  };
  const history = () => ({
    baseline_step_id: state.baseline,
    cursor: state.cursor,
    position_step_id: state.position,
    step_ids: [...state.steps],
  });
  api.getExamWorkspaceHistory.mockImplementation(async () => history());
  api.getExamWorkspaceHistoryStep.mockImplementation(async (_lineage: string, stepId: string) => ({
    document: documents.get(stepId)!,
    step_id: stepId,
  }));
  api.storeExamWorkspaceUndoStep.mockImplementation(
    async (
      _lineage: string,
      request: { expectedCursor: string; document: NativeExamDocument; afterStepId: string | null },
    ) => {
      if (request.expectedCursor !== state.cursor) {
        throw conflict();
      }
      let steps = state.steps;
      if (request.afterStepId !== null) {
        const ids = [state.baseline, ...steps];
        steps = steps.slice(0, ids.indexOf(request.afterStepId));
      }
      const stepId = `step-${++counter}`;
      documents.set(stepId, request.document);
      state.steps = [...steps, stepId].slice(-MAX_STEPS);
      state.cursor = stepId;
      state.position = stepId;
      return { document: request.document, export_blockers: [], history: history() };
    },
  );
  // The position move: stands on a retained step and rotates the cursor, no new step.
  api.moveExamWorkspaceHistoryPosition.mockImplementation(
    async (_lineage: string, request: { expectedCursor: string; stepId: string }) => {
      if (request.expectedCursor !== state.cursor) {
        throw conflict();
      }
      const ids = [state.baseline, ...state.steps];
      if (!ids.includes(request.stepId)) {
        throw new ApiError({ code: "NOT_FOUND", message: "Ångrasteget finns inte.", status: 404 });
      }
      state.position = request.stepId;
      state.cursor = `move-${++counter}`;
      const document = documents.get(request.stepId)!;
      return { document, export_blockers: [], history: history() };
    },
  );
  return state;
}

export function titled(document: NativeExamDocument, title: string): NativeExamDocument {
  return { ...document, title };
}

export async function setupHistory(
  api: HistoryApiMocks,
  failFirstLoad = false,
  hooks: HistorySetupHooks = {},
) {
  const baseline = buildParentDocument();
  const server = fakeHistoryServer(api, baseline);
  const noteStored = vi.fn();
  const noteLeaseLost = vi.fn();
  const noteConflict = vi.fn();
  const fixture = await openGateHistory({
    api,
    baseline,
    failFirstHistoryLoad: failFirstLoad,
    leaseHeld: hooks.leaseHeld,
    noteConflict: () => {
      noteConflict();
    },
    noteLeaseLost: () => {
      noteLeaseLost();
      hooks.onLeaseLost?.();
    },
    noteStored: (document) => {
      noteStored(document);
    },
    shared: hooks.shared,
  });
  function edit(title: string, structural = false): void {
    const current = fixture.workspaceDocument.value;
    if (current === null) {
      throw new Error("expected an open exam");
    }
    fixture.workspaceDocument.value = titled(current, title);
    fixture.history.noteEdit(structural);
  }
  return { ...fixture, edit, noteConflict, noteLeaseLost, noteStored, server };
}
