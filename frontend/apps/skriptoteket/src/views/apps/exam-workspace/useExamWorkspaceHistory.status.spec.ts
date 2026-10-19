/**
 * Exam workspace save status (TASK-SKRIPT-40-04-14, items 6 and 9).
 *
 * Expected behavior:
 *   The status is one computed value: `Sparar …` while an edit is pending
 *   or being stored, `Sparat HH:MM` once the confirmed snapshot equals the
 *   copy in front of the teacher, and `Inte sparat` with the reason when a
 *   store failed or was refused. A keystroke typed while a store is in
 *   flight stays in the copy when the response arrives, the status reads
 *   `Sparar …` until the newer copy is stored, and never `Sparat` before
 *   that. After a network or server failure the pending edit stays, the
 *   status shows `Inte sparat`, and the store is retried after 5 s and on
 *   the next edit. A refused store shows `Inte sparat` with the save rule's
 *   Swedish copy; a step that changes a placeholder still being converted
 *   shows the guard's message.
 */

import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { effectScope, ref } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import type { NativeExamDocument } from "../../../api/examWorkspace";
import { useToastStore } from "../../../stores/toast";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import { examWorkspaceSaveRefusalCopy } from "./examWorkspaceItemSaveRules";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import {
  EXAM_WORKSPACE_TYPING_PAUSE_MS,
  useExamWorkspaceHistory,
} from "./useExamWorkspaceHistory";
import { EXAM_WORKSPACE_SAVE_RETRY_MS } from "./useExamWorkspaceSaveStatus";

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

function setup(isGuest = false) {
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
      hasKeptEdit: () => false,
      noteKeptStored: () => undefined,
      recoverKeptEdit: async () => false,
      isGuest: () => isGuest,
      isReadOnly: () => false,
      isReplacing: () => false,
      replaceCopy: (run) => run(),
      lineageId: () => "lineage-1",
      noteExportBlockers: vi.fn(),
      noteLeaseLost: vi.fn(),
      noteStored: vi.fn(),
      onConflict: async () => undefined,
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

beforeEach(() => {
  setActivePinia(createPinia());
  for (const mock of Object.values(apiMocks)) mock.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("one computed save status", () => {
  it("reads Sparat without a time before the first store, Sparar while pending, Sparat HH:MM after", async () => {
    const { edit, history } = setup();
    await flushPromises();

    expect(history.saveStatus.value).toEqual({ state: "saved", detail: null, savedAt: null });

    edit("one");
    expect(history.saveStatus.value).toEqual({ state: "saving", detail: null });

    await history.flush(false);
    expect(history.saveStatus.value.state).toBe("saved");
    expect(history.saveStatus.value.detail).toMatch(/^\d{2}:\d{2}$/);
  });

  it("keeps a keystroke typed while a store is in flight, reads Sparar until the newer copy is stored", async () => {
    vi.useFakeTimers();
    const { edit, history, workspaceDocument } = setup();
    await flushPromises();
    const slowStore = apiMocks.storeExamWorkspaceUndoStep.getMockImplementation();
    if (!slowStore) {
      throw new Error("expected the step store double");
    }
    apiMocks.storeExamWorkspaceUndoStep.mockImplementation(async (...args: unknown[]) => {
      await new Promise((resolve) => setTimeout(resolve, 50));
      return slowStore(...args);
    });

    edit("one", true);
    const storing = history.flush(false);
    // The store is in flight; the teacher types the next word meanwhile.
    await vi.advanceTimersByTimeAsync(10);
    await flushPromises();
    edit("two");

    await vi.advanceTimersByTimeAsync(50);
    await flushPromises();
    // The first store confirmed snapshot "one", but the copy holds "two":
    // the keystroke survived the response and the status is not Sparat.
    expect(workspaceDocument.value!.title).toBe("two");
    expect(history.saveStatus.value).toEqual({ state: "saving", detail: null });

    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_TYPING_PAUSE_MS + 50);
    await flushPromises();
    await storing;
    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(2);
    expect(apiMocks.storeExamWorkspaceUndoStep.mock.calls[1]![1].document.title).toBe("two");
    expect(workspaceDocument.value!.title).toBe("two");
    expect(history.saveStatus.value.state).toBe("saved");
    expect(history.saveStatus.value.detail).toMatch(/^\d{2}:\d{2}$/);
  });

  it("shows Inte sparat after a failed store and retries after 5 s", async () => {
    vi.useFakeTimers();
    const { edit, history } = setup();
    await flushPromises();
    apiMocks.storeExamWorkspaceUndoStep.mockRejectedValueOnce(new Error("offline"));

    edit("one");
    await history.flush(false);

    expect(history.saveStatus.value).toEqual({
      state: "unsaved",
      detail: "Ändringarna kunde inte sparas. Vi försöker igen automatiskt.",
    });
    expect(useToastStore().toasts).toHaveLength(1);

    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_SAVE_RETRY_MS - 1);
    await flushPromises();
    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(1);
    await flushPromises();
    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(2);
    expect(history.saveStatus.value.state).toBe("saved");
    // The retry succeeds quietly: no second toast for the same outage.
    expect(useToastStore().toasts).toHaveLength(1);
  });

  it("stores at once on the next edit after a failed store", async () => {
    const { edit, history } = setup();
    await flushPromises();
    apiMocks.storeExamWorkspaceUndoStep.mockRejectedValueOnce(new Error("offline"));
    edit("one");
    await history.flush(false);
    expect(history.saveStatus.value.state).toBe("unsaved");

    edit("two");
    await flushPromises();

    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(2);
    expect(apiMocks.storeExamWorkspaceUndoStep.mock.calls[1]![1].document.title).toBe("two");
    expect(history.saveStatus.value.state).toBe("saved");
  });

  it("shows Inte sparat with the save rule's copy when the draft is refused", async () => {
    const { history, workspaceDocument } = setup();
    await flushPromises();
    const document = workspaceDocument.value!;
    const refused = {
      ...document,
      items: document.items.map((item, index) => (index === 0 ? { ...item, points: -1 } : item)),
    };
    workspaceDocument.value = refused;
    apiMocks.storeExamWorkspaceUndoStep.mockRejectedValueOnce(
      new ApiError({ code: "VALIDATION_ERROR", message: "Validation error", details: [], status: 422 }),
    );

    history.noteEdit(false);
    await history.flush(false);

    expect(history.saveStatus.value).toEqual({
      state: "unsaved",
      detail: examWorkspaceSaveRefusalCopy(refused),
    });
    expect(examWorkspaceSaveRefusalCopy(refused)).not.toBeNull();

    // A refused draft never reaches the server: no 5 s retry until the teacher edits again.
    vi.useFakeTimers();
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_SAVE_RETRY_MS + 1);
    await flushPromises();
    expect(apiMocks.storeExamWorkspaceUndoStep).not.toHaveBeenCalled();
  });

  it("shows Inte sparat with the guard's message when a placeholder step is refused", async () => {
    const message =
      "Provet kunde inte sparas. Vänta tills frågorna har konverterats innan du ändrar, flyttar eller tar bort dem.";
    const { edit, history } = setup();
    await flushPromises();
    apiMocks.storeExamWorkspaceUndoStep.mockRejectedValueOnce(
      new ApiError({
        code: "CONVERSION_IN_PROGRESS",
        message,
        details: { item_ids: ["item_001"] },
        status: 422,
      }),
    );

    edit("one");
    await history.flush(false);

    expect(history.saveStatus.value).toEqual({ state: "unsaved", detail: message });
  });

  it("reads Sparat i webbläsaren HH:MM for a guest exam and Sparat HH:MM otherwise", async () => {
    const signedIn = setup(false);
    await flushPromises();

    expect(signedIn.history.saveText.value).toBe("Sparat");

    signedIn.edit("one", true);
    await signedIn.history.flush(false);

    expect(signedIn.history.saveText.value).toMatch(/^Sparat \d{2}:\d{2}$/);

    const guest = setup(true);
    await flushPromises();

    expect(guest.history.saveText.value).toBe("Sparat i webbläsaren");

    guest.edit("one", true);
    await guest.history.flush(false);

    expect(guest.history.saveText.value).toMatch(/^Sparat i webbläsaren \d{2}:\d{2}$/);

    // Sparar … and Inte sparat stay the same for a guest exam.
    guest.edit("two");
    expect(guest.history.saveText.value).toBe("Sparar …");
  });
});
