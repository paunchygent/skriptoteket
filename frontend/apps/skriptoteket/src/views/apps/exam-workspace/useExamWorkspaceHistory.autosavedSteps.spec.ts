/**
 * Exam workspace autosaved undo steps.
 *
 * Expected behavior:
 *   Against a fake of the server's step store (baseline plus retained
 *   steps, `after_step_id` truncates the redo steps): typing becomes one
 *   step only after the pause, a structural edit at once; undo stores the
 *   pending edit first so it can be redone; an edit after undo branches and
 *   drops the redo steps; a read that echoes an older cursor neither reloads
 *   nor breaks the next write; a failed history load is retried before the
 *   next write; a failed undo move shows a toast, and a rejected autosave
 *   shows Swedish copy only when the editor does not already say why inline.
 */

import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useToastStore } from "../../../stores/toast";import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import { serverExamWorkspaceStore, type ExamWorkspaceSharedStore } from "./examWorkspaceStore";
import { EXAM_WORKSPACE_TYPING_PAUSE_MS } from "./useExamWorkspaceHistory";
import {
  setupHistory,
  validationError,
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

describe("autosaved undo steps", () => {
  it("stores typing once, after the pause", async () => {
    vi.useFakeTimers();
    const { edit } = await setup();
    await flushPromises();

    edit("A");
    edit("AB");
    vi.advanceTimersByTime(EXAM_WORKSPACE_TYPING_PAUSE_MS - 1);
    await flushPromises();
    expect(apiMocks.storeExamWorkspaceUndoStep).not.toHaveBeenCalled();

    vi.advanceTimersByTime(1);
    await flushPromises();
    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledOnce();
    expect(apiMocks.storeExamWorkspaceUndoStep.mock.calls[0]![1].document.title).toBe("AB");
  });

  it("stores the pending edit before undo, so the edit itself can be redone", async () => {
    const { edit, history, workspaceDocument } = await setup();
    await flushPromises();
    edit("first", true);
    await flushPromises();
    edit("typed, not yet stored");

    await history.undo();
    expect(workspaceDocument.value!.title).toBe("first");
    expect(history.canRedo.value).toBe(true);

    await history.redo();
    expect(workspaceDocument.value!.title).toBe("typed, not yet stored");
  });

  it("branches after an undo: the next edit drops the redo steps", async () => {
    const { edit, history, server, workspaceDocument } = await setup();
    await flushPromises();
    edit("one", true);
    edit("two", true);
    edit("three", true);
    await history.flush(false);

    await history.undo();
    await history.undo();
    expect(workspaceDocument.value!.title).toBe("one");
    edit("branch", true);
    await history.flush(false);

    expect(server.steps).toHaveLength(2);
    expect(history.canRedo.value).toBe(false);
    await history.undo();
    expect(workspaceDocument.value!.title).toBe("one");
  });

  it("keeps ten steps after the baseline and cannot undo past the oldest kept step", async () => {
    const { edit, history, workspaceDocument } = await setup();
    await flushPromises();
    for (let index = 1; index <= 12; index += 1) {
      edit(`edit ${index}`, true);
    }
    await history.flush(false);

    let undos = 0;
    while (history.canUndo.value && undos < 20) {
      await history.undo();
      undos += 1;
    }

    // Ten kept steps plus the baseline: nine undos reach the oldest step, one more the baseline.
    expect(undos).toBe(10);
    expect(workspaceDocument.value!.title).toBe(buildParentDocument().title);
  });

  it("settles an undone step as the newest one before a server command", async () => {
    const { edit, history, historyCursor, server, workspaceDocument } = await setup();
    await flushPromises();
    edit("one", true);
    edit("two", true);
    await history.flush(false);
    await history.undo();

    await history.flush(true);

    expect(historyCursor.value).toBe(server.cursor);
    expect(apiMocks.storeExamWorkspaceUndoStep.mock.lastCall![1]).toMatchObject({
      afterStepId: "step-1",
    });
    expect(workspaceDocument.value!.title).toBe("one");
  });

  it("ignores a read that echoes an older cursor and keeps writing", async () => {
    const { edit, history, historyCursor, noteConflict } = await setup();
    await flushPromises();
    edit("one", true);
    await history.flush(false);
    apiMocks.getExamWorkspaceHistory.mockClear();

    historyCursor.value = "step-0";
    await flushPromises();
    // The echo guard restores this tab's own cursor before the next write.
    expect(historyCursor.value).toBe("step-1");
    edit("two", true);
    await history.flush(false);

    // The gate refreshes the step list for the foreign cursor, but the echo
    // changes nothing else: no conflict, and both edits are stored.
    expect(apiMocks.getExamWorkspaceHistory).toHaveBeenCalled();
    expect(noteConflict).not.toHaveBeenCalled();
    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(2);
  });

  it("loads the step list again when it failed before the first write", async () => {
    const { edit, fireGateRetry, history } = await setup(true);
    await flushPromises();
    expect(history.canUndo.value).toBe(false);

    // The gate's retry reruns the failed fresh load; the next write then runs.
    fireGateRetry();
    await flushPromises();

    edit("one", true);
    await history.flush(false);

    expect(apiMocks.getExamWorkspaceHistory).toHaveBeenCalledTimes(2);
    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledOnce();
    expect(history.canUndo.value).toBe(true);
  });

  it("shows a toast only when an undo move fails", async () => {
    const { edit, history } = await setup();
    await flushPromises();
    edit("one", true);
    await history.flush(false);
    const toasts = useToastStore();
    expect(toasts.toasts).toEqual([]);
    apiMocks.moveExamWorkspaceHistoryPosition.mockRejectedValueOnce(new Error("offline"));

    await history.undo();

    expect(toasts.toasts.map((toast) => toast.message)).toEqual([
      "Det gick inte att ångra. Försök igen.",
    ]);
  });

  it("shows no toast when the server rejects a draft the editor already explains inline", async () => {
    const { history, workspaceDocument } = await setup();
    await flushPromises();
    const document = workspaceDocument.value!;
    workspaceDocument.value = {
      ...document,
      items: document.items.map((item, index) => (index === 0 ? { ...item, points: -1 } : item)),
    };
    apiMocks.storeExamWorkspaceUndoStep.mockRejectedValueOnce(validationError());

    history.noteEdit(true);
    await history.flush(false);

    expect(useToastStore().toasts).toEqual([]);
  });

  it("states a rejected autosave in Swedish, never the server's English shape error", async () => {
    const { edit, history } = await setup();
    await flushPromises();
    apiMocks.storeExamWorkspaceUndoStep.mockRejectedValueOnce(validationError());

    edit("one", true);
    await history.flush(false);

    expect(useToastStore().toasts.map((toast) => toast.message)).toEqual([
      "Ändringarna kunde inte sparas. Vi försöker igen automatiskt.",
    ]);
  });

  it("reports a DataCloneError autosave failure as a toast and keeps the edit owed", async () => {
    const shared: ExamWorkspaceSharedStore = {
      ...serverExamWorkspaceStore.shared,
      storeExamWorkspaceUndoStep: vi.fn<ExamWorkspaceSharedStore["storeExamWorkspaceUndoStep"]>(),
    };
    vi.mocked(shared.storeExamWorkspaceUndoStep).mockRejectedValueOnce(
      new DOMException("#<Object> could not be cloned.", "DataCloneError"),
    );
    vi.mocked(shared.storeExamWorkspaceUndoStep).mockImplementation((...args) =>
      serverExamWorkspaceStore.shared.storeExamWorkspaceUndoStep(...args),
    );
    const { edit, history } = await setup(false, { shared });
    await flushPromises();
    apiMocks.storeExamWorkspaceUndoStep.mockClear();

    edit("one", true);
    await flushPromises();

    expect(useToastStore().toasts.map((toast) => toast.message)).toEqual([
      "Ändringarna kunde inte sparas. Vi försöker igen automatiskt.",
    ]);

    await expect(history.flush(false)).resolves.toBe(true);
    expect(apiMocks.storeExamWorkspaceUndoStep.mock.calls.at(-1)?.[1].document.title).toBe(
      "one",
    );
  });
});
