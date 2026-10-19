/**
 * Exam workspace editing session: acquiring the lease reads the newest state.
 *
 * Expected behavior (TASK-SKRIPT-40-04-14, G2 port to the sync gate):
 *   - A read-only tab with no pending edit that acquires the lease reads the
 *     newest server copy: after Ta över the working copy equals the newest
 *     server document and a GET was sent.
 *   - With a kept edit, the takeover's fresh load merges it at the merge
 *     point and stores it. A structural command's 409 after that merge
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
  ExamWorkspaceEditLeaseResponse,
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
    expect(editing.leaseReadOnly.value).toBe(true);

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

    expect(editing.leaseReadOnly.value).toBe(false);
    expect(api.getExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    const workspace = editing.workspaceDocument.value;
    if (workspace === null) {
      throw new Error("expected an open document");
    }
    expect(workspace.title).toBe("Från en annan flik");
    expect(pointsOf(workspace, "item_002")).toBe(9);
  });
});

describe("a structural command's 409 after the takeover merge", () => {
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
    expect(editing.leaseReadOnly.value).toBe(false);

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

    // The takeover's fresh load merges the kept edit at the merge point and
    // stores it, with no recovery routine.
    api.getExamWorkspaceDocument.mockImplementation(async () => {
      const newest = server.documents.get(server.state.cursor);
      if (newest === undefined) {
        throw new Error("expected the newest server document");
      }
      return response(JSON.parse(JSON.stringify(newest)), server.state.cursor);
    });

    holder.current = "tab-A";
    await editing.requestTakeover();
    for (let attempt = 0; attempt < 20 && editing.history.pending.value; attempt += 1) {
      await flushPromises();
    }
    expect(editing.history.pending.value).toBe(false);
    const merged = editing.workspaceDocument.value;
    if (merged === null) {
      throw new Error("expected an open document");
    }
    expect(merged.items.map((item) => item.points)).toEqual([7, 9]);

    // A structural command then meets a stale cursor: the gate reloads the
    // newest copy, which already holds the merged edit, and nothing is lost.
    api.changeExamWorkspaceItemType.mockRejectedValueOnce(conflict());
    await editing.structure.changeType("item_001", "single_choice");
    for (let attempt = 0; attempt < 20 && editing.editingLocked.value; attempt += 1) {
      await flushPromises();
    }

    const workspace = editing.workspaceDocument.value;
    if (workspace === null) {
      throw new Error("expected an open document");
    }
    expect(workspace.items.map((item) => item.points)).toEqual([7, 9]);
    const newest = lastStoredDocument();
    expect(newest.items.map((item) => item.points)).toEqual([7, 9]);
    expect(editing.history.pending.value).toBe(false);
  });
});
