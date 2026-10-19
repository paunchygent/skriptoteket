/**
 * Exam workspace editing session: the kept-edit recovery shares its history
 * resync with the watcher's follow-up load (TASK-SKRIPT-40-04-14, lead review
 * RK5 of RK4 at 1001aad6).
 *
 * Expected behavior:
 *   - When the history watcher's load starts after the recovery's explicit
 *     resync for the same lineage and server document, the two share one
 *     history GET and the recovery still merges the kept edit and stores it:
 *     exactly one document GET and one history GET before the merged store,
 *     with no fall-back to the refused copy.
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
} from "../../../api/examWorkspace";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
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

describe("the history watcher's load starting after the recovery's resync", () => {
  it("shares one history GET and the recovery still merges and stores", async () => {
    const baseline = exam();
    const server = fakeServer(api, baseline);
    const holder = { current: "tab-A" };
    const editing = inScope(() =>
      useExamWorkspaceEditing(serverExamWorkspaceStore, {
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

    api.getExamWorkspaceDocument.mockClear();
    api.getExamWorkspaceHistory.mockClear();
    api.storeExamWorkspaceUndoStep.mockClear();
    const documentGate = deferred<ExamWorkspaceDocumentResponse>();
    const historyGate = deferred<ExamWorkspaceHistory>();
    let documentGets = 0;
    let historyGets = 0;
    api.getExamWorkspaceDocument.mockImplementation(() => {
      documentGets += 1;
      return documentGate.promise;
    });
    api.getExamWorkspaceHistory.mockImplementation(() => {
      historyGets += 1;
      return historyGate.promise;
    });

    holder.current = "tab-A";
    const taking = editing.requestTakeover();
    for (let attempt = 0; attempt < 20 && documentGets < 1; attempt += 1) {
      await flushPromises();
    }
    expect(documentGets).toBe(1);
    const stored = server.documents.get(server.state.cursor);
    if (stored === undefined) {
      throw new Error("expected the stored step");
    }
    // The reload answers with the same cursor, so it replaces the copy
    // without tripping the history watcher's follow-up load on its own.
    documentGate.resolve(
      response(
        { ...stored, items: stored.items.map((item) => ({ ...item })) },
        server.state.cursor,
      ),
    );
    for (let attempt = 0; attempt < 20 && historyGets < 1; attempt += 1) {
      await flushPromises();
    }
    expect(historyGets).toBe(1);

    // The watcher's follow-up load starts after the recovery's explicit
    // resync, for the same lineage and server document. The store below
    // reads this cursor, so the double's cursor follows it.
    server.state.cursor = "cursor-new";
    editing.historyCursor.value = "cursor-new";
    for (let attempt = 0; attempt < 10; attempt += 1) {
      await flushPromises();
    }
    // Joined with the in-flight resync: no second history GET.
    expect(historyGets).toBe(1);

    historyGate.resolve({
      baseline_step_id: "step-0",
      cursor: "cursor-new",
      position_step_id: server.state.position,
      step_ids: [...server.state.steps],
    });
    await taking;
    for (let attempt = 0; attempt < 20; attempt += 1) {
      await flushPromises();
    }

    expect(api.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(1);
    const firstStoreOrder = api.storeExamWorkspaceUndoStep.mock.invocationCallOrder[0];
    if (firstStoreOrder === undefined) {
      throw new Error("expected the merged store");
    }
    const documentGetsBeforeStore =
      api.getExamWorkspaceDocument.mock.invocationCallOrder.filter(
        (order) => order < firstStoreOrder,
      );
    const historyGetsBeforeStore =
      api.getExamWorkspaceHistory.mock.invocationCallOrder.filter(
        (order) => order < firstStoreOrder,
      );
    expect(documentGetsBeforeStore).toHaveLength(1);
    expect(historyGetsBeforeStore).toHaveLength(1);
    const workspace = editing.workspaceDocument.value;
    if (workspace === null) {
      throw new Error("expected an open document");
    }
    expect(workspace.items.map((item) => item.points)).toEqual([7, 2]);
    expect(editing.history.pending.value).toBe(false);
  });
});
