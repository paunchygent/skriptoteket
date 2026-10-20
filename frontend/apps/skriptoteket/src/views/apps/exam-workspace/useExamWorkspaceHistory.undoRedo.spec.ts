/**
 * Exam workspace undo and redo through the position move.
 *
 * Expected behavior:
 *   Undo and redo send the position move with the cursor and the step id
 *   instead of reading the step; a 409 from the move reloads the exam like a
 *   409 from a store; a failed redo move shows a toast and keeps the
 *   standing step.
 */

import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useToastStore } from "../../../stores/toast";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import {
  setupHistory,
  type HistorySetupHooks,
} from "./useExamWorkspaceHistory.specSupport";

const apiMocks = vi.hoisted(() => ({
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));

vi.mock("../../../api/examWorkspace", () => apiMocks);

async function setup(failFirstLoad = false, hooks: HistorySetupHooks = {}) {
  return setupHistory(apiMocks, failFirstLoad, hooks);
}

beforeEach(() => {
  setActivePinia(createPinia());
  for (const mock of Object.values(apiMocks)) mock.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("undo and redo through the position move", () => {
  it("sends the move with the cursor and the step id and never reads the step", async () => {
    const { edit, history, historyCursor, workspaceDocument } = await setup();
    await flushPromises();
    edit("one", true);
    edit("two", true);
    await history.flush(false);
    const cursor = historyCursor.value;
    apiMocks.getExamWorkspaceHistoryStep.mockClear();
    apiMocks.moveExamWorkspaceHistoryPosition.mockClear();

    await history.undo();

    expect(apiMocks.getExamWorkspaceHistoryStep).not.toHaveBeenCalled();
    expect(apiMocks.moveExamWorkspaceHistoryPosition).toHaveBeenCalledOnce();
    expect(apiMocks.moveExamWorkspaceHistoryPosition.mock.calls[0]).toEqual([
      "lineage-1",
      { expectedCursor: cursor, stepId: "step-1", tabId: "tab-1" },
    ]);
    expect(workspaceDocument.value!.title).toBe("one");
  });

  it("moves redo forward to the step after the standing one", async () => {
    const { edit, history, workspaceDocument } = await setup();
    await flushPromises();
    edit("one", true);
    edit("two", true);
    await history.flush(false);
    await history.undo();
    apiMocks.moveExamWorkspaceHistoryPosition.mockClear();

    await history.redo();

    expect(apiMocks.moveExamWorkspaceHistoryPosition).toHaveBeenCalledOnce();
    expect(apiMocks.moveExamWorkspaceHistoryPosition.mock.calls[0]![1].stepId).toBe("step-2");
    expect(workspaceDocument.value!.title).toBe("two");
  });

  it("reports the confirmed step as stored, so its document is the saved baseline", async () => {
    const { edit, history, noteStored } = await setup();
    await flushPromises();
    edit("one", true);
    await history.flush(false);
    await history.undo();

    expect(noteStored).toHaveBeenLastCalledWith(
      expect.objectContaining({ title: buildParentDocument().title }),
    );
    expect(history.saveStatus.value.state).toBe("saved");
  });

  it("reloads the exam when a move meets a newer cursor, without a toast", async () => {
    const { edit, history, noteConflict, server } = await setup();
    await flushPromises();
    edit("one", true);
    await history.flush(false);
    server.cursor = "other-tab";

    await history.undo();

    expect(noteConflict).toHaveBeenCalledOnce();
    expect(useToastStore().toasts).toEqual([]);
    expect(apiMocks.getExamWorkspaceHistoryStep).not.toHaveBeenCalled();
  });

  it("stops redo on a failed move and keeps the standing step", async () => {
    const { edit, history, workspaceDocument } = await setup();
    await flushPromises();
    edit("one", true);
    await history.flush(false);
    await history.undo();
    apiMocks.moveExamWorkspaceHistoryPosition.mockRejectedValueOnce(new Error("offline"));

    await history.redo();

    expect(useToastStore().toasts.map((toast) => toast.message)).toEqual([
      "Det gick inte att göra om. Försök igen.",
    ]);
    expect(workspaceDocument.value!.title).toBe(buildParentDocument().title);
  });
});
