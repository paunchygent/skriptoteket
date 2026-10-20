/**
 * Exam workspace editing session: lease-fence fail-first ports
 * (TASK-SKRIPT-40-04-14, unit FF2, rereview 5).
 *
 * Ported from the reviewer's failing probes, kept scenario-for-scenario with
 * truthful names. Every test drives the public editing session
 * (`applyCommandResponse`, `openDocument`, `save`, `updateItemPoints`), the
 * same seam the probes use, so the tests survive the V1/V4/V5 repairs. Each
 * test fails at 768d8ab3 the way the reviewer saw it.
 *
 * Probe source (read-only, not edited):
 *   fence-neighbours.spec.mjs, tests 1 (V1), 2 (V4) and 5 (V5).
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
import type { ExamWorkspaceEditLeaseServer } from "./examWorkspaceEditLeaseDrivers";
import {
  LINEAGE,
  exam,
  fakeServer,
  inScope,
  response,
  stopScopes,
} from "./useExamWorkspaceEditing.history.specSupport";
import { deferred } from "./useExamWorkspaceSyncGate.specSupport";

const api = vi.hoisted(() => ({
  copyExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  retryExamWorkspaceItem: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));
const toast = vi.hoisted(() => ({ failure: vi.fn(), warning: vi.fn() }));

vi.mock("../../../api/examWorkspace", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspace")>()),
  ...api,
}));
vi.mock("../../../composables/useToast", () => ({ useToast: () => toast }));
vi.mock("../../../composables/useAiAccess", () => ({ useAiAccess: () => ({ canUseAi: { value: true } }) }));

beforeEach(() => {
  for (const fn of [...Object.values(api), ...Object.values(toast)]) fn.mockReset();
});

afterEach(() => {
  stopScopes();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

const EXAM_B = "00000000-0000-4000-8000-000000000002";

function held(tab: string | null = "A", requested = false): ExamWorkspaceEditLeaseResponse {
  return {
    holder_tab_id: tab,
    renewed_at: "2026-10-20T06:15:00Z",
    takeover_requested: requested,
    takeover_requested_by: requested ? "B" : null,
  };
}

function heldError(): ApiError {
  return new ApiError({ code: "EDIT_LEASE_HELD", message: "held", status: 409 });
}

function reply(
  document: NativeExamDocument,
  cursor = "step-0",
  lineage: string = LINEAGE,
): ExamWorkspaceDocumentResponse {
  const payload = response(document, cursor);
  return { ...payload, summary: { ...payload.summary, lineage_id: lineage, vault_file_id: lineage } };
}

function session(
  server: ExamWorkspaceEditLeaseServer,
  tabId = "A",
): ReturnType<typeof useExamWorkspaceEditing> {
  return inScope(() => useExamWorkspaceEditing(serverExamWorkspaceStore, { server, tabId }));
}

function driverWith(flags: { offline?: boolean } = {}): ExamWorkspaceEditLeaseServer {
  return {
    claim: () => Promise.resolve(held()),
    release: () => Promise.resolve(held(null)),
    requestTakeover: () => Promise.resolve(held()),
    renew: () => {
      if (flags.offline === true) {
        return Promise.reject(new TypeError("network"));
      }
      return Promise.resolve(held());
    },
  };
}

describe("the lease fence fail-first ports", () => {
  it("a stale claim must not free a newer live A visit lease after A to B to A", async () => {
    vi.useFakeTimers();
    const base = exam();
    fakeServer(api, base);
    const holders = new Map<string, string>([[LINEAGE, "B"]]);
    const delayed = deferred<ExamWorkspaceEditLeaseResponse>();
    let arm = false;
    const driver: ExamWorkspaceEditLeaseServer = {
      claim: (lineageId: string, tabId: string) => {
        if (holders.has(lineageId) && holders.get(lineageId) !== tabId) {
          return Promise.reject(heldError());
        }
        holders.set(lineageId, tabId);
        if (lineageId === LINEAGE && tabId === "A" && arm) {
          arm = false;
          return delayed.promise;
        }
        return Promise.resolve(held(tabId));
      },
      release: (lineageId: string, tabId: string) => {
        if (holders.get(lineageId) === tabId) {
          holders.delete(lineageId);
        }
        return Promise.resolve(held(null));
      },
      renew: (lineageId: string, tabId: string) => {
        if (holders.get(lineageId) !== tabId) {
          return Promise.reject(heldError());
        }
        return Promise.resolve(held(tabId));
      },
      requestTakeover: () => Promise.resolve(held("B")),
    };
    const editing = session(driver);
    editing.applyCommandResponse(reply(base));
    await flushPromises();
    expect(editing.leaseReadOnly.value).toBe(true);
    holders.delete(LINEAGE);
    arm = true;
    await vi.advanceTimersByTimeAsync(5000);
    expect(holders.get(LINEAGE)).toBe("A");
    editing.applyCommandResponse(reply({ ...base, document_id: EXAM_B, title: "Exam B" }, "step-0", EXAM_B));
    await flushPromises();
    editing.applyCommandResponse(reply(base));
    await flushPromises();
    expect(editing.editingLocked.value).toBe(false);
    delayed.resolve(held());
    await flushPromises();
    const other = session(driver, "B");
    other.applyCommandResponse(reply(base));
    await flushPromises();
    expect({
      editableA: !editing.editingLocked.value,
      editableB: !other.editingLocked.value,
      holder: holders.get(LINEAGE),
    }).toEqual({ editableA: true, editableB: false, holder: "A" });
  });

  it("a stale renew takeover answer must not yield the new exam before the fence sees it", async () => {
    vi.useFakeTimers();
    const base = exam();
    fakeServer(api, base);
    const old = deferred<ExamWorkspaceEditLeaseResponse>();
    let first = true;
    const driver: ExamWorkspaceEditLeaseServer = {
      ...driverWith(),
      renew: () => {
        if (first) {
          first = false;
          return old.promise;
        }
        return Promise.resolve(held());
      },
    };
    const editing = session(driver);
    editing.applyCommandResponse(reply(base));
    await flushPromises();
    await vi.advanceTimersByTimeAsync(5000);
    const second = { ...base, document_id: EXAM_B, title: "Exam B" };
    api.getExamWorkspaceDocument.mockResolvedValue(reply(second, "step-0", EXAM_B));
    expect(await editing.openDocument(EXAM_B)).toBe(true);
    await flushPromises();
    expect(editing.editingLocked.value).toBe(false);
    old.resolve(held("A", true));
    await flushPromises();
    await flushPromises();
    const workspace = editing.workspaceDocument.value;
    if (workspace === null) {
      throw new Error("expected an open document");
    }
    expect({
      locked: editing.editingLocked.value,
      readonly: editing.leaseReadOnly.value,
      title: workspace.title,
    }).toEqual({ locked: false, readonly: false, title: "Exam B" });
  });

  it("pagehide must retire pending acknowledgement installs even without a Vue unmount", async () => {
    const events = new EventTarget();
    vi.stubGlobal("window", events);
    const base = exam();
    fakeServer(api, base);
    const driver = driverWith();
    const release = vi.fn(driver.release);
    const tracked: ExamWorkspaceEditLeaseServer = { ...driver, release };
    const editing = session(tracked);
    editing.applyCommandResponse(reply(base));
    await flushPromises();
    const persist = api.storeExamWorkspaceUndoStep.getMockImplementation();
    if (persist === undefined) {
      throw new Error("expected the step store double");
    }
    const old = deferred<unknown>();
    let ack: unknown = undefined;
    api.storeExamWorkspaceUndoStep.mockImplementationOnce(
      async (lineageId: string, request: { document: NativeExamDocument }) => {
        const stored: unknown = await persist(lineageId, request);
        ack = stored;
        return old.promise;
      },
    );
    editing.updateItemPoints("item_001", 7);
    const saving = editing.save();
    await flushPromises();
    events.dispatchEvent(new Event("pagehide"));
    await flushPromises();
    expect(release).toHaveBeenCalled();
    if (ack === undefined) {
      throw new Error("expected the delayed acknowledgement");
    }
    old.resolve(ack);
    const saved = await saving;
    await flushPromises();
    expect({ position: editing.history.position.value, saved }).toEqual({
      position: "step-0",
      saved: false,
    });
  });
});
