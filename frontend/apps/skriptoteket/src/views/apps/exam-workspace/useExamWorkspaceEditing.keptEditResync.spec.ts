/**
 * Exam workspace editing session: a kept edit across a failed takeover load
 * (TASK-SKRIPT-40-04-14, G2 port of the kept-edit recovery specs to the sync
 * gate).
 *
 * Expected behavior:
 *   - When the takeover's fresh load fails, the refused working copy stays
 *     visible and pending, and no store is sent. The gate retries the load;
 *     when it succeeds, the kept edit merges onto the newest server document
 *     at the merge point and stores through the normal save path.
 *   - While the takeover load is still waiting, the session is locked: a
 *     normal edit is refused and the kept edit survives, then merges as above.
 *   - After the merge, the next natural save sends no new read.
 *
 * Transport is a named double of the server's step store plus a lease double
 * whose holder the test moves between the tabs; the composables are the
 * production ones.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import type {
  ExamWorkspaceEditLeaseResponse,
  ExamWorkspaceHistory,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import { nullRouteProjection } from "./examWorkspaceRouteProjection.specSupport";
import {
  exam,
  fakeServer,
  inScope,
  response,
  stopScopes,
} from "./useExamWorkspaceEditing.history.specSupport";

const api = vi.hoisted(() => ({
  changeExamWorkspaceItemType: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));
const toast = vi.hoisted(() => ({ failure: vi.fn(), warning: vi.fn() }));

vi.mock("../../../api/examWorkspace", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspace")>()),
  ...api,
}));
vi.mock("../../../api/examWorkspaceStructureCommands", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspaceStructureCommands")>()),
  changeExamWorkspaceItemType: api.changeExamWorkspaceItemType,
}));
vi.mock("../../../composables/useToast", () => ({ useToast: () => toast }));

beforeEach(() => {
  for (const fn of [...Object.values(api), ...Object.values(toast)]) fn.mockReset();
});

afterEach(() => {
  stopScopes();
  vi.useRealTimers();
});

function leaseHeld(): ApiError {
  return new ApiError({
    code: "EDIT_LEASE_HELD",
    message: "Provet redigeras i en annan flik.",
    status: 409,
  });
}

function leaseResponse(holder: string): ExamWorkspaceEditLeaseResponse {
  return {
    holder_tab_id: holder,
    renewed_at: "2026-10-19T12:00:00.000Z",
    takeover_requested: false,
    takeover_requested_by: null,
  };
}

function pointsOf(document: NativeExamDocument, itemId: string): number | null {
  const found = document.items.find((item) => item.item_id === itemId);
  if (found === undefined) {
    throw new Error(`expected ${itemId}`);
  }
  return found.points;
}

function workspacePoints(
  editing: ReturnType<typeof useExamWorkspaceEditing>,
  itemId: string,
): number | null {
  const workspace = editing.workspaceDocument.value;
  if (workspace === null) {
    throw new Error("expected an open document");
  }
  return pointsOf(workspace, itemId);
}

function lastStoredDocument(): NativeExamDocument {
  const calls = api.storeExamWorkspaceUndoStep.mock.calls;
  const last = calls[calls.length - 1];
  if (last === undefined) {
    throw new Error("expected a stored step");
  }
  const request: { document: NativeExamDocument } | undefined = last[1];
  if (request === undefined) {
    throw new Error("expected a store request");
  }
  return request.document;
}

function deferred<T>(): {
  promise: Promise<T>;
  resolve: (value: T) => void;
} {
  let resolveFn: ((value: T) => void) | null = null;
  const promise = new Promise<T>((resolve) => {
    resolveFn = resolve;
  });
  return {
    promise,
    resolve: (value: T) => {
      if (resolveFn !== null) {
        resolveFn(value);
      }
    },
  };
}

async function refuseEdit(): Promise<{
  editing: ReturnType<typeof useExamWorkspaceEditing>;
  holder: { current: string };
  server: ReturnType<typeof fakeServer>;
}> {
  const baseline = exam();
  const server = fakeServer(api, baseline);
  const holder = { current: "tab-A" };
  const editing = inScope(() =>
    useExamWorkspaceEditing(serverExamWorkspaceStore, nullRouteProjection(), {
      server: {
        claim: async () => {
          if (holder.current !== "tab-A") {
            throw leaseHeld();
          }
          return leaseResponse("tab-A");
        },
        release: async () => leaseResponse(holder.current),
        renew: async () => {
          if (holder.current !== "tab-A") {
            throw leaseHeld();
          }
          return leaseResponse("tab-A");
        },
        requestTakeover: async () => leaseResponse("tab-B"),
      },
      tabId: "tab-A",
    }),
  );
  editing.applyCommandResponse(response(baseline, "step-0"));
  await flushPromises();
  editing.updateItemPoints("item_001", 5);
  expect(await editing.save()).toBe(true);
  holder.current = "tab-B";
  api.storeExamWorkspaceUndoStep.mockRejectedValueOnce(leaseHeld());
  editing.updateItemPoints("item_001", 7);
  expect(await editing.save()).toBe(false);
  expect(editing.history.pending.value).toBe(true);
  return { editing, holder, server };
}

describe("a failed history read during the takeover", () => {
  it("keeps the refused working copy visible and merges it when the retry succeeds", async () => {
    vi.useFakeTimers();
    const { editing, holder, server } = await refuseEdit();
    const saved = server.documents.get(server.state.cursor);
    if (saved === undefined) {
      throw new Error("expected tab A's stored step");
    }
    const storesBefore = api.storeExamWorkspaceUndoStep.mock.calls.length;
    api.getExamWorkspaceDocument.mockImplementation(async () =>
      response(JSON.parse(JSON.stringify(saved)), server.state.cursor),
    );
    api.getExamWorkspaceHistory.mockRejectedValue(new Error("history unavailable"));
    holder.current = "tab-A";
    const taking = editing.requestTakeover();
    let taken = false;
    void taking.then(() => {
      taken = true;
    });
    for (let attempt = 0; attempt < 20 && !taken; attempt += 1) {
      await vi.advanceTimersByTimeAsync(1000);
      await flushPromises();
    }
    await taking;
    await flushPromises();
    // The load failed: the kept edit stays visible and locked, and nothing
    // was stored past the refusal. The gate (not the history's pending flag,
    // which the failed read cleared with the step list) carries the kept
    // edit across the failure: the retry below merges it.
    expect(editing.editingLocked.value).toBe(true);
    expect(workspacePoints(editing, "item_001")).toBe(7);
    expect(api.getExamWorkspaceDocument).toHaveBeenCalled();
    expect(api.storeExamWorkspaceUndoStep.mock.calls.length).toBe(storesBefore);

    api.getExamWorkspaceHistory.mockImplementation(async () => ({
      baseline_step_id: "step-0",
      cursor: server.state.cursor,
      position_step_id: server.state.position,
      step_ids: [...server.state.steps],
    }));
    // The retry's fresh load merges the kept edit at the merge point and
    // stores it, with no save needed.
    for (
      let attempt = 0;
      attempt < 20 && api.storeExamWorkspaceUndoStep.mock.calls.length === storesBefore;
      attempt += 1
    ) {
      await vi.advanceTimersByTimeAsync(1000);
      await flushPromises();
    }
    await flushPromises();
    expect(pointsOf(lastStoredDocument(), "item_001")).toBe(7);
    expect(editing.history.pending.value).toBe(false);
    // The merged store's own step-list refresh settles back to editing.
    for (let attempt = 0; attempt < 20 && editing.editingLocked.value; attempt += 1) {
      await vi.advanceTimersByTimeAsync(1000);
      await flushPromises();
    }
    expect(workspacePoints(editing, "item_001")).toBe(7);
    expect(editing.editingLocked.value).toBe(false);
  });
});

describe("an edit while the takeover load is waiting", () => {
  it("is refused and the merged refused edit survives", async () => {
    const { editing, holder, server } = await refuseEdit();
    const saved = server.documents.get(server.state.cursor);
    if (saved === undefined) {
      throw new Error("expected tab A's stored step");
    }
    const other: NativeExamDocument = {
      ...saved,
      items: saved.items.map((item) =>
        item.item_id === "item_002" ? { ...item, points: 9 } : item,
      ),
    };
    server.documents.set("step-B", other);
    server.state.steps = [...server.state.steps, "step-B"];
    server.state.cursor = "step-B";
    server.state.position = "step-B";
    const gate = deferred<ExamWorkspaceHistory>();
    api.getExamWorkspaceDocument.mockImplementation(async () =>
      response(JSON.parse(JSON.stringify(other)), "step-B"),
    );
    api.getExamWorkspaceHistory.mockImplementation(() => gate.promise);

    holder.current = "tab-A";
    const taking = editing.requestTakeover();
    await flushPromises();
    await flushPromises();
    // The session is locked while the takeover load runs: the typing is
    // refused and the kept edit stays in front of the teacher.
    expect(editing.editingLocked.value).toBe(true);
    editing.updateItemPoints("item_001", 8);
    await flushPromises();
    expect(workspacePoints(editing, "item_001")).toBe(7);
    expect(editing.history.pending.value).toBe(true);

    gate.resolve({
      baseline_step_id: "step-0",
      cursor: server.state.cursor,
      position_step_id: server.state.position,
      step_ids: [...server.state.steps],
    });
    await taking;
    await flushPromises();
    await flushPromises();
    expect(workspacePoints(editing, "item_001")).toBe(7);
    expect(workspacePoints(editing, "item_002")).toBe(9);
    expect(pointsOf(lastStoredDocument(), "item_001")).toBe(7);
    expect(editing.history.pending.value).toBe(false);

    editing.updateItemPoints("item_002", 4);
    expect(workspacePoints(editing, "item_002")).toBe(4);
  });
});

describe("a natural save after a failed takeover load", () => {
  it("merges the kept edit onto the newest copy without a new 409", async () => {
    vi.useFakeTimers();
    const { editing, holder, server } = await refuseEdit();
    const saved = server.documents.get(server.state.cursor);
    if (saved === undefined) {
      throw new Error("expected tab A's stored step");
    }
    const other: NativeExamDocument = {
      ...saved,
      items: saved.items.map((item) =>
        item.item_id === "item_002" ? { ...item, points: 9 } : item,
      ),
    };
    server.documents.set("step-B", other);
    server.state.steps = [...server.state.steps, "step-B"];
    server.state.cursor = "step-B";
    server.state.position = "step-B";

    api.getExamWorkspaceDocument.mockImplementation(async () =>
      response(JSON.parse(JSON.stringify(other)), "step-B"),
    );
    api.getExamWorkspaceHistory.mockRejectedValue(new Error("history unavailable"));
    holder.current = "tab-A";
    const taking = editing.requestTakeover();
    let taken = false;
    void taking.then(() => {
      taken = true;
    });
    for (let attempt = 0; attempt < 20 && !taken; attempt += 1) {
      await vi.advanceTimersByTimeAsync(1000);
      await flushPromises();
    }
    await taking;
    await flushPromises();
    // The load failed, so the kept edit waits in the gate for the retry.
    expect(workspacePoints(editing, "item_001")).toBe(7);
    expect(editing.editingLocked.value).toBe(true);

    api.getExamWorkspaceHistory.mockImplementation(async () => ({
      baseline_step_id: "step-0",
      cursor: server.state.cursor,
      position_step_id: server.state.position,
      step_ids: [...server.state.steps],
    }));
    // The retry's fresh load merges the kept edit at the merge point and
    // stores it; the next natural save then sends no new read.
    const storesBeforeMerge = api.storeExamWorkspaceUndoStep.mock.calls.length;
    for (
      let attempt = 0;
      attempt < 20 && api.storeExamWorkspaceUndoStep.mock.calls.length === storesBeforeMerge;
      attempt += 1
    ) {
      await vi.advanceTimersByTimeAsync(1000);
      await flushPromises();
    }
    await flushPromises();
    for (let attempt = 0; attempt < 20 && editing.editingLocked.value; attempt += 1) {
      await vi.advanceTimersByTimeAsync(1000);
      await flushPromises();
    }
    expect(editing.workspaceDocument.value?.items.map((item) => item.points)).toEqual([7, 9]);
    const stored = server.documents.get(server.state.cursor);
    if (stored === undefined) {
      throw new Error("expected the merged step");
    }
    expect(stored.items.map((item) => item.points)).toEqual([7, 9]);
    expect(editing.history.pending.value).toBe(false);

    api.getExamWorkspaceDocument.mockClear();
    editing.updateItemPoints("item_001", 8);
    await editing.save();
    await flushPromises();
    await flushPromises();
    expect(api.getExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(editing.workspaceDocument.value?.items.map((item) => item.points)).toEqual([8, 9]);
  });
});
