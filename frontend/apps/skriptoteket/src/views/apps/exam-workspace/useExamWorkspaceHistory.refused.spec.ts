/**
 * Exam workspace autosave and server-stored undo history: a pending edit the
 * save rules refuse.
 *
 * Expected behavior (TASK-SKRIPT-40-04-09 repair A1):
 *   When the working copy is a draft the save rules refuse (HTTP 422), undo
 *   installs the step the editor stands on and leaves nothing pending, so the
 *   refused edit is discarded; a second undo then moves to the step before.
 *   The refusal already shows inline in the editor, so no toast fires.
 */

import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { effectScope, ref } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import type { NativeExamDocument } from "../../../api/examWorkspace";
import { useToastStore } from "../../../stores/toast";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { useExamWorkspaceHistory } from "./useExamWorkspaceHistory";

const apiMocks = vi.hoisted(() => ({
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));

vi.mock("../../../api/examWorkspace", () => apiMocks);

const MAX_STEPS = 10;

type FakeServerState = {
  baseline: string;
  steps: string[];
  cursor: string;
  position: string | null;
};

function fakeServer(baseline: NativeExamDocument) {
  let counter = 0;
  const documents = new Map<string, NativeExamDocument>([["step-0", baseline]]);
  const state: FakeServerState = {
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
  apiMocks.getExamWorkspaceHistory.mockImplementation(async () => history());
  apiMocks.getExamWorkspaceHistoryStep.mockImplementation(async (_lineage: string, stepId: string) => ({
    document: documents.get(stepId)!,
    step_id: stepId,
  }));
  apiMocks.moveExamWorkspaceHistoryPosition.mockImplementation(
    async (_lineage: string, request: { expectedCursor: string; stepId: string }) => {
      state.position = request.stepId;
      state.cursor = `move-${++counter}`;
      return { document: documents.get(request.stepId)!, export_blockers: [], history: history() };
    },
  );
  apiMocks.storeExamWorkspaceUndoStep.mockImplementation(
    async (
      _lineage: string,
      request: { expectedCursor: string; document: NativeExamDocument; afterStepId: string | null },
    ) => {
      if (request.expectedCursor !== state.cursor) {
        throw Object.assign(new Error("conflict"), { status: 409 });
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
  return state;
}

function titled(document: NativeExamDocument, title: string): NativeExamDocument {
  return { ...document, title };
}

function setup() {
  const baseline = buildParentDocument();
  fakeServer(baseline);
  const workspaceDocument = ref<NativeExamDocument | null>(baseline);
  const serverDocument = ref<NativeExamDocument | null>(baseline);
  const historyCursor = ref<string | null>("step-0");
  const onConflict = vi.fn(async () => undefined);
  const history = effectScope().run(() =>
    useExamWorkspaceHistory({
      historyCursor,
      install: (document) => {
        workspaceDocument.value = document;
      },
      isBlocked: () => false,
      hasKeptEdit: () => false,
      noteKeptStored: () => undefined,
      recoverKeptEdit: async () => false,
      isGuest: () => false,
      isReadOnly: () => false,
      isReplacing: () => false,
      replaceCopy: (run) => run(),
      lineageId: () => "lineage-1",
      noteExportBlockers: vi.fn(),
      noteLeaseLost: vi.fn(),
      noteStored: vi.fn(),
      onConflict,
      savedRevision: () => baseline.revision,
      serverDocument,
      shared: serverExamWorkspaceStore.shared,
      tabId: () => "tab-1",
      workspaceDocument,
    }),
  )!;
  function edit(title: string, structural = false): void {
    workspaceDocument.value = titled(workspaceDocument.value!, title);
    history.noteEdit(structural);
  }
  return { edit, history, workspaceDocument };
}

function validationError(): ApiError {
  return new ApiError({
    code: "VALIDATION_ERROR", message: "Validation error", details: [], correlationId: null, status: 422,
  });
}

/** Negative points name their question inline, so the refusal copy is non-null. */
function refused(document: NativeExamDocument): NativeExamDocument {
  return {
    ...document,
    items: document.items.map((item, index) => (index === 0 ? { ...item, points: -1 } : item)),
  };
}

beforeEach(() => {
  setActivePinia(createPinia());
  for (const mock of Object.values(apiMocks)) mock.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("a pending edit the save rules refuse", () => {
  it("is discarded by undo, which reinstalls the standing step with nothing pending", async () => {
    const { edit, history, workspaceDocument } = setup();
    await flushPromises();
    edit("one", true);
    await history.flush(false);
    const stored = workspaceDocument.value!;
    workspaceDocument.value = refused(stored);
    apiMocks.storeExamWorkspaceUndoStep.mockRejectedValueOnce(validationError());

    await history.undo();

    expect(workspaceDocument.value).toEqual(stored);
    expect(history.pending.value).toBe(false);
    expect(history.saveStatus.value.state).toBe("saved");
    expect(useToastStore().toasts).toEqual([]);
  });

  it("is gone after the discard, so the next undo moves to the step before", async () => {
    const { edit, history, workspaceDocument } = setup();
    await flushPromises();
    edit("one", true);
    await history.flush(false);
    workspaceDocument.value = refused(workspaceDocument.value!);
    apiMocks.storeExamWorkspaceUndoStep.mockRejectedValue(validationError());

    await history.undo();
    await history.undo();

    expect(workspaceDocument.value!.title).toBe(buildParentDocument().title);
    expect(history.canRedo.value).toBe(true);
  });
});
