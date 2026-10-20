/**
 * Exam workspace kept remote edit: fail-first ports of the reviewer's R9-2
 * probes (TASK-SKRIPT-40-04-14, rereview 9, both rows of "a committed store
 * plus remote edit retains the revert").
 *
 * Each case keeps the reviewer's scenario, assertion and name, driven through
 * the production owners as the probes do: the production editing, document,
 * gate, history and merge, with the existing cursor-aware fake server. B's
 * write is modeled only after A's lease TTL expires (16 s without renewal
 * against the 15 s TTL). Doubles cover only transport, clock, lease responses
 * and server persistence. The probe source is read-only and lives outside
 * the repository:
 * `RR/scratch/3e452c40-125d-4406-940a-ed0effc63ed6/route-boundaries.spec.mjs`.
 *
 * Both rows must fail before the repair (the kept-edit merge base treats the
 * reverted q1 as unchanged against the confirmed baseline, so the fresh copy
 * keeps the remote q1=7 instead of A's revert to 2).
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

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
  type EditingApiMocks,
} from "./useExamWorkspaceEditing.history.specSupport";
import { deferred } from "./useExamWorkspaceSyncGate.specSupport";

const api: EditingApiMocks = vi.hoisted(() => ({
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
vi.mock("../../../composables/useAiAccess", () => ({ useAiAccess: () => ({ canUseAi: { value: true } }) }));

function held(): ExamWorkspaceEditLeaseResponse {
  return {
    holder_tab_id: "A",
    renewed_at: "2026-10-20T06:15:00Z",
    takeover_requested: false,
    takeover_requested_by: null,
  };
}

function heldError(): ApiError {
  return new ApiError({ code: "EDIT_LEASE_HELD", message: "held", status: 409 });
}

function pointsList(document: NativeExamDocument | null): Array<number | null> {
  if (document === null) {
    throw new Error("expected an open document");
  }
  return document.items.map((item) => item.points);
}

async function settle(): Promise<void> {
  for (let index = 0; index < 8; index += 1) {
    await flushPromises();
  }
}

beforeEach(() => {
  vi.useFakeTimers();
  for (const mock of Object.values(api)) {
    mock.mockReset();
  }
  for (const mock of Object.values(toast)) {
    mock.mockReset();
  }
});

afterEach(() => {
  stopScopes();
  vi.useRealTimers();
});

it.each([false, true])(
  "R9 a committed store plus remote edit retains the revert (additional local title edit: %s)",
  async (changeTitle: boolean) => {
    const base = exam();
    const server = fakeServer(api, base);
    let holder = "A";
    let offline = false;
    // A native ApiError is needed for the lease driver to classify foreign ownership.
    const editing = inScope(() =>
      useExamWorkspaceEditing(serverExamWorkspaceStore, {
        server: {
          claim: () => {
            if (holder !== "A") {
              return Promise.reject(heldError());
            }
            return Promise.resolve(held());
          },
          renew: () => {
            if (offline) {
              return Promise.reject(new TypeError("network unavailable"));
            }
            if (holder !== "A") {
              return Promise.reject(heldError());
            }
            return Promise.resolve(held());
          },
          release: () => Promise.resolve(held()),
          requestTakeover: () => Promise.resolve(held()),
        },
        tabId: "A",
      }),
    );
    editing.applyCommandResponse(response(base, "step-0"));
    await settle();
    const persist = api.storeExamWorkspaceUndoStep.getMockImplementation();
    if (persist === undefined) {
      throw new Error("expected the step store double");
    }
    const ack = deferred<unknown>();
    let stored: unknown = null;
    api.storeExamWorkspaceUndoStep.mockImplementationOnce((lineageId: string, request: unknown) => {
      const saving = persist(lineageId, request);
      stored = saving;
      return ack.promise;
    });
    editing.updateItemPoints("item_001", 7);
    const saving = editing.save();
    await settle();
    editing.updateItemPoints("item_001", 2);
    if (changeTitle) {
      editing.setTitle("Locally kept title");
    }
    // A cannot renew for longer than the 15 s TTL. B writes only after A expires.
    offline = true;
    await vi.advanceTimersByTimeAsync(16000);
    await settle();
    expect(editing.leaseReadOnly.value).toBe(true);
    holder = "B";
    const current = server.documents.get(server.state.position);
    if (current === undefined) {
      throw new Error("expected the served document");
    }
    const newer: NativeExamDocument = {
      ...current,
      items: current.items.map((item) =>
        item.item_id === "item_002" ? { ...item, points: 9 } : item,
      ),
    };
    server.documents.set("step-B", newer);
    server.state.steps.push("step-B");
    server.state.cursor = "step-B";
    server.state.position = "step-B";
    ack.resolve(stored);
    await saving;
    await settle();
    // B now releases; A's next heartbeat can claim normally.
    holder = "A";
    offline = false;
    await vi.advanceTimersByTimeAsync(4000);
    await settle();
    expect(editing.editingLocked.value).toBe(false);
    const beforeSave = pointsList(editing.workspaceDocument.value);
    // A normal save/conflict recovery of the reacquired copy must preserve both teachers' edits.
    await editing.save();
    await settle();
    expect({
      beforeSave,
      persisted: pointsList(server.documents.get(server.state.position) ?? null),
      status: editing.history.saveStatus.value.state,
      visible: pointsList(editing.workspaceDocument.value),
    }).toEqual({ beforeSave: [2, 9], persisted: [2, 9], status: "saved", visible: [2, 9] });
  },
);
