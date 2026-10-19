/**
 * Exam workspace autosave history: leaving the exam under the held editing lock.
 *
 * Expected behavior:
 *   Departure resolves false without storing while another undo holds the
 *   copy; it runs the settle flush inside the replacing lock and holds the
 *   lock past the leave; a failed departure store, a leave that returns
 *   false, a leave that throws, or a scope disposed inside the leave all
 *   resolve false and release the lock.
 */

import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { effectScope, ref } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { NativeExamDocument } from "../../../api/examWorkspace";
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
      let steps = state.steps;
      if (request.afterStepId !== null) {
        const ids = [state.baseline, ...steps];
        steps = steps.slice(0, ids.indexOf(request.afterStepId));
      }
      const stepId = `step-${++counter}`;
      documents.set(stepId, request.document);
      state.steps = [...steps, stepId].slice(-10);
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

function setup(
  hooks: {
    isReplacing?: () => boolean;
    replaceCopy?: <T>(run: () => Promise<T>) => Promise<T>;
  } = {},
) {
  const baseline = buildParentDocument();
  fakeServer(baseline);
  const workspaceDocument = ref<NativeExamDocument | null>(baseline);
  const serverDocument = ref<NativeExamDocument | null>(baseline);
  const historyCursor = ref<string | null>("step-0");
  const history = effectScope().run(() =>
    useExamWorkspaceHistory({
      historyCursor,
      install: (document) => {
        workspaceDocument.value = document;
      },
      isBlocked: () => false,
      isGuest: () => false,
      isReplacing: hooks.isReplacing ?? (() => false),
      replaceCopy: hooks.replaceCopy ?? ((run) => run()),
      lineageId: () => "lineage-1",
      noteExportBlockers: vi.fn(),
      noteStored: vi.fn(),
      onConflict: async () => undefined,
      savedRevision: () => baseline.revision,
      serverDocument,
      shared: serverExamWorkspaceStore.shared,
      workspaceDocument,
    }),
  )!;
  function edit(title: string, structural = false): void {
    workspaceDocument.value = titled(workspaceDocument.value!, title);
    history.noteEdit(structural);
  }
  return { edit, history };
}

beforeEach(() => {
  setActivePinia(createPinia());
  for (const mock of Object.values(apiMocks)) mock.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("departure under the held editing lock", () => {
  it("resolves false without storing while another undo holds the copy", async () => {
    const { edit, history } = setup({ isReplacing: () => true });
    await flushPromises();
    edit("one");
    apiMocks.storeExamWorkspaceUndoStep.mockClear();
    const leave = vi.fn(async () => true);

    await expect(history.depart(leave)).resolves.toBe(false);

    expect(apiMocks.storeExamWorkspaceUndoStep).not.toHaveBeenCalled();
    expect(leave).not.toHaveBeenCalled();
  });

  it("runs the settle flush inside the replacing lock and holds it past the leave", async () => {
    const events: string[] = [];
    const { edit, history } = setup({
      replaceCopy: async <T>(run: () => Promise<T>): Promise<T> => {
        events.push("lock");
        try {
          return await run();
        } finally {
          events.push("unlock");
        }
      },
    });
    await flushPromises();
    edit("one");
    const inner = apiMocks.storeExamWorkspaceUndoStep.getMockImplementation();
    if (!inner) {
      throw new Error("expected the step store double");
    }
    apiMocks.storeExamWorkspaceUndoStep.mockImplementation(async (...args) => {
      events.push("store");
      return inner(...args);
    });

    await expect(
      history.depart(async () => true),
    ).resolves.toBe(true);
    expect(events).toEqual(["lock", "store"]);

    window.dispatchEvent(new Event("pageshow"));
    await flushPromises();
    expect(events).toEqual(["lock", "store", "unlock"]);
  });

  it("resolves false when the departure store fails", async () => {
    const { edit, history } = setup();
    await flushPromises();
    edit("one");
    apiMocks.storeExamWorkspaceUndoStep.mockRejectedValueOnce(new Error("offline"));
    const leave = vi.fn(async () => true);

    await expect(history.depart(leave)).resolves.toBe(false);

    expect(leave).not.toHaveBeenCalled();
  });

  it("resolves false and releases the lock when the leave returns false", async () => {
    const events: string[] = [];
    const { edit, history } = setup({
      replaceCopy: async <T>(run: () => Promise<T>): Promise<T> => {
        events.push("lock");
        try {
          return await run();
        } finally {
          events.push("unlock");
        }
      },
    });
    await flushPromises();
    edit("one");
    const inner = apiMocks.storeExamWorkspaceUndoStep.getMockImplementation();
    if (!inner) {
      throw new Error("expected the step store double");
    }
    apiMocks.storeExamWorkspaceUndoStep.mockImplementation(async (...args) => {
      events.push("store");
      return inner(...args);
    });

    await expect(history.depart(async () => false)).resolves.toBe(false);

    expect(events).toEqual(["lock", "store", "unlock"]);
  });

  it("resolves false and releases the lock when the leave throws", async () => {
    const { edit, history } = setup();
    await flushPromises();
    edit("one");

    await expect(
      history.depart(async () => {
        throw new Error("navigation unavailable");
      }),
    ).resolves.toBe(false);
  });

  it("resolves false without holding when the scope is disposed inside leave", async () => {
    const baseline = buildParentDocument();
    fakeServer(baseline);
    const workspaceDocument = ref<NativeExamDocument | null>(baseline);
    const serverDocument = ref<NativeExamDocument | null>(baseline);
    const historyCursor = ref<string | null>("step-0");
    const events: string[] = [];
    const addSpy = vi.spyOn(window, "addEventListener");
    try {
      const scope = effectScope();
      const history = scope.run(() =>
        useExamWorkspaceHistory({
          historyCursor,
          install: (document) => {
            workspaceDocument.value = document;
          },
          isBlocked: () => false,
          isGuest: () => false,
          isReplacing: () => false,
          replaceCopy: async <T>(run: () => Promise<T>): Promise<T> => {
            events.push("lock");
            try {
              return await run();
            } finally {
              events.push("unlock");
            }
          },
          lineageId: () => "lineage-1",
          noteExportBlockers: vi.fn(),
          noteStored: vi.fn(),
          onConflict: async () => undefined,
          savedRevision: () => baseline.revision,
          serverDocument,
          shared: serverExamWorkspaceStore.shared,
          workspaceDocument,
        }),
      )!;
      await flushPromises();
      workspaceDocument.value = titled(workspaceDocument.value!, "one");

      addSpy.mockClear();
      await expect(
        history.depart(async () => {
          scope.stop();
          return true;
        }),
      ).resolves.toBe(false);

      expect(addSpy.mock.calls.some(([name]) => name === "pageshow")).toBe(false);
      expect(events).toEqual(["lock", "unlock"]);
    } finally {
      addSpy.mockRestore();
      window.dispatchEvent(new Event("pageshow"));
      await flushPromises();
    }
  });
});
