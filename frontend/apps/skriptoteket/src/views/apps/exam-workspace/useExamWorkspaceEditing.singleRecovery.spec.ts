/**
 * Exam workspace editing session: acquiring with a kept edit recovers once.
 *
 * Expected behavior (TASK-SKRIPT-40-04, lead review RK3 of RK2 at 84a7024a):
 *   - Acquisition with a kept edit runs exactly one recovery phase: one
 *     document GET and one history GET before the store. The history store
 *     owns the recovery; the acquisition only requests the store.
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

function leaseDouble(getHolder: () => string) {
  return {
    claim: async () => {
      if (getHolder() !== "tab-A") {
        throw leaseHeld();
      }
      return leaseResponse("tab-A");
    },
    release: async () => leaseResponse(getHolder()),
    renew: async () => {
      if (getHolder() !== "tab-A") {
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

describe("acquisition with a kept edit", () => {
  it("sends exactly one document GET and one history GET before the store", async () => {
    const baseline = exam();
    const server = fakeServer(api, baseline);
    let holder = "tab-A";
    const editing = inScope(() =>
      useExamWorkspaceEditing(serverExamWorkspaceStore, nullRouteProjection(), {
        server: leaseDouble(() => holder),
        tabId: "tab-A",
      }),
    );
    editing.applyCommandResponse(response(baseline, "step-0"));
    await flushPromises();

    editing.updateItemPoints("item_001", 5);
    expect(await editing.save()).toBe(true);

    holder = "tab-B";
    api.storeExamWorkspaceUndoStep.mockRejectedValueOnce(leaseHeld());
    editing.updateItemPoints("item_001", 7);
    expect(await editing.save()).toBe(false);
    expect(editing.history.pending.value).toBe(true);

    // The other tab takes the lease but stores nothing new: the takeover GET
    // returns the same cursor and content, but in a fresh response object
    // every time, as the transport does (the reload-failure check is by
    // identity). Counts start here, so only the acquisition recovery is
    // measured.
    api.getExamWorkspaceDocument.mockClear();
    api.getExamWorkspaceHistory.mockClear();
    api.storeExamWorkspaceUndoStep.mockClear();
    api.getExamWorkspaceDocument.mockImplementation(async () => {
      const newest = server.documents.get(server.state.cursor);
      if (newest === undefined) {
        throw new Error("expected the newest server document");
      }
      return response(JSON.parse(JSON.stringify(newest)), server.state.cursor);
    });

    holder = "tab-A";
    await editing.requestTakeover();
    await flushPromises();
    await flushPromises();
    await flushPromises();

    expect(api.storeExamWorkspaceUndoStep).toHaveBeenCalled();
    const firstStoreOrder = api.storeExamWorkspaceUndoStep.mock.invocationCallOrder[0];
    if (firstStoreOrder === undefined) {
      throw new Error("expected a stored step");
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
    expect(pointsOf(workspace, "item_001")).toBe(7);
    expect(editing.history.pending.value).toBe(false);
  });
});
