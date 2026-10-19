/**
 * Exam workspace editing session: kept-edit recovery across the history resync
 * (TASK-SKRIPT-40-04-14, rereview R1/R2 of KE at 04ef7bee).
 *
 * Expected behavior:
 *   - R1: the document GET succeeds but the explicit history resync fails. The
 *     refused working copy stays visible and pending, and the next save
 *     recovers it: the kept base and edited snapshot merge onto the newest
 *     server document and store through the normal save path.
 *   - R2: while the history resync is still waiting, a normal edit is refused
 *     by the replacing lock. After settling, the merged refused edit stands
 *     and later edits are accepted again.
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
  return { editing, holder, server };
}

describe("a failed history resync during the takeover", () => {
  it("keeps the refused working copy visible and recovers it on the next save", async () => {
    const { editing, holder, server } = await refuseEdit();
    const saved = server.documents.get(server.state.cursor);
    if (saved === undefined) {
      throw new Error("expected tab A's stored step");
    }
    api.getExamWorkspaceDocument.mockResolvedValueOnce(
      response(JSON.parse(JSON.stringify(saved)), server.state.cursor),
    );
    api.getExamWorkspaceHistory.mockRejectedValue(new Error("history unavailable"));
    holder.current = "tab-A";
    await editing.requestTakeover();
    await flushPromises();
    await flushPromises();
    expect(workspacePoints(editing, "item_001")).toBe(7);
    expect(editing.history.pending.value).toBe(true);

    api.getExamWorkspaceHistory.mockImplementation(async () => ({
      baseline_step_id: "step-0",
      cursor: server.state.cursor,
      position_step_id: server.state.position,
      step_ids: [...server.state.steps],
    }));
    const newest = server.documents.get(server.state.cursor);
    if (newest === undefined) {
      throw new Error("expected the newest server document");
    }
    api.getExamWorkspaceDocument.mockResolvedValueOnce(
      response(JSON.parse(JSON.stringify(newest)), server.state.cursor),
    );
    api.storeExamWorkspaceUndoStep.mockRejectedValueOnce(conflict());
    // Later recoveries reread the newest server copy with a fresh object each
    // time, as the transport does (the reload-failure check is by identity).
    api.getExamWorkspaceDocument.mockImplementation(async () =>
      response(JSON.parse(JSON.stringify(newest)), server.state.cursor),
    );
    await editing.save();
    await flushPromises();
    await flushPromises();
    await flushPromises();
    await flushPromises();
    await flushPromises();
    expect(workspacePoints(editing, "item_001")).toBe(7);
    expect(pointsOf(lastStoredDocument(), "item_001")).toBe(7);
    expect(editing.history.pending.value).toBe(false);
  });
});

describe("an edit while the history resync is waiting", () => {
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
    api.getExamWorkspaceDocument.mockResolvedValueOnce(response(other, "step-B"));
    // The recovery's follow-up store runs the serialized phase again: reread
    // with a fresh object each time, as the transport does.
    api.getExamWorkspaceDocument.mockImplementation(async () =>
      response(JSON.parse(JSON.stringify(other)), "step-B"),
    );
    api.getExamWorkspaceHistory.mockImplementation(() => gate.promise);

    holder.current = "tab-A";
    const taking = editing.requestTakeover();
    await flushPromises();
    await flushPromises();
    editing.updateItemPoints("item_001", 8);
    await flushPromises();
    expect(workspacePoints(editing, "item_001")).toBe(5);

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

describe("a natural save after a failed history resync", () => {
  it("merges the kept edit onto the newest copy without a new 409", async () => {
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
    await editing.requestTakeover();
    await flushPromises();
    await flushPromises();
    expect(workspacePoints(editing, "item_001")).toBe(7);
    expect(editing.history.pending.value).toBe(true);

    api.getExamWorkspaceHistory.mockImplementation(async () => ({
      baseline_step_id: "step-0",
      cursor: server.state.cursor,
      position_step_id: server.state.position,
      step_ids: [...server.state.steps],
    }));
    await editing.save();
    await flushPromises();
    await flushPromises();
    await flushPromises();
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
