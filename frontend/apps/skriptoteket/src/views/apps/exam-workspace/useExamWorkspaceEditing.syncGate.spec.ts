/**
 * Exam workspace editing session: the sync gate fail-first ports (TASK-SKRIPT-40-04-14, G1b).
 *
 * Ported from rereview-3 probes T1 and T2 against the public editing API.
 * Fixed behavior: after a failed resync the session is loading, structural
 * edits are refused at entry (no owed snapshot, no store), and a clean-exam
 * save during loading settles at once without awaiting any read.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import type { ExamWorkspaceEditLeaseResponse } from "../../../api/examWorkspace";
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
vi.mock("../../../composables/useToast", () => ({ useToast: () => toast }));

beforeEach(() => {
  for (const fn of [...Object.values(api), ...Object.values(toast)]) fn.mockReset();
});

afterEach(() => {
  stopScopes();
  vi.useRealTimers();
});

function heldError(): ApiError {
  return new ApiError({ code: "EDIT_LEASE_HELD", status: 409, message: "held" });
}

function leaseResponse(holder: string | null): ExamWorkspaceEditLeaseResponse {
  return {
    holder_tab_id: holder,
    renewed_at: "2026-10-19T12:00:00Z",
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

function pointsOf(document: { items: Array<{ item_id: string; points: number | null }> }, itemId: string): number | null {
  const found = document.items.find((item) => item.item_id === itemId);
  if (found === undefined) {
    throw new Error(`expected ${itemId}`);
  }
  return found.points;
}

async function refusedFixture(owner: { holder: string }) {
  const base = exam();
  const server = fakeServer(api, base);
  const editing = inScope(() =>
    useExamWorkspaceEditing(serverExamWorkspaceStore, {
      server: {
        claim: async () => {
          if (owner.holder !== "A") throw heldError();
          return leaseResponse("A");
        },
        release: async () => leaseResponse(owner.holder),
        renew: async () => {
          if (owner.holder !== "A") throw heldError();
          return leaseResponse("A");
        },
        requestTakeover: async () => leaseResponse("B"),
      },
      tabId: "A",
    }),
  );
  editing.applyCommandResponse(response(base, "step-0"));
  await flushPromises();
  editing.updateItemPoints("item_001", 5);
  await editing.save();
  owner.holder = "B";
  api.storeExamWorkspaceUndoStep.mockRejectedValueOnce(heldError());
  editing.updateItemPoints("item_001", 7);
  await editing.save();
  const saved = server.documents.get(server.state.cursor);
  if (saved === undefined) {
    throw new Error("expected the stored step");
  }
  const newest = {
    ...saved,
    items: saved.items.map((item) => (item.item_id === "item_002" ? { ...item, points: 9 } : item)),
  };
  server.documents.set("step-B", newest);
  server.state.steps.push("step-B");
  server.state.cursor = "step-B";
  server.state.position = "step-B";
  return { editing, server, newest };
}

describe("the sync gate fail-first ports", () => {
  it("T1: a structural edit after failed history resync is refused until the merge", async () => {
    vi.useFakeTimers();
    const owner = { holder: "A" };
    const { editing, server, newest } = await refusedFixture(owner);
    const history = api.getExamWorkspaceHistory.getMockImplementation();
    if (history === undefined) {
      throw new Error("expected the history double");
    }
    api.getExamWorkspaceDocument.mockImplementation(async () => response(JSON.parse(JSON.stringify(newest)), "step-B"));
    api.getExamWorkspaceHistory.mockRejectedValue(new Error("history unavailable"));
    owner.holder = "A";
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
    const workspace = editing.workspaceDocument.value;
    if (workspace === null) {
      throw new Error("expected an open document");
    }
    expect(pointsOf(workspace, "item_001")).toBe(7);

    const stores = api.storeExamWorkspaceUndoStep.mock.calls.length;
    editing.structure.addItem("free_text");
    await flushPromises();
    const refused = editing.workspaceDocument.value;
    if (refused === null) {
      throw new Error("expected an open document");
    }
    expect(refused.items.length).toBe(2);
    expect(api.storeExamWorkspaceUndoStep.mock.calls.length).toBe(stores);
    expect(editing.editingLocked.value).toBe(true);

    api.getExamWorkspaceHistory.mockImplementation(history);
    for (let attempt = 0; attempt < 20; attempt += 1) {
      const mergedPoints = editing.workspaceDocument.value?.items.map((item) => item.points);
        if (mergedPoints !== undefined && mergedPoints[0] === 7 && mergedPoints[1] === 9) {
        break;
      }
        await vi.advanceTimersByTimeAsync(1000);
        await flushPromises();
      }
    await flushPromises();
    const merged = editing.workspaceDocument.value;
    if (merged === null) {
      throw new Error("expected an open document");
    }
    expect(merged.items.map((item) => item.points)).toEqual([7, 9]);
    const stored = server.documents.get(server.state.cursor);
    if (stored === undefined) {
      throw new Error("expected the merged store");
    }
    expect(stored.items.map((item) => item.points)).toEqual([7, 9]);

    editing.structure.addItem("free_text");
    await editing.save();
    await flushPromises();
    const after = editing.workspaceDocument.value;
    if (after === null) {
      throw new Error("expected an open document");
    }
    const final = server.documents.get(server.state.cursor);
    if (final === undefined) {
      throw new Error("expected the final store");
    }
    expect({
      count: after.items.length,
      points: ["item_001", "item_002"].map(
        (id) => after.items.find((item) => item.item_id === id)?.points,
      ),
      storedCount: final.items.length,
      storedPoints: ["item_001", "item_002"].map(
        (id) => final.items.find((item) => item.item_id === id)?.points,
      ),
    }).toEqual({ count: 3, points: [7, 9], storedCount: 3, storedPoints: [7, 9] });
  });

  it("T2: an abandoned joined history load never blocks saves in the next exam", async () => {
    const oldHistory = deferred<{
      baseline_step_id: string;
      cursor: string;
      position_step_id: string;
      step_ids: string[];
    }>();
    const lineageA = "00000000-0000-4000-8000-000000000001";
    const lineageB = "00000000-0000-4000-8000-000000000002";
    const first = exam();
    const server = fakeServer(api, first);
    api.getExamWorkspaceHistory.mockImplementation((id: string) =>
      id === lineageA
        ? oldHistory.promise
        : Promise.resolve({ baseline_step_id: "step-0", cursor: "step-0", position_step_id: "step-0", step_ids: [] }),
    );
    const editing = inScope(() =>
      useExamWorkspaceEditing(serverExamWorkspaceStore, {
        server: {
          claim: async () => leaseResponse("A"),
          release: async () => leaseResponse("A"),
          renew: async () => leaseResponse("A"),
          requestTakeover: async () => leaseResponse("A"),
        },
        tabId: "A",
      }),
    );
    editing.applyCommandResponse(response(first, "step-0"));
    await flushPromises();
    expect(editing.isDirty.value).toBe(false);
    let firstSettled = false;
    const savingA = editing.save().then(() => {
      firstSettled = true;
    });
    await flushPromises();
    expect(editing.isBusy.value).toBe(false);
    expect(editing.history.saveStatus.value.state).toBe("saved");
    const second = { ...exam("Second exam"), document_id: lineageB };
    const secondResponse = response(second, "step-0");
    secondResponse.summary = { ...secondResponse.summary, lineage_id: lineageB, vault_file_id: lineageB };
    api.getExamWorkspaceDocument.mockImplementation(async () => secondResponse);
    expect(await editing.openDocument(lineageB)).toBe(true);
    await flushPromises();
    expect(editing.history.position.value).toBe("step-0");
    // The lineage switch re-claims the lease asynchronously; the drawer
    // briefly shows readonly until the claim resolves and the gate edits.
    for (let attempt = 0; attempt < 50 && editing.editingLocked.value; attempt += 1) {
      await flushPromises();
    }
    expect(editing.editingLocked.value).toBe(false);
    editing.updateItemPoints("item_001", 8);
    let secondSettled = false;
    const savingB = editing.save().then(() => {
      secondSettled = true;
    });
    await flushPromises();
    await flushPromises();
    const beforeOldAnswer = {
      firstSettled,
      secondSettled,
      newExamStores: api.storeExamWorkspaceUndoStep.mock.calls.filter(([id]) => id === lineageB).length,
    };
    oldHistory.resolve({ baseline_step_id: "step-0", cursor: "step-0", position_step_id: "step-0", step_ids: [] });
    await savingA;
    await savingB;
    expect(beforeOldAnswer).toEqual({ firstSettled: true, secondSettled: true, newExamStores: 1 });
    void server;
  });
});
