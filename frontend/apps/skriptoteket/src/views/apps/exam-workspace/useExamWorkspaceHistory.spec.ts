/**
 * Exam workspace autosave and server-stored undo history.
 *
 * Expected behavior:
 *   Against a fake of the server's step store (baseline plus retained
 *   steps, `after_step_id` truncates the redo steps, the position move
 *   rotates the cursor without a new step): typing becomes one step only
 *   after the pause, a structural edit at once; undo stores the pending edit
 *   first so it can be redone; an edit after undo branches and drops the
 *   redo steps; undo and redo send the position move with the cursor and the
 *   step id instead of reading the step; a 409 from the move reloads the
 *   exam like a 409 from a store; a read that echoes an older cursor neither
 *   reloads nor breaks the next write; a failed history load is retried
 *   before the next write; a failed undo or redo move shows a toast, and a
 *   rejected autosave shows Swedish copy only when the editor does not
 *   already say why inline.
 */

import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { effectScope, ref } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import type { NativeExamDocument } from "../../../api/examWorkspace";
import { useToastStore } from "../../../stores/toast";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import { serverExamWorkspaceStore, type ExamWorkspaceSharedStore } from "./examWorkspaceStore";
import { EXAM_WORKSPACE_TYPING_PAUSE_MS, useExamWorkspaceHistory } from "./useExamWorkspaceHistory";

const apiMocks = vi.hoisted(() => ({
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));

vi.mock("../../../api/examWorkspace", () => apiMocks);

const MAX_STEPS = 10;

/** The fake server's stored step state: baseline plus retained undo steps. */
type FakeServerState = {
  baseline: string;
  steps: string[];
  cursor: string;
  position: string | null;
};

function conflict(): ApiError {
  return new ApiError({ code: "CONFLICT", message: "Dokumentet har ändrats sedan det öppnades.", status: 409 });
}

/** The server's step store: same truncation and pruning rules as exam_workspace_undo_steps.py. */
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
  apiMocks.moveExamWorkspaceHistoryPosition.mockImplementation(
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

function titled(document: NativeExamDocument, title: string): NativeExamDocument {
  return { ...document, title };
}

function setup(
  failFirstLoad = false,
  hooks: {
    isReadOnly?: () => boolean;
    isReplacing?: () => boolean;
    onLeaseLost?: () => void;
    replaceCopy?: <T>(run: () => Promise<T>) => Promise<T>;
    shared?: ExamWorkspaceSharedStore;
  } = {},
) {
  const baseline = buildParentDocument();
  const server = fakeServer(baseline);
  if (failFirstLoad) {
    apiMocks.getExamWorkspaceHistory.mockRejectedValueOnce(new Error("offline"));
  }
  const workspaceDocument = ref<NativeExamDocument | null>(baseline);
  const serverDocument = ref<NativeExamDocument | null>(baseline);
  const historyCursor = ref<string | null>("step-0");
  const onConflict = vi.fn(async () => undefined);
  const noteStored = vi.fn();
  const noteLeaseLost = vi.fn();
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
      isReadOnly: hooks.isReadOnly ?? (() => false),
      isReplacing: hooks.isReplacing ?? (() => false),
      replaceCopy: hooks.replaceCopy ?? ((run) => run()),
      lineageId: () => "lineage-1",
      noteExportBlockers: vi.fn(),
      noteLeaseLost: () => {
        noteLeaseLost();
        hooks.onLeaseLost?.();
      },
      noteStored,
      onConflict,
      savedRevision: () => baseline.revision,
      serverDocument,
      shared: hooks.shared ?? serverExamWorkspaceStore.shared,
      tabId: () => "tab-1",
      workspaceDocument,
    }),
  )!;
  function edit(title: string, structural = false): void {
    workspaceDocument.value = titled(workspaceDocument.value!, title);
    history.noteEdit(structural);
  }
  return { edit, history, historyCursor, noteLeaseLost, noteStored, onConflict, server, workspaceDocument };
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
    const { edit } = setup();
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
    const { edit, history, workspaceDocument } = setup();
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
    const { edit, history, server, workspaceDocument } = setup();
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
    const { edit, history, workspaceDocument } = setup();
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
    const { edit, history, historyCursor, server, workspaceDocument } = setup();
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
    const { edit, history, historyCursor, onConflict } = setup();
    await flushPromises();
    edit("one", true);
    await history.flush(false);
    apiMocks.getExamWorkspaceHistory.mockClear();

    historyCursor.value = "step-0";
    await flushPromises();
    edit("two", true);
    await history.flush(false);

    expect(apiMocks.getExamWorkspaceHistory).not.toHaveBeenCalled();
    expect(onConflict).not.toHaveBeenCalled();
    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(2);
  });

  it("loads the step list again when it failed before the first write", async () => {
    const { edit, history } = setup(true);
    await flushPromises();
    expect(history.canUndo.value).toBe(false);

    edit("one", true);
    await history.flush(false);

    expect(apiMocks.getExamWorkspaceHistory).toHaveBeenCalledTimes(2);
    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledOnce();
    expect(history.canUndo.value).toBe(true);
  });

  it("shows a toast only when an undo move fails", async () => {
    const { edit, history } = setup();
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

  function validationError(): ApiError {
    return new ApiError({
      code: "VALIDATION_ERROR", message: "Validation error", details: [], correlationId: null, status: 422,
    });
  }

  it("shows no toast when the server rejects a draft the editor already explains inline", async () => {
    const { history, workspaceDocument } = setup();
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
    const { edit, history } = setup();
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
    const { edit, history } = setup(false, { shared });
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

describe("undo and redo through the position move", () => {
  it("sends the move with the cursor and the step id and never reads the step", async () => {
    const { edit, history, historyCursor, workspaceDocument } = setup();
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
    const { edit, history, workspaceDocument } = setup();
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
    const { edit, history, noteStored } = setup();
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
    const { edit, history, onConflict, server } = setup();
    await flushPromises();
    edit("one", true);
    await history.flush(false);
    server.cursor = "other-tab";

    await history.undo();

    expect(onConflict).toHaveBeenCalledOnce();
    expect(useToastStore().toasts).toEqual([]);
    expect(apiMocks.getExamWorkspaceHistoryStep).not.toHaveBeenCalled();
  });

  it("stops redo on a failed move and keeps the standing step", async () => {
    const { edit, history, workspaceDocument } = setup();
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

describe("the edit lease on writes", () => {
  function leaseHeldError(): ApiError {
    return new ApiError({
      code: "EDIT_LEASE_HELD",
      message: "Provet redigeras i en annan flik.",
      status: 409,
    });
  }

  it("sends the tab id on every store", async () => {
    const { edit, history } = setup();
    await flushPromises();
    edit("one", true);
    await history.flush(false);

    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledOnce();
    expect(apiMocks.storeExamWorkspaceUndoStep.mock.calls[0]![1]).toMatchObject({ tabId: "tab-1" });
  });

  it("turns read-only on a lease-held store and keeps the pending edit, without a reload", async () => {
    const isReadOnly = ref(false);
    const { edit, history, noteLeaseLost, onConflict, workspaceDocument } = setup(false, {
      isReadOnly: () => isReadOnly.value,
      onLeaseLost: () => {
        isReadOnly.value = true;
      },
    });
    await flushPromises();
    apiMocks.storeExamWorkspaceUndoStep.mockRejectedValueOnce(leaseHeldError());
    edit("one", true);

    await history.flush(false);

    expect(noteLeaseLost).toHaveBeenCalledOnce();
    expect(onConflict).not.toHaveBeenCalled();
    expect(workspaceDocument.value!.title).toBe("one");
    expect(history.pending.value).toBe(true);
    expect(useToastStore().toasts).toEqual([]);
  });

  it("turns read-only on a lease-held move and never reads the step", async () => {
    const isReadOnly = ref(false);
    const { edit, history, noteLeaseLost, onConflict } = setup(false, {
      isReadOnly: () => isReadOnly.value,
      onLeaseLost: () => {
        isReadOnly.value = true;
      },
    });
    await flushPromises();
    edit("one", true);
    await history.flush(false);
    apiMocks.moveExamWorkspaceHistoryPosition.mockRejectedValueOnce(leaseHeldError());

    await history.undo();

    expect(noteLeaseLost).toHaveBeenCalledOnce();
    expect(onConflict).not.toHaveBeenCalled();
    expect(apiMocks.getExamWorkspaceHistoryStep).not.toHaveBeenCalled();
    expect(useToastStore().toasts).toEqual([]);
  });

  it("stops undo and redo while read-only and stores nothing", async () => {
    const isReadOnly = ref(true);
    const { edit, history, workspaceDocument } = setup(false, { isReadOnly: () => isReadOnly.value });
    await flushPromises();
    edit("one", true);
    await history.flush(false);

    expect(history.canUndo.value).toBe(false);
    expect(history.canRedo.value).toBe(false);
    expect(apiMocks.storeExamWorkspaceUndoStep).not.toHaveBeenCalled();

    await history.undo();
    expect(apiMocks.moveExamWorkspaceHistoryPosition).not.toHaveBeenCalled();
    expect(workspaceDocument.value!.title).toBe("one");
    isReadOnly.value = false;
  });
});
