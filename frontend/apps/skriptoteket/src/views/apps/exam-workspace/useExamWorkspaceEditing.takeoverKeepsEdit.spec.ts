/**
 * Exam workspace editing session: a refused edit survives the takeover
 * (TASK-SKRIPT-40-04-14, USER decision 2026-10-19 "Ta över keeps the edit").
 *
 * Expected behavior:
 *   Tab A types in question 1 and its store is refused with EDIT_LEASE_HELD
 *   (Inte sparat, read-only, edit kept). The other tab meanwhile stores a
 *   change to question 2. When A gets the lease back through Ta över, the
 *   refused edit is merged onto the newest server document and stored through
 *   the normal save path: the server's newest step holds A's question 1 edit
 *   and the other tab's question 2 change, and A's status reads Sparat.
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
  return last[1].document;
}

describe("a refused edit across the takeover", () => {
  it("merges the kept question 1 edit onto the other tab's question 2 change and reads Sparat", async () => {
    const baseline = exam();
    const server = fakeServer(api, baseline);
    let holder = "tab-A";
    const editing = inScope(() =>
      useExamWorkspaceEditing(serverExamWorkspaceStore, {
        server: {
          claim: async () => {
            if (holder !== "tab-A") {
              throw leaseHeld();
            }
            return leaseResponse("tab-A");
          },
          release: async () => leaseResponse(holder),
          renew: async () => {
            if (holder !== "tab-A") {
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
    expect(editing.readOnly.value).toBe(false);

    // Tab A types in question 1 and stores it.
    editing.updateItemPoints("item_001", 5);
    expect(await editing.save()).toBe(true);

    // The other tab takes the lease; A's next store is refused and kept.
    holder = "tab-B";
    api.storeExamWorkspaceUndoStep.mockRejectedValueOnce(leaseHeld());
    editing.updateItemPoints("item_001", 7);
    expect(await editing.save()).toBe(false);
    expect(editing.readOnly.value).toBe(true);
    expect(editing.history.pending.value).toBe(true);
    expect(editing.history.saveText.value).toBe("Inte sparat");

    // The other tab meanwhile stores a change to question 2.
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
    api.getExamWorkspaceDocument.mockResolvedValueOnce(response(storedB, "step-B"));

    // Tab A takes over: the kept edit merges onto the newest document.
    holder = "tab-A";
    await editing.requestTakeover();
    await flushPromises();

    expect(editing.readOnly.value).toBe(false);
    const workspace = editing.workspaceDocument.value;
    if (workspace === null) {
      throw new Error("expected an open document");
    }
    expect(pointsOf(workspace, "item_001")).toBe(7);
    expect(pointsOf(workspace, "item_002")).toBe(9);
    const newest = lastStoredDocument();
    expect(pointsOf(newest, "item_001")).toBe(7);
    expect(pointsOf(newest, "item_002")).toBe(9);
    expect(editing.history.saveText.value).toMatch(/^Sparat \d{2}:\d{2}$/);
  });
});
