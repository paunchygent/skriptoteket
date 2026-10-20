/**
 * Exam workspace editing session: generation-fenced history and write effects
 * (TASK-SKRIPT-40-04-14, unit FF fail-first ports of rereview-4 U1-U3).
 *
 * Ported from the reviewer's failing probes, kept scenario-for-scenario with
 * truthful names. Every test drives the public editing session
 * (`applyCommandResponse`, `openDocument`, `save`, `updateItemPoints`,
 * `history.undo`) or the real sync gate (`createGate`), because the gate and
 * history internals are about to be redesigned around a fence helper. Each
 * test fails at the current head the way the reviewer saw it.
 *
 * Probe sources (read-only, not edited):
 *   gate-boundaries.spec.mjs (6 tests) and undo-generation.spec.mjs (1 test).
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceEditLeaseResponse,
  ExamWorkspaceHistory,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import { nullRouteProjection } from "./examWorkspaceRouteProjection.specSupport";
import {
  LINEAGE,
  exam,
  fakeServer,
  inScope,
  response,
  stopScopes,
} from "./useExamWorkspaceEditing.history.specSupport";
import {
  createGate,
  deferred,
  succeedLoad,
} from "./useExamWorkspaceSyncGate.specSupport";

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

type LeaseFlags = {
  offline?: boolean;
};

function leaseResponse(): ExamWorkspaceEditLeaseResponse {
  return {
    holder_tab_id: "A",
    renewed_at: "2026-10-20T00:30:00Z",
    takeover_requested: false,
    takeover_requested_by: null,
  };
}

function session(flags: LeaseFlags = {}): ReturnType<typeof useExamWorkspaceEditing> {
  return inScope(() =>
    useExamWorkspaceEditing(serverExamWorkspaceStore, nullRouteProjection(), {
      server: {
        claim: async () => leaseResponse(),
        release: async () => leaseResponse(),
        requestTakeover: async () => leaseResponse(),
        renew: async () => {
          if (flags.offline === true) {
            throw new TypeError("network");
          }
          return leaseResponse();
        },
      },
      tabId: "A",
    }),
  );
}

function stepList(cursor: string, ids: string[]): ExamWorkspaceHistory {
  return {
    baseline_step_id: "step-0",
    cursor,
    position_step_id: cursor,
    step_ids: ids,
  };
}

function cloneDocument(document: NativeExamDocument): NativeExamDocument {
  return JSON.parse(JSON.stringify(document));
}

function workspaceOf(editing: ReturnType<typeof useExamWorkspaceEditing>): NativeExamDocument {
  const document = editing.workspaceDocument.value;
  if (document === null) {
    throw new Error("expected an open document");
  }
  return document;
}

function pointsOf(document: NativeExamDocument, itemId: string): number | null {
  const found = document.items.find((item) => item.item_id === itemId);
  if (found === undefined) {
    throw new Error(`expected ${itemId}`);
  }
  return found.points;
}

function documentOf(reply: unknown): NativeExamDocument {
  if (typeof reply !== "object" || reply === null) {
    throw new Error("expected a move reply");
  }
  if (!("document" in reply)) {
    throw new Error("expected a move reply");
  }
  const document: unknown = reply.document;
  return JSON.parse(JSON.stringify(document));
}

describe("the generation fence fail-first ports", () => {
  it("a late history success from the same lineage but an older generation must not overwrite the new history", async () => {
    const base = exam();
    fakeServer(api, base);
    const old = deferred<ExamWorkspaceHistory>();
    api.getExamWorkspaceHistory
      .mockImplementationOnce(() => old.promise)
      .mockResolvedValue(stepList("step-B", ["step-B"]));
    const editing = session();
    editing.applyCommandResponse(response(base, "step-0"));
    await flushPromises();
    const newer = { ...base, title: "New copy" };
    editing.applyCommandResponse(response(newer, "step-B"));
    await flushPromises();
    await flushPromises();
    expect(editing.editingLocked.value).toBe(false);
    expect(editing.history.position.value).toBe("step-B");
    old.resolve(stepList("step-0", []));
    await flushPromises();
    expect({
      locked: editing.editingLocked.value,
      position: editing.history.position.value,
      stepTitle: editing.history.stepDocument.value?.title,
    }).toEqual({ locked: false, position: "step-B", stepTitle: "New copy" });
  });

  it("a late history failure from an abandoned exam must not reset the new exam history", async () => {
    const base = exam();
    const server = fakeServer(api, base);
    const old = deferred<ExamWorkspaceHistory>();
    const other = "00000000-0000-4000-8000-000000000002";
    api.getExamWorkspaceHistory.mockImplementation((id: string) =>
      id === LINEAGE ? old.promise : Promise.resolve(stepList("step-B", ["step-B"])),
    );
    const editing = session();
    editing.applyCommandResponse(response(base, "step-0"));
    await flushPromises();
    const second = { ...exam("Second exam"), document_id: other };
    const next: ExamWorkspaceDocumentResponse = response(second, "step-B");
    next.summary = { ...next.summary, lineage_id: other, vault_file_id: other };
    server.documents.set("step-B", second);
    server.state.steps = ["step-B"];
    server.state.cursor = "step-B";
    server.state.position = "step-B";
    api.getExamWorkspaceDocument.mockImplementation(async () => structuredClone(next));
    expect(await editing.requestRoute(other)).toBe("installed");
    await flushPromises();
    await flushPromises();
    await flushPromises();
    expect(editing.editingLocked.value).toBe(false);
    expect(editing.history.position.value).toBe("step-B");
    old.reject(new Error("old history failed"));
    await flushPromises();
    const ready = {
      locked: editing.editingLocked.value,
      position: editing.history.position.value,
      stepTitle: editing.history.stepDocument.value?.title,
    };
    editing.updateItemPoints("item_001", 8);
    const saved = await editing.save();
    await flushPromises();
    expect({
      ...ready,
      saved,
      status: editing.history.saveStatus.value.state,
      stores: api.storeExamWorkspaceUndoStep.mock.calls.length,
    }).toEqual({
      locked: false,
      position: "step-B",
      saved: true,
      status: "saved",
      stepTitle: "Second exam",
      stores: 1,
    });
  });

  it("writes submitted outside editing must refuse immediately even when a prior generation write is pending", async () => {
    const harness = createGate();
    harness.gate.openExam(LINEAGE, false);
    await succeedLoad(harness, exam());
    const first = deferred<string>();
    const writing = harness.gate.enqueueWrite(() => first.promise, "refused");
    await harness.settle();
    harness.gate.foreignCursor(false);
    let settled = false;
    const refused = harness.gate
      .enqueueWrite(async () => "should never run", "refused")
      .then((value) => {
        settled = true;
        return value;
      });
    await harness.settle();
    const wasSettled = settled;
    first.resolve("old response");
    await writing;
    await refused;
    harness.gate.dispose();
    expect(wasSettled).toBe(true);
  });

  it("an old-generation store reply must not discard newer typing after the lease is reclaimed and the fresh merge installs", async () => {
    vi.useFakeTimers();
    const base = exam();
    const server = fakeServer(api, base);
    const flags: LeaseFlags = { offline: false };
    const editing = session(flags);
    editing.applyCommandResponse(response(base, "step-0"));
    await flushPromises();
    editing.updateItemPoints("item_001", 5);
    await editing.save();
    const transport = api.storeExamWorkspaceUndoStep.getMockImplementation();
    if (transport === undefined) {
      throw new Error("expected the step store double");
    }
    const old = deferred<unknown>();
    let oldAck: unknown = undefined;
    api.storeExamWorkspaceUndoStep.mockImplementationOnce(
      async (lineage: string, request: { document: NativeExamDocument }) => {
        const ack: unknown = await transport(lineage, request);
        oldAck = ack;
        return await old.promise;
      },
    );
    editing.updateItemPoints("item_001", 7);
    const saving = editing.save();
    await flushPromises();
    expect(oldAck).toBeDefined();
    flags.offline = true;
    await vi.advanceTimersByTimeAsync(16000);
    await flushPromises();
    const committed = server.documents.get(server.state.cursor);
    if (committed === undefined) {
      throw new Error("expected the committed step");
    }
    const other: NativeExamDocument = {
      ...cloneDocument(committed),
      items: committed.items.map((item) =>
        item.item_id === "item_002" ? { ...item, points: 9 } : item,
      ),
    };
    server.documents.set("step-B", other);
    server.state.steps.push("step-B");
    server.state.cursor = "step-B";
    server.state.position = "step-B";
    api.getExamWorkspaceDocument.mockImplementation(async () => {
      const current = server.documents.get(server.state.cursor);
      if (current === undefined) {
        throw new Error("expected the server copy");
      }
      return response(cloneDocument(current), server.state.cursor);
    });
    await vi.advanceTimersByTimeAsync(4000);
    await flushPromises();
    await flushPromises();
    expect(editing.editingLocked.value).toBe(false);
    expect(workspaceOf(editing).items.map((item) => item.points)).toEqual([7, 9]);
    editing.updateItemPoints("item_001", 8);
    expect(pointsOf(workspaceOf(editing), "item_001")).toBe(8);
    if (oldAck === undefined) {
      throw new Error("expected the delayed acknowledgement");
    }
    old.resolve(oldAck);
    await saving;
    await flushPromises();
    await flushPromises();
    await flushPromises();
    expect(workspaceOf(editing).items.map((item) => item.points)).toEqual([8, 9]);
  });

  it("a same-lineage reopen after reclaim must survive a delayed obsolete undo acknowledgement", async () => {
    vi.useFakeTimers();
    const base = exam();
    const server = fakeServer(api, base);
    const flags: LeaseFlags = { offline: false };
    const editing = session(flags);
    editing.applyCommandResponse(response(base, "step-0"));
    await flushPromises();
    editing.updateItemPoints("item_001", 5);
    await editing.save();
    editing.updateItemPoints("item_001", 7);
    await editing.save();
    const inner = api.moveExamWorkspaceHistoryPosition.getMockImplementation();
    if (inner === undefined) {
      throw new Error("expected the move double");
    }
    let oldAck: unknown = undefined;
    const reply = deferred<unknown>();
    api.moveExamWorkspaceHistoryPosition.mockImplementationOnce(
      async (lineage: string, request: { stepId: string }) => {
        const ack: unknown = await inner(lineage, request);
        oldAck = ack;
        return reply.promise;
      },
    );
    const undoing = editing.history.undo();
    await flushPromises();
    expect(oldAck).toBeDefined();
    flags.offline = true;
    await vi.advanceTimersByTimeAsync(16000);
    await flushPromises();
    if (oldAck === undefined) {
      throw new Error("expected the delayed move acknowledgement");
    }
    const moved = documentOf(oldAck);
    const other: NativeExamDocument = {
      ...cloneDocument(moved),
      items: moved.items.map((item) =>
        item.item_id === "item_002" ? { ...item, points: 9 } : item,
      ),
    };
    server.documents.set("step-B", other);
    server.state.steps.push("step-B");
    server.state.position = "step-B";
    server.state.cursor = "step-B";
    api.getExamWorkspaceDocument.mockImplementation(async () => {
      const current = server.documents.get(server.state.position);
      if (current === undefined) {
        throw new Error("expected the server copy");
      }
      return response(cloneDocument(current), server.state.cursor);
    });
    await vi.advanceTimersByTimeAsync(4000);
    await flushPromises();
    await flushPromises();
    await editing.requestRoute(LINEAGE);
    await flushPromises();
    expect(workspaceOf(editing).items.map((item) => item.points)).toEqual([5, 9]);
    reply.resolve(oldAck);
    await undoing;
    await flushPromises();
    await flushPromises();
    expect({
      points: workspaceOf(editing).items.map((item) => item.points),
      status: editing.history.saveStatus.value.state,
    }).toEqual({ points: [5, 9], status: "saved" });
  });

  it("acquiring after a lease expired during loading must not make the pre-acquisition response editable", async () => {
    vi.useFakeTimers();
    const base = exam();
    const server = fakeServer(api, base);
    const flags: LeaseFlags = { offline: false };
    const editing = session(flags);
    editing.applyCommandResponse(response(base, "step-0"));
    await flushPromises();
    const steps = deferred<ExamWorkspaceHistory>();
    api.getExamWorkspaceHistory.mockImplementationOnce(() => steps.promise);
    editing.applyCommandResponse(response({ ...base, title: "Before lease loss" }, "step-X"));
    await flushPromises();
    flags.offline = true;
    await vi.advanceTimersByTimeAsync(16000);
    await flushPromises();
    const newest = { ...base, title: "After remote save" };
    server.documents.set("step-Y", newest);
    server.state.steps = ["step-X", "step-Y"];
    server.state.cursor = "step-Y";
    server.state.position = "step-Y";
    api.getExamWorkspaceDocument.mockResolvedValue(response(newest, "step-Y"));
    api.getExamWorkspaceHistory.mockResolvedValue(stepList("step-Y", ["step-X", "step-Y"]));
    await vi.advanceTimersByTimeAsync(4000);
    await flushPromises();
    steps.resolve(stepList("step-X", ["step-X"]));
    await flushPromises();
    await flushPromises();
    expect({
      locked: editing.editingLocked.value,
      title: workspaceOf(editing).title,
    }).toEqual({ locked: false, title: "After remote save" });
  });
});
