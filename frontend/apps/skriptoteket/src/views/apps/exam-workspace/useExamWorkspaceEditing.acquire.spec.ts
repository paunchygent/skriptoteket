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
  ExamWorkspaceUndoStep,
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

function stored(document: NativeExamDocument, cursor: string): ExamWorkspaceUndoStep {
  return {
    document,
    export_blockers: [],
    history: {
      baseline_step_id: "step-0",
      cursor,
      position_step_id: cursor,
      step_ids: [cursor],
    },
  };
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

describe("two overlapping kept-edit recoveries", () => {
  it("keeps the replacing lock until the second recovery's history read settles", async () => {
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

    const firstDocument = deferred<ExamWorkspaceDocumentResponse>();
    const secondDocument = deferred<ExamWorkspaceDocumentResponse>();
    const firstHistory = deferred<ExamWorkspaceHistory>();
    const secondHistory = deferred<ExamWorkspaceHistory>();
    const mergedStore = deferred<ExamWorkspaceUndoStep>();
    let gets = 0;
    let historyReads = 0;
    api.getExamWorkspaceDocument.mockImplementation(async () => {
      gets += 1;
      if (gets === 1) {
        return firstDocument.promise;
      }
      return secondDocument.promise;
    });
    api.getExamWorkspaceHistory.mockImplementation(() => {
      // The first two loads belong to the first recovery's resync and the
      // history watcher's reload follow-up; the second recovery's resync is
      // the third, whatever order the first two land in.
      historyReads += 1;
      if (historyReads <= 2) {
        return firstHistory.promise;
      }
      return secondHistory.promise;
    });

    const saving = editing.save();
    await flushPromises();
    expect(editing.isReplacing.value).toBe(true);

    renewGate.fail = true;
    await vi.advanceTimersByTimeAsync(20000);
    for (let attempt = 0; attempt < 20 && gets < 2; attempt += 1) {
      await flushPromises();
    }

    firstDocument.resolve(response(JSON.parse(JSON.stringify(other)), "step-B"));
    for (let attempt = 0; attempt < 10 && historyReads < 1; attempt += 1) {
      await flushPromises();
    }
    firstHistory.resolve({
      baseline_step_id: "step-0",
      cursor: server.state.cursor,
      position_step_id: server.state.position,
      step_ids: [...server.state.steps],
    });
    api.storeExamWorkspaceUndoStep.mockImplementationOnce(() => mergedStore.promise);
    for (let attempt = 0; attempt < 10; attempt += 1) {
      await flushPromises();
    }
    secondDocument.resolve(response(JSON.parse(JSON.stringify(other)), "step-B"));
    for (let attempt = 0; attempt < 20 && historyReads < 3; attempt += 1) {
      await flushPromises();
    }

    const duringSecond = { locked: editing.isReplacing.value, editable: !editing.readOnly.value };
    const standing = editing.workspaceDocument.value?.items.find((item) => item.item_id === "item_001")?.points;
    editing.updateItemPoints("item_001", 8);
    const workspace = editing.workspaceDocument.value;
    if (workspace === null) {
      throw new Error("expected an open document");
    }
    const typed = workspace.items.find((item) => item.item_id === "item_001")?.points;

    const storedCalls = api.storeExamWorkspaceUndoStep.mock.calls;
    const firstStoreCall = storedCalls[storedCalls.length - 1];
    if (firstStoreCall === undefined) {
      throw new Error("expected the merged store");
    }
    const firstStoreRequest: { document: NativeExamDocument } = firstStoreCall[1];
    // Answer the parked merged store with the still-current cursor: the fake
    // server never advanced, so inventing a new cursor would desynchronize
    // the follow-up store from it.
    mergedStore.resolve(stored(firstStoreRequest.document, server.state.cursor));
    secondHistory.resolve({
      baseline_step_id: "step-0",
      cursor: server.state.cursor,
      position_step_id: server.state.position,
      step_ids: [...server.state.steps],
    });
    for (let attempt = 0; attempt < 20; attempt += 1) {
      await flushPromises();
    }
    const finalWorkspace = editing.workspaceDocument.value;
    if (finalWorkspace === null) {
      throw new Error("expected an open document");
    }
    expect(duringSecond).toEqual({ locked: true, editable: true });
    // The second recovery reloaded the newest copy before merging, and the
    // write attempted meanwhile was refused: the standing value is unchanged.
    expect(typed).toBe(standing);
    expect(typed).not.toBe(8);
    expect(await saving).toBe(true);
    expect(finalWorkspace.items.map((item) => item.points)).toEqual([7, 9]);
    expect(editing.history.pending.value).toBe(false);
    renewGate.fail = false;
  });
});
