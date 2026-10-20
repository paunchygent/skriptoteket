/**
 * Exam workspace editing session: every edit entry point refuses outside editing.
 *
 * Expected behavior (TASK-SKRIPT-40-04-14, G1b): in `loading` and in
 * `readonly` each entry point (body text, points, title, instructions, a
 * structure command, undo, redo) is refused with no state change and no
 * transport call.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import type { ExamWorkspaceEditLeaseResponse, ExamWorkspaceHistory } from "../../../api/examWorkspace";
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

function leaseResponse(holder: string): ExamWorkspaceEditLeaseResponse {
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

function openSession(owner: { holder: string }, historyGate: { promise: Promise<ExamWorkspaceHistory> } | null) {
  const baseline = exam();
  fakeServer(api, baseline);
  if (historyGate !== null) {
    api.getExamWorkspaceHistory.mockImplementation(() => historyGate.promise);
  }
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
  editing.applyCommandResponse(response(baseline, "step-0"));
  return editing;
}

function transportCalls(): number {
  return Object.values(api).reduce((total, fn) => total + fn.mock.calls.length, 0);
}

async function expectAllRefused(
  editing: ReturnType<typeof useExamWorkspaceEditing>,
  label: string,
): Promise<void> {
  const before = JSON.parse(JSON.stringify(editing.workspaceDocument.value));
  const calls = transportCalls();
  editing.updateItemBody("item_001", [], false);
  editing.updateItemPoints("item_001", 5);
  editing.setTitle("Ny titel");
  editing.setExamInstructions([], false);
  editing.structure.addItem("free_text");
  await editing.history.undo();
  await editing.history.redo();
  await flushPromises();
  expect(editing.editingLocked.value, label).toBe(true);
  expect(JSON.parse(JSON.stringify(editing.workspaceDocument.value)), label).toEqual(before);
  expect(transportCalls(), label).toBe(calls);
  expect(editing.history.canUndo.value, label).toBe(false);
  expect(editing.history.canRedo.value, label).toBe(false);
}

describe("edit entry points outside editing", () => {
  it("refuses every entry point in loading with no state change and no transport call", async () => {
    const gate = deferred<ExamWorkspaceHistory>();
    const editing = openSession({ holder: "A" }, gate);
    await flushPromises();
    expect(editing.editingLocked.value).toBe(true);
    expect(editing.leaseReadOnly.value).toBe(false);
    await expectAllRefused(editing, "loading");
  });

  it("refuses every entry point in readonly with no state change and no transport call", async () => {
    const editing = openSession({ holder: "B" }, null);
    await flushPromises();
    expect(editing.editingLocked.value).toBe(true);
    expect(editing.leaseReadOnly.value).toBe(true);
    await expectAllRefused(editing, "readonly");
  });
});
