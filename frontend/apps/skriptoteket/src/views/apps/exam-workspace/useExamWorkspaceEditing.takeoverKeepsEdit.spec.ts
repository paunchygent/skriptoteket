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
  ExamWorkspaceDocumentResponse,
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
      useExamWorkspaceEditing(serverExamWorkspaceStore, nullRouteProjection(), {
        server: leaseDouble(() => holder),
        tabId: "tab-A",
      }),
    );
    editing.applyCommandResponse(response(baseline, "step-0"));
    await flushPromises();
    expect(editing.leaseReadOnly.value).toBe(false);

    // Tab A types in question 1 and stores it.
    editing.updateItemPoints("item_001", 5);
    expect(await editing.save()).toBe(true);

    // The other tab takes the lease; A's next store is refused and kept.
    holder = "tab-B";
    api.storeExamWorkspaceUndoStep.mockRejectedValueOnce(leaseHeld());
    editing.updateItemPoints("item_001", 7);
    expect(await editing.save()).toBe(false);
    expect(editing.leaseReadOnly.value).toBe(true);
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
    // The recovery's follow-up store runs the serialized phase again: serve
    // the live server cursor with a fresh object each time, as the transport
    // does (the reload-failure check is by identity).
    api.getExamWorkspaceDocument.mockImplementation(async () => {
      const newest = server.documents.get(server.state.cursor);
      if (newest === undefined) {
        throw new Error("expected the newest server document");
      }
      return response(JSON.parse(JSON.stringify(newest)), server.state.cursor);
    });

    // Tab A takes over: the kept edit merges onto the newest document.
    holder = "tab-A";
    await editing.requestTakeover();
    await flushPromises();

    expect(editing.leaseReadOnly.value).toBe(false);
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

  it("settles without merging when the takeover reload fails", { timeout: 5000 }, async () => {
    const baseline = exam();
    fakeServer(api, baseline);
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
    const storesBefore = api.storeExamWorkspaceUndoStep.mock.calls.length;
    api.getExamWorkspaceDocument.mockRejectedValueOnce(new Error("reload failed"));
    holder = "tab-A";
    const outcome = await Promise.race([
      editing.requestTakeover().then(() => "settled"),
      new Promise((resolve) => setTimeout(() => resolve("hung"), 1500)).then((value) => value),
    ]);
    expect(outcome).toBe("settled");
    await flushPromises();
    const workspace = editing.workspaceDocument.value;
    if (workspace === null) {
      throw new Error("expected an open document");
    }
    expect(pointsOf(workspace, "item_001")).toBe(7);
    expect(editing.history.pending.value).toBe(true);
    expect(api.storeExamWorkspaceUndoStep.mock.calls.length).toBe(storesBefore);
  });

  it("settles without a merged store when the lineage changes during the takeover wait", { timeout: 8000 }, async () => {
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
    // The history read hangs: both the cursor-triggered load and the
    // recovery's explicit resync wait for it while the lineage moves on.
    api.getExamWorkspaceHistory.mockImplementation(() => new Promise(() => undefined));
    const storesBefore = api.storeExamWorkspaceUndoStep.mock.calls.length;
    holder = "tab-A";
    const takeover = editing.requestTakeover();
    const settledRace = Promise.race([
      takeover.then(() => "settled"),
      new Promise((resolve) => setTimeout(() => resolve("hung"), 2000)).then((value) => value),
    ]);
    await flushPromises();
    await new Promise((resolve) => setTimeout(resolve, 100));
    const otherLineage = "00000000-0000-4000-8000-000000000002";
    const otherDocument: NativeExamDocument = { ...storedB, document_id: otherLineage };
    editing.applyCommandResponse({
      ...response(otherDocument, "other-cursor"),
      summary: { ...response(otherDocument, "other-cursor").summary, lineage_id: otherLineage },
    });
    await flushPromises();
    expect(await settledRace).toBe("settled");
    await takeover;
    await flushPromises();
    expect(api.storeExamWorkspaceUndoStep.mock.calls.length).toBe(storesBefore);
  });

  it("settles and keeps the edit when the takeover GET returns the unchanged cursor in a fresh object", { timeout: 8000 }, async () => {
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
    // The other tab made no document edit: the takeover GET returns the same
    // cursor and content, but in a fresh response object every time, as the
    // transport does (the reload-failure check is by identity).
    api.getExamWorkspaceDocument.mockImplementation(async () => {
      const newest = server.documents.get(server.state.cursor);
      if (newest === undefined) {
        throw new Error("expected the newest server document");
      }
      return response(JSON.parse(JSON.stringify(newest)), server.state.cursor);
    });
    holder = "tab-A";
    const outcome = await Promise.race([
      editing.requestTakeover().then(() => "settled"),
      new Promise((resolve) => setTimeout(() => resolve("hung"), 2000)).then((value) => value),
    ]);
    expect(outcome).toBe("settled");
    await flushPromises();
    const workspace = editing.workspaceDocument.value;
    if (workspace === null) {
      throw new Error("expected an open document");
    }
    expect(pointsOf(workspace, "item_001")).toBe(7);
    expect(editing.history.pending.value).toBe(false);
    expect(pointsOf(lastStoredDocument(), "item_001")).toBe(7);
  });

  it("merges the kept edit at the retry's fresh load after a failed takeover reload", { timeout: 8000 }, async () => {
    vi.useFakeTimers();
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
    // The takeover load fails once, then serves the newest copy with a fresh
    // object each time, as the transport does.
    api.getExamWorkspaceDocument.mockRejectedValueOnce(new Error("reload failed"));
    api.getExamWorkspaceDocument.mockImplementation(async () =>
      response(JSON.parse(JSON.stringify(storedB)), "step-B"),
    );
    holder = "tab-A";
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
    // The kept edit waits in the gate for the retry: visible and locked.
    const kept = editing.workspaceDocument.value;
    if (kept === null) {
      throw new Error("expected an open document");
    }
    expect(pointsOf(kept, "item_001")).toBe(7);
    expect(editing.editingLocked.value).toBe(true);
    const storesBefore = api.storeExamWorkspaceUndoStep.mock.calls.length;
    // A save while loading settles at once: no store, no conflict recovery,
    // and the kept edit stays intact.
    await expect(editing.save()).resolves.toBe(false);
    expect(api.storeExamWorkspaceUndoStep.mock.calls.length).toBe(storesBefore);
    // The retry's fresh load merges the kept edit at the merge point and
    // stores it.
    for (
      let attempt = 0;
      attempt < 20 && api.storeExamWorkspaceUndoStep.mock.calls.length === storesBefore;
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

  it("settles without storing past disposal while the acquisition GET is in flight", { timeout: 8000 }, async () => {
    const baseline = exam();
    fakeServer(api, baseline);
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
    let resolveGet: ((payload: ExamWorkspaceDocumentResponse) => void) | undefined;
    api.getExamWorkspaceDocument.mockImplementationOnce(
      () =>
        new Promise<ExamWorkspaceDocumentResponse>((resolve) => {
          resolveGet = resolve;
        }),
    );
    const storesBefore = api.storeExamWorkspaceUndoStep.mock.calls.length;
    holder = "tab-A";
    const takeover = editing.requestTakeover();
    await flushPromises();
    stopScopes();
    if (resolveGet === undefined) {
      throw new Error("expected the acquisition GET to start");
    }
    resolveGet(response({ ...baseline }, "step-0"));
    const outcome = await Promise.race([
      takeover.then(() => "settled"),
      new Promise((resolve) => setTimeout(() => resolve("hung"), 2000)).then((value) => value),
    ]);
    expect(outcome).toBe("settled");
    await flushPromises();
    expect(api.storeExamWorkspaceUndoStep.mock.calls.length).toBe(storesBefore);
  });
});
