/**
 * Exam workspace editing session: acquiring the lease reads the newest state.
 *
 * Expected behavior (TASK-SKRIPT-40-04-14 lead review of KE, follow-up of
 * code review 23bc9c5a F1/F2):
 *   - A read-only tab with no pending edit that acquires the lease reads the
 *     newest server copy: after onAcquired the working copy equals the newest
 *     server document and a GET was sent.
 *   - A structural command's 409 after a kept refused edit has recovered
 *     reloads the newest copy, which already holds the merged edit.
 *
 * Transport is a named double of the server's step store plus a lease double
 * whose holder the test moves between the tabs; the composables are the
 * production ones.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceEditLeaseResponse,
  ExamWorkspaceHistory,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import {
  conflict,
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

function leaseServer(holder: { current: string }) {
  return {
    claim: async () => {
      if (holder.current !== "tab-A") {
        throw leaseHeld();
      }
      return leaseResponse("tab-A");
    },
    release: async () => leaseResponse(holder.current),
    renew: async () => {
      if (renewGate.fail) {
        throw new TypeError("offline");
      }
      if (holder.current !== "tab-A") {
        throw leaseHeld();
      }
      return leaseResponse("tab-A");
    },
    requestTakeover: async () => leaseResponse("tab-B"),
  };
}

const renewGate = { fail: false };

function pointsOf(document: NativeExamDocument, itemId: string): number | null {
  const found = document.items.find((item) => item.item_id === itemId);
  if (found === undefined) {
    throw new Error(`expected ${itemId}`);
  }
  return found.points;
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
  fail: (reason: unknown) => void;
} {
  let resolveFn: ((value: T) => void) | null = null;
  let failFn: ((reason: unknown) => void) | null = null;
  const promise = new Promise<T>((resolve, reject) => {
    resolveFn = resolve;
    failFn = reject;
  });
  return {
    promise,
    resolve: (value: T) => {
      if (resolveFn !== null) {
        resolveFn(value);
      }
    },
    fail: (reason: unknown) => {
      if (failFn !== null) {
        failFn(reason);
      }
    },
  };
}

describe("acquiring the lease without a pending edit", () => {
  it("reloads the newest server copy", async () => {
    const baseline = exam();
    fakeServer(api, baseline);
    const holder = { current: "tab-B" };
    const editing = inScope(() =>
      useExamWorkspaceEditing(serverExamWorkspaceStore, {
        server: leaseServer(holder),
        tabId: "tab-A",
      }),
    );
    editing.applyCommandResponse(response(baseline, "step-0"));
    await flushPromises();
    expect(editing.readOnly.value).toBe(true);

    const other: NativeExamDocument = {
      ...baseline,
      title: "Från en annan flik",
      items: baseline.items.map((item) =>
        item.item_id === "item_002" ? { ...item, points: 9 } : item,
      ),
    };
    api.getExamWorkspaceDocument.mockResolvedValueOnce(response(other, "step-B"));

    holder.current = "tab-A";
    await editing.requestTakeover();
    await flushPromises();

    expect(editing.readOnly.value).toBe(false);
    expect(api.getExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    const workspace = editing.workspaceDocument.value;
    if (workspace === null) {
      throw new Error("expected an open document");
    }
    expect(workspace.title).toBe("Från en annan flik");
    expect(pointsOf(workspace, "item_002")).toBe(9);
  });
});

describe("a structural command's 409 after a kept-edit recovery", () => {
  it("reloads the newest copy that already holds the merged edit", async () => {
    const baseline = exam();
    const server = fakeServer(api, baseline);
    const holder = { current: "tab-A" };
    const editing = inScope(() =>
      useExamWorkspaceEditing(serverExamWorkspaceStore, {
        server: leaseServer(holder),
        tabId: "tab-A",
      }),
    );
    editing.applyCommandResponse(response(baseline, "step-0"));
    await flushPromises();
    expect(editing.readOnly.value).toBe(false);

    editing.updateItemPoints("item_001", 5);
    expect(await editing.save()).toBe(true);

    holder.current = "tab-B";
    api.storeExamWorkspaceUndoStep.mockRejectedValueOnce(leaseHeld());
    editing.updateItemPoints("item_001", 7);
    expect(await editing.save()).toBe(false);
    expect(editing.history.pending.value).toBe(true);

    const storedA = server.documents.get(server.state.cursor);
    if (storedA === undefined) {
      throw new Error("expected tab A's stored step");
    }
    const storedB: NativeExamDocument = {
      ...storedA,
      items: storedA.items.map((item) =>
        item.item_id === "item_002" ? { ...item, points: 9 } : item,
      ),
    };
    server.documents.set("step-B", storedB);
    server.state.steps = [...server.state.steps, "step-B"];
    server.state.cursor = "step-B";
    server.state.position = "step-B";

    api.getExamWorkspaceDocument.mockRejectedValueOnce(new Error("reload failed"));
    holder.current = "tab-A";
    await editing.requestTakeover();
    await flushPromises();
    expect(api.getExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    const kept = editing.workspaceDocument.value;
    if (kept === null) {
      throw new Error("expected an open document");
    }
    expect(pointsOf(kept, "item_001")).toBe(7);
    expect(editing.history.pending.value).toBe(true);

    const commandGate = deferred<null>();
    api.changeExamWorkspaceItemType.mockImplementationOnce(() => commandGate.promise);
    // The document read serves the fake server's live cursor with a fresh
    // object each time, as the transport does.
    api.getExamWorkspaceDocument.mockImplementation(async () => {
      const newest = server.documents.get(server.state.cursor);
      if (newest === undefined) {
        throw new Error("expected the newest server document");
      }
      return response(JSON.parse(JSON.stringify(newest)), server.state.cursor);
    });

    const changing = editing.structure.changeType("item_001", "single_choice");
    await flushPromises();
    await flushPromises();
    await flushPromises();
    expect(api.changeExamWorkspaceItemType).toHaveBeenCalledTimes(1);

    // The flush already recovered the kept edit onto the newest copy and
    // stored it, so the command's 409 finds nothing left to recover and
    // reloads the newest copy that already holds the merged edit.
    commandGate.fail(conflict());
    await changing;
    await flushPromises();
    await flushPromises();
    await flushPromises();
    await flushPromises();

    const workspace = editing.workspaceDocument.value;
    if (workspace === null) {
      throw new Error("expected an open document");
    }
    expect(pointsOf(workspace, "item_001")).toBe(7);
    expect(pointsOf(workspace, "item_002")).toBe(9);
    const newest = lastStoredDocument();
    expect(pointsOf(newest, "item_001")).toBe(7);
    expect(pointsOf(newest, "item_002")).toBe(9);
    expect(editing.history.pending.value).toBe(false);
  });
});

describe("a heartbeat reclaim during a kept-edit recovery", () => {
  it("serializes the reclaim flush after the single recovery and keeps a later edit", async () => {
    vi.useFakeTimers();
    renewGate.fail = false;
    const baseline = exam();
    const server = fakeServer(api, baseline);
    const holder = { current: "tab-A" };
    const editing = inScope(() =>
      useExamWorkspaceEditing(serverExamWorkspaceStore, {
        server: leaseServer(holder),
        tabId: "tab-A",
      }),
    );
    editing.applyCommandResponse(response(baseline, "step-0"));
    await flushPromises();
    expect(editing.readOnly.value).toBe(false);

    editing.updateItemPoints("item_001", 5);
    expect(await editing.save()).toBe(true);

    holder.current = "tab-B";
    api.storeExamWorkspaceUndoStep.mockRejectedValueOnce(leaseHeld());
    editing.updateItemPoints("item_001", 7);
    expect(await editing.save()).toBe(false);
    expect(editing.history.pending.value).toBe(true);

    const storedA = server.documents.get(server.state.cursor);
    if (storedA === undefined) {
      throw new Error("expected tab A's stored step");
    }
    const other: NativeExamDocument = {
      ...storedA,
      items: storedA.items.map((item) =>
        item.item_id === "item_002" ? { ...item, points: 9 } : item,
      ),
    };
    server.documents.set("step-B", other);
    server.state.steps = [...server.state.steps, "step-B"];
    server.state.cursor = "step-B";
    server.state.position = "step-B";

    api.getExamWorkspaceDocument.mockRejectedValueOnce(new Error("reload failed"));
    holder.current = "tab-A";
    await editing.requestTakeover();
    await flushPromises();
    expect(editing.history.pending.value).toBe(true);

    // Gate the single recovery's reads: the history store owns the only
    // recovery phase, so the reclaim below only queues another flush behind
    // it instead of starting a second concurrent recovery.
    const firstDocument = deferred<ExamWorkspaceDocumentResponse>();
    const firstHistory = deferred<ExamWorkspaceHistory>();
    let documentGets = 0;
    let historyGets = 0;
    api.getExamWorkspaceDocument.mockClear();
    api.getExamWorkspaceHistory.mockClear();
    api.storeExamWorkspaceUndoStep.mockClear();
    api.getExamWorkspaceDocument.mockImplementation(() => {
      documentGets += 1;
      return firstDocument.promise;
    });
    api.getExamWorkspaceHistory.mockImplementation(() => {
      historyGets += 1;
      return firstHistory.promise;
    });

    // The stale cursor starts a save recovery; its document GET stays pending.
    const saving = editing.save();
    await flushPromises();
    expect(documentGets).toBe(1);
    firstDocument.resolve(response(JSON.parse(JSON.stringify(other)), "step-B"));
    for (let attempt = 0; attempt < 20 && historyGets < 1; attempt += 1) {
      await flushPromises();
    }
    // One history read: the recovery's resync shares its in-flight read with
    // the history watcher's reload follow-up for the fresh cursor; no second
    // recovery phase reads.
    expect(historyGets).toBe(1);

    // (a) While the recovery's history read is pending, the replacing lock
    // refuses typing: the standing value is unchanged.
    expect(editing.isReplacing.value).toBe(true);
    const workspaceBefore = editing.workspaceDocument.value;
    if (workspaceBefore === null) {
      throw new Error("expected an open document");
    }
    const standing = pointsOf(workspaceBefore, "item_001");
    editing.updateItemPoints("item_001", 8);
    await flushPromises();
    const refusedWorkspace = editing.workspaceDocument.value;
    if (refusedWorkspace === null) {
      throw new Error("expected an open document");
    }
    expect(pointsOf(refusedWorkspace, "item_001")).toBe(standing);
    expect(editing.isReplacing.value).toBe(true);

    // Renewals fail, so the lease expires locally at 15 s; the 20 s heartbeat
    // self-claims the free lease and queues its flush behind the running one.
    renewGate.fail = true;
    await vi.advanceTimersByTimeAsync(20000);
    await flushPromises();
    // (b) No second concurrent recovery phase started: still one document GET
    // and the same single history read, and the lock never released meanwhile.
    expect(documentGets).toBe(1);
    expect(historyGets).toBe(1);
    expect(editing.isReplacing.value).toBe(true);

    firstHistory.resolve({
      baseline_step_id: "step-0",
      cursor: server.state.cursor,
      position_step_id: server.state.position,
      step_ids: [...server.state.steps],
    });
    expect(await saving).toBe(true);
    for (let attempt = 0; attempt < 20; attempt += 1) {
      await flushPromises();
    }
    // The reclaim's flush ran after the recovery and its merged store without
    // any further reads: the queued flush found nothing left to recover.
    const storeOrder = api.storeExamWorkspaceUndoStep.mock.invocationCallOrder[0];
    if (storeOrder === undefined) {
      throw new Error("expected the merged store");
    }
    const documentGetsBeforeStore =
      api.getExamWorkspaceDocument.mock.invocationCallOrder.filter(
        (order) => order < storeOrder,
      );
    const historyGetsBeforeStore =
      api.getExamWorkspaceHistory.mock.invocationCallOrder.filter(
        (order) => order < storeOrder,
      );
    expect(documentGetsBeforeStore).toHaveLength(1);
    expect(historyGetsBeforeStore).toHaveLength(1);
    // The queued reclaim flush stored nothing of its own: one merged store.
    expect(api.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(1);
    expect(editing.isReplacing.value).toBe(false);
    const merged = editing.workspaceDocument.value;
    if (merged === null) {
      throw new Error("expected an open document");
    }
    expect(merged.items.map((item) => item.points)).toEqual([7, 9]);
    expect(editing.history.pending.value).toBe(false);

    // (c) An edit accepted after the recovery settles is stored and never
    // replaced by the older refused snapshot.
    editing.updateItemPoints("item_001", 8);
    const edited = editing.workspaceDocument.value;
    if (edited === null) {
      throw new Error("expected an open document");
    }
    expect(pointsOf(edited, "item_001")).toBe(8);
    expect(await editing.save()).toBe(true);
    await flushPromises();
    const finalWorkspace = editing.workspaceDocument.value;
    if (finalWorkspace === null) {
      throw new Error("expected an open document");
    }
    expect(finalWorkspace.items.map((item) => item.points)).toEqual([8, 9]);
    const storedFinal = server.documents.get(server.state.cursor);
    if (storedFinal === undefined) {
      throw new Error("expected the stored step");
    }
    expect(storedFinal.items.map((item) => item.points)).toEqual([8, 9]);
    renewGate.fail = false;
  });
});
