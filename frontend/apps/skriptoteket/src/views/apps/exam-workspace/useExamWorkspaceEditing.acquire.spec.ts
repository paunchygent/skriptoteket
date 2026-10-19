/**
 * Exam workspace editing session: acquiring the lease reads the newest state.
 *
 * Expected behavior (TASK-SKRIPT-40-04-14 lead review of KE, follow-up of
 * code review 23bc9c5a F1/F2):
 *   - A read-only tab with no pending edit that acquires the lease reads the
 *     newest server copy: after onAcquired the working copy equals the newest
 *     server document and a GET was sent.
 *   - A structural command's 409 while a kept refused edit is recovering runs
 *     the same recovery instead of reloading past the edit: the kept edit is
 *     merged onto the newest copy and stored.
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

afterEach(stopScopes);

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
      if (holder.current !== "tab-A") {
        throw leaseHeld();
      }
      return leaseResponse("tab-A");
    },
    requestTakeover: async () => leaseResponse("tab-B"),
  };
}

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

describe("a structural command's 409 during a kept-edit recovery", () => {
  it("keeps the edit merged and stored", async () => {
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

    const firstStore = deferred<ExamWorkspaceUndoStep>();
    const secondStore = deferred<ExamWorkspaceUndoStep>();
    let commandStores = 0;
    api.storeExamWorkspaceUndoStep.mockClear();
    api.storeExamWorkspaceUndoStep.mockImplementation(
      (
        lineage: string,
        request: { afterStepId: string | null; document: NativeExamDocument; expectedCursor: string },
      ) => {
        commandStores += 1;
        if (commandStores === 1) {
          return firstStore.promise;
        }
        if (commandStores === 2) {
          return secondStore.promise;
        }
        return Promise.resolve(stored(request.document, `step-manual-${commandStores}`));
      },
    );
    api.getExamWorkspaceDocument.mockResolvedValue(response(storedB, "step-B"));
    const commandGate = deferred<null>();
    api.changeExamWorkspaceItemType.mockImplementationOnce(() => commandGate.promise);

    const changing = editing.structure.changeType("item_001", "single_choice");
    await flushPromises();
    expect(commandStores).toBe(1);

    // The flush store succeeds, but the confirmed step carries the other
    // tab's change as well, so the working copy stays pending past the
    // flush: the parked command then meets the 409 with a kept edit
    // recovering.
    const firstRequest = api.storeExamWorkspaceUndoStep.mock.calls[0];
    if (firstRequest === undefined) {
      throw new Error("expected the flush store");
    }
    const firstDocument: NativeExamDocument = firstRequest[1].document;
    const combined: NativeExamDocument = {
      ...firstDocument,
      items: firstDocument.items.map((item) =>
        item.item_id === "item_002" ? { ...item, points: 9 } : item,
      ),
    };
    firstStore.resolve(stored(combined, "step-B"));
    await flushPromises();
    await flushPromises();
    expect(api.changeExamWorkspaceItemType).toHaveBeenCalledTimes(1);

    commandGate.fail(conflict());
    await flushPromises();
    await flushPromises();

    const secondRequest = api.storeExamWorkspaceUndoStep.mock.calls[1];
    if (secondRequest === undefined) {
      throw new Error("expected the follow-up store");
    }
    const secondDocument: NativeExamDocument = secondRequest[1].document;
    secondStore.resolve(stored(secondDocument, "step-flush2"));
    await changing;
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
