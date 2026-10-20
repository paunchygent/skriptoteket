/**
 * Exam workspace edit lease on writes.
 *
 * Expected behavior:
 *   Every store sends the tab id; a lease-held store or move turns the
 *   editor read-only without a reload or a toast, and the pending edit is
 *   kept; while read-only, undo and redo store nothing.
 */

import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useToastStore } from "../../../stores/toast";
import {
  leaseHeldError,
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

describe("the edit lease on writes", () => {
  it("sends the tab id on every store", async () => {
    const { edit, history } = await setup();
    await flushPromises();
    edit("one", true);
    await history.flush(false);

    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledOnce();
    expect(apiMocks.storeExamWorkspaceUndoStep.mock.calls[0]![1]).toMatchObject({ tabId: "tab-1" });
  });

  it("turns read-only on a lease-held store and keeps the pending edit, without a reload", async () => {
    const { edit, gate, history, noteConflict, noteLeaseLost, workspaceDocument } = await setup();
    await flushPromises();
    apiMocks.storeExamWorkspaceUndoStep.mockRejectedValueOnce(leaseHeldError());
    edit("one", true);

    await history.flush(false);

    expect(noteLeaseLost).toHaveBeenCalledOnce();
    expect(gate.phase.value).toBe("readonly");
    expect(noteConflict).not.toHaveBeenCalled();
    expect(workspaceDocument.value!.title).toBe("one");
    expect(history.pending.value).toBe(true);
    expect(useToastStore().toasts).toEqual([]);
  });

  it("turns read-only on a lease-held move and never reads the step", async () => {
    const { edit, history, noteConflict, noteLeaseLost } = await setup();
    await flushPromises();
    edit("one", true);
    await history.flush(false);
    apiMocks.moveExamWorkspaceHistoryPosition.mockRejectedValueOnce(leaseHeldError());

    await history.undo();

    expect(noteLeaseLost).toHaveBeenCalledOnce();
    expect(noteConflict).not.toHaveBeenCalled();
    expect(apiMocks.getExamWorkspaceHistoryStep).not.toHaveBeenCalled();
    expect(useToastStore().toasts).toEqual([]);
  });

  it("stops undo and redo while read-only and stores nothing", async () => {
    const { edit, history, workspaceDocument } = await setup(false, { leaseHeld: false });
    await flushPromises();
    edit("one", true);
    await history.flush(false);

    expect(history.canUndo.value).toBe(false);
    expect(history.canRedo.value).toBe(false);
    expect(apiMocks.storeExamWorkspaceUndoStep).not.toHaveBeenCalled();

    await history.undo();
    expect(apiMocks.moveExamWorkspaceHistoryPosition).not.toHaveBeenCalled();
    expect(workspaceDocument.value!.title).toBe("one");
  });
});
