/**
 * Exam workspace save status when a tab loses the edit lease (TASK-SKRIPT-40-04-14, L1).
 *
 * Expected behavior:
 *   A store that meets 409 `EDIT_LEASE_HELD` with an unconfirmed edit leaves
 *   `Sparar …` for `Inte sparat` with the lease reason, toasts nothing,
 *   promises no retry and schedules none while the tab is read-only. After
 *   `Ta över` the status follows the edit's real outcome: a stored edit reads
 *   `Sparat HH:MM`, and opening another exam drops the kept edit so the
 *   status follows the new exam. A read-only tab with no pending edit keeps today's
 *   status. A guest tab whose store meets the guest lease's 409 shows the
 *   same state through the same branch.
 */

import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import type { NativeExamDocument } from "../../../api/examWorkspace";
import { useToastStore } from "../../../stores/toast";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import type { ExamWorkspaceSharedStore } from "./examWorkspaceStore";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import {
  installGuestStoreObjectUrls,
  setupGuestStore,
  startBlank,
} from "./examWorkspaceGuestStore.specSupport";
import { openGateHistory } from "./useExamWorkspaceEditing.history.specSupport";
import { EXAM_WORKSPACE_SAVE_RETRY_MS, LEASE_LOST_COPY } from "./useExamWorkspaceSaveStatus";

const apiMocks = vi.hoisted(() => ({
  getExamWorkspaceDocument: vi.fn(),
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

beforeEach(() => {
  setActivePinia(createPinia());
  for (const mock of Object.values(apiMocks)) mock.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("a tab that loses the lease with a pending edit", () => {
  const LEASE_LOST_REASON =
    "Ändringen sparades inte eftersom provet redigeras i den andra fliken.";

  function leaseHeldError(): ApiError {
    return new ApiError({
      code: "EDIT_LEASE_HELD",
      message: "Provet redigeras i en annan flik.",
      status: 409,
    });
  }

  async function setupLeaseLoss(
    shared: ExamWorkspaceSharedStore = serverExamWorkspaceStore.shared,
    leaseHeld = true,
  ) {
    const baseline = buildParentDocument();
    fakeServer(baseline);
    const noteLeaseLost = vi.fn();
    const fixture = await openGateHistory({
      api: apiMocks,
      baseline,
      leaseHeld,
      noteLeaseLost,
      shared,
    });
    function edit(title: string): void {
      const current = fixture.workspaceDocument.value;
      if (current === null) {
        throw new Error("expected an open exam");
      }
      fixture.workspaceDocument.value = titled(current, title);
      fixture.history.noteEdit(false);
    }
    return { ...fixture, baseline, edit, noteLeaseLost };
  }

  async function loseLeaseWithPendingEdit(): Promise<Awaited<ReturnType<typeof setupLeaseLoss>>> {
    const fixture = await setupLeaseLoss();
    await flushPromises();
    apiMocks.storeExamWorkspaceUndoStep.mockRejectedValueOnce(leaseHeldError());
    fixture.edit("one");
    await fixture.history.flush(false);
    return fixture;
  }

  it("leaves Sparar and shows Inte sparat with the lease reason, never the retry copy", async () => {
    const { history, noteLeaseLost, workspaceDocument } = await loseLeaseWithPendingEdit();

    expect(noteLeaseLost).toHaveBeenCalledOnce();
    expect(workspaceDocument.value!.title).toBe("one");
    expect(history.pending.value).toBe(true);
    expect(LEASE_LOST_COPY).toBe(LEASE_LOST_REASON);
    expect(history.saveStatus.value).toEqual({ state: "unsaved", detail: LEASE_LOST_COPY });
    expect(history.saveText.value).toBe("Inte sparat");
    // The edit was never stored, so no retry is promised: no toast, no generic copy.
    expect(useToastStore().toasts).toEqual([]);
    expect(history.saveStatus.value.detail).not.toContain("försöker igen");
  });

  it("schedules no retry while read-only after a lease loss", async () => {
    vi.useFakeTimers();
    const { history } = await loseLeaseWithPendingEdit();
    expect(history.saveStatus.value.state).toBe("unsaved");

    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_SAVE_RETRY_MS * 3);
    await flushPromises();

    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(1);
  });

  it("keeps today's status on a read-only tab with no pending edit", async () => {
    const { history } = await setupLeaseLoss(serverExamWorkspaceStore.shared, false);
    await flushPromises();

    expect(history.saveStatus.value).toEqual({ state: "saved", detail: null, savedAt: null });

    await history.flush(false);

    expect(apiMocks.storeExamWorkspaceUndoStep).not.toHaveBeenCalled();
    expect(history.saveStatus.value).toEqual({ state: "saved", detail: null, savedAt: null });
  });

  it("follows the stored edit after the tab takes over again", async () => {
    const { gate, history, leaseHeld } = await loseLeaseWithPendingEdit();
    expect(history.saveStatus.value.state).toBe("unsaved");

    // Ta över: the gate's fresh load runs, then the pending edit stores.
    leaseHeld.value = true;
    gate.leaseAcquired();
    await flushPromises();
    await history.flush(false);

    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(2);
    expect(history.saveStatus.value.state).toBe("saved");
    expect(history.saveText.value).toMatch(/^Sparat \d{2}:\d{2}$/);
  });

  it("drops the kept edit when another exam opens and follows the new exam", async () => {
    const { baseline, gate, history, workspaceDocument } = await loseLeaseWithPendingEdit();
    expect(history.saveStatus.value).toEqual({ state: "unsaved", detail: LEASE_LOST_COPY });

    // The teacher opens another exam: the gate drops the kept edit, the
    // fresh load installs the new exam, and the status stops pinning
    // `Inte sparat` and follows the new exam instead.
    gate.openExam("lineage-2", false);
    await flushPromises();

    expect(gate.hasKeptEdit.value).toBe(false);
    expect(workspaceDocument.value).toEqual(baseline);
    expect(history.pending.value).toBe(false);
    expect(history.saveStatus.value.state).toBe("saved");
    expect(history.saveText.value).toMatch(/^Sparat/);
  });

  it("shows the same state when a guest tab loses the lease with a pending edit", async () => {
    installGuestStoreObjectUrls();
    const context = setupGuestStore();
    const lineageId = await startBlank(context, "Original");
    await context.leaseStorage.claim("tab-holder", Date.now());
    const shared = context.store.store.shared;
    const opened = await shared.getExamWorkspaceDocument(lineageId);
    const noteLeaseLost = vi.fn();
    const fixture = await openGateHistory({
      api: apiMocks,
      baseline: opened.document,
      isGuest: true,
      lineage: lineageId,
      noteLeaseLost,
      shared,
      tabId: "tab-loser",
    });
    await flushPromises();

    const current = fixture.workspaceDocument.value;
    if (current === null) {
      throw new Error("expected an open exam");
    }
    fixture.workspaceDocument.value = titled(current, "förlorad");
    fixture.history.noteEdit(false);
    await fixture.history.flush(false);

    expect(noteLeaseLost).toHaveBeenCalledOnce();
    expect(fixture.history.pending.value).toBe(true);
    expect(fixture.history.saveStatus.value).toEqual({ state: "unsaved", detail: LEASE_LOST_COPY });
    expect(fixture.history.saveText.value).toBe("Inte sparat");
    expect(useToastStore().toasts).toEqual([]);
  });
});
