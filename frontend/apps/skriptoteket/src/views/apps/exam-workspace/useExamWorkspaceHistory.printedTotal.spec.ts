/**
 * Exam workspace printed-total line through Godta, Angra and Gor om.
 *
 * Expected behavior:
 *   The teacher's Godta on the printed-total points line clears that level's
 *   stored total as one structural undo step, so the line goes at once. Angra
 *   then sends the position move with the cursor and the step id (it never
 *   reads the step), and only the server's confirmation restores the working
 *   copy, the saved baseline and Sparat: nothing changes while the move is in
 *   flight. A reload remounts the move's returned document, so the line is
 *   back. Gor om moves forward again and the cleared file returns with it.
 *   This pins the TASK-SKRIPT-40-04-14 undo persistence for the staging walk
 *   at cf9547fa, where undo only moved the local position and never wrote the
 *   Mina filer file, so the reload lost the restored line.
 */

import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import { openGateHistory } from "./useExamWorkspaceEditing.history.specSupport";
import {
  examWorkspacePrintedTotalMismatches,
  withoutExamPrintedTotal,
} from "./examWorkspaceTotals";

const apiMocks = vi.hoisted(() => ({
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));

vi.mock("../../../api/examWorkspace", () => apiMocks);

/** The fake server's stored steps: baseline plus retained undo steps. */
type FakeServerState = {
  baseline: string;
  steps: string[];
  cursor: string;
  position: string | null;
};

/** The server's step store: stores append a step and write the file, the move writes the file too. */
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
  apiMocks.storeExamWorkspaceUndoStep.mockImplementation(
    async (
      _lineage: string,
      request: { expectedCursor: string; document: NativeExamDocument; afterStepId: string | null },
    ) => {
      let steps = state.steps;
      if (request.afterStepId !== null) {
        const ids = [state.baseline, ...steps];
        steps = steps.slice(0, ids.indexOf(request.afterStepId));
      }
      const stepId = `step-${++counter}`;
      documents.set(stepId, request.document);
      state.steps = [...steps, stepId];
      state.cursor = stepId;
      state.position = stepId;
      return { document: request.document, export_blockers: [], history: history() };
    },
  );
  // The position move: stands on a retained step and writes that step's document to the file.
  apiMocks.moveExamWorkspaceHistoryPosition.mockImplementation(
    async (_lineage: string, request: { expectedCursor: string; stepId: string }) => {
      const ids = [state.baseline, ...state.steps];
      if (!ids.includes(request.stepId)) {
        throw new Error("missing step");
      }
      state.position = request.stepId;
      state.cursor = `move-${++counter}`;
      const document = documents.get(request.stepId)!;
      return { document, export_blockers: [], history: history() };
    },
  );
  return state;
}

/** An exam whose printed total differs from its questions' sum, so the points line shows. */
function printedBaseline(): NativeExamDocument {
  const baseline = buildParentDocument();
  const sum = baseline.items.reduce((total, item) => total + (item.points ?? 0), 0);
  return { ...baseline, header: { ...baseline.header, printed_total: sum + 3 } };
}

async function setup() {
  const baseline = printedBaseline();
  fakeServer(baseline);
  const noteStored = vi.fn();
  const fixture = await openGateHistory({ api: apiMocks, baseline, noteStored });
  /** Godta on the printed-total line: clear the exam's stored total as one structural step. */
  function acceptPrintedTotal(): void {
    const current = fixture.workspaceDocument.value;
    if (current === null) {
      throw new Error("expected an open exam");
    }
    fixture.workspaceDocument.value = withoutExamPrintedTotal(current);
    fixture.history.noteEdit(true);
  }
  return {
    acceptPrintedTotal,
    baseline,
    history: fixture.history,
    historyCursor: fixture.historyCursor,
    noteStored,
    workspaceDocument: fixture.workspaceDocument,
  };
}

beforeEach(() => {
  setActivePinia(createPinia());
  for (const mock of Object.values(apiMocks)) mock.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("the printed-total line through Godta, Angra and Gor om", () => {
  it("stores Godta at once and the line goes with Sparat HH:MM", async () => {
    const { acceptPrintedTotal, history, workspaceDocument } = await setup();
    await flushPromises();
    expect(examWorkspacePrintedTotalMismatches(workspaceDocument.value!)).toHaveLength(1);

    acceptPrintedTotal();
    await history.flush(false);

    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledOnce();
    expect(workspaceDocument.value!.header.printed_total).toBeNull();
    expect(examWorkspacePrintedTotalMismatches(workspaceDocument.value!)).toEqual([]);
    expect(history.saveText.value).toMatch(/^Sparat \d{2}:\d{2}$/);
  });

  it("sends Angra as the position move, never a step read", async () => {
    const { acceptPrintedTotal, history, historyCursor, workspaceDocument } = await setup();
    await flushPromises();
    acceptPrintedTotal();
    await history.flush(false);
    const cursor = historyCursor.value;
    apiMocks.getExamWorkspaceHistoryStep.mockClear();
    apiMocks.moveExamWorkspaceHistoryPosition.mockClear();

    await history.undo();

    expect(apiMocks.getExamWorkspaceHistoryStep).not.toHaveBeenCalled();
    expect(apiMocks.moveExamWorkspaceHistoryPosition).toHaveBeenCalledOnce();
    expect(apiMocks.moveExamWorkspaceHistoryPosition.mock.calls[0]).toEqual([
      "lineage-1",
      { expectedCursor: cursor, stepId: "step-0", tabId: "tab-1" },
    ]);
    expect(workspaceDocument.value!.header.printed_total).toBe(printedBaseline().header.printed_total);
    expect(examWorkspacePrintedTotalMismatches(workspaceDocument.value!)).toHaveLength(1);
  });

  it("restores the working copy, the saved baseline and Sparat only when the move confirms", async () => {
    const { acceptPrintedTotal, history, noteStored, workspaceDocument } = await setup();
    await flushPromises();
    acceptPrintedTotal();
    await history.flush(false);
    const storedAfterAccept = vi.mocked(noteStored).mock.calls.length;
    const realMove = apiMocks.moveExamWorkspaceHistoryPosition.getMockImplementation();
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    apiMocks.moveExamWorkspaceHistoryPosition.mockImplementationOnce(
      async (...args: unknown[]) => {
        await gate;
        return realMove!(...args);
      },
    );

    const undoing = history.undo();
    await flushPromises();
    await flushPromises();

    // The move is in flight and the server has said nothing yet: the copy,
    // the saved baseline and the line all still hold the accepted state.
    expect(apiMocks.moveExamWorkspaceHistoryPosition).toHaveBeenCalledOnce();
    expect(workspaceDocument.value!.header.printed_total).toBeNull();
    expect(examWorkspacePrintedTotalMismatches(workspaceDocument.value!)).toEqual([]);
    expect(vi.mocked(noteStored).mock.calls.length).toBe(storedAfterAccept);

    release();
    await undoing;

    expect(workspaceDocument.value!.header.printed_total).toBe(
      printedBaseline().header.printed_total,
    );
    expect(vi.mocked(noteStored).mock.calls.length).toBe(storedAfterAccept + 1);
    expect(vi.mocked(noteStored).mock.lastCall![0]).toEqual(workspaceDocument.value);
    expect(history.saveStatus.value.state).toBe("saved");
    expect(history.saveText.value).toMatch(/^Sparat \d{2}:\d{2}$/);
    expect(examWorkspacePrintedTotalMismatches(workspaceDocument.value!)).toHaveLength(1);
  });

  it("reloads the confirmed move document with the line back, and Gor om clears it again", async () => {
    const { acceptPrintedTotal, history, workspaceDocument } = await setup();
    await flushPromises();
    acceptPrintedTotal();
    await history.flush(false);
    await history.undo();

    // The reload after Angra remounts the move's returned document: no accepted line.
    const confirmed = await apiMocks.moveExamWorkspaceHistoryPosition.mock.results[0]!.value;
    const reloaded = confirmed.document as NativeExamDocument;
    expect(reloaded.header.printed_total).toBe(printedBaseline().header.printed_total);
    expect(examWorkspacePrintedTotalMismatches(reloaded)).toEqual([
      expect.objectContaining({ level: "exam", printed: printedBaseline().header.printed_total }),
    ]);

    apiMocks.moveExamWorkspaceHistoryPosition.mockClear();
    await history.redo();

    expect(apiMocks.moveExamWorkspaceHistoryPosition).toHaveBeenCalledOnce();
    expect(apiMocks.moveExamWorkspaceHistoryPosition.mock.calls[0]![1].stepId).toBe("step-1");
    expect(workspaceDocument.value!.header.printed_total).toBeNull();
    expect(examWorkspacePrintedTotalMismatches(workspaceDocument.value!)).toEqual([]);
    expect(history.saveText.value).toMatch(/^Sparat \d{2}:\d{2}$/);
  });
});
