/**
 * Exam workspace kept store across the other two retirements (TASK-SKRIPT-40-04-14, R8, step 1).
 *
 * Fail-first for the two retirement paths the FF4 route probes do not cover:
 * the kept-edit rule must keep an edit whenever the desired copy is
 * unconfirmed, even when the working copy equals the old baseline because a
 * store is still in flight with an unknown answer. Each case opens X at
 * question points 2, changes to 7, starts a store and changes the points back
 * to 2 (or keeps 7), all through the production editing session; doubles
 * cover only transport, clock, server and the lease holder.
 *
 * Cases a and b must fail before the repair (no kept edit is captured, so the
 * fresh load installs the committed 7 and the status reads saved early); case
 * c passes before and after (an ordinary pending edit is already kept).
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
import { nullRouteProjection } from "./examWorkspaceRouteProjection.specSupport";
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

type EditingSession = ReturnType<typeof useExamWorkspaceEditing>;

function heldError(): ApiError {
  return new ApiError({ code: "EDIT_LEASE_HELD", message: "held", status: 409 });
}

function leaseResponse(holder: string): ExamWorkspaceEditLeaseResponse {
  return {
    holder_tab_id: holder,
    renewed_at: "2026-10-20T06:15:00Z",
    takeover_requested: false,
    takeover_requested_by: null,
  };
}

function leaseDouble(getHolder: () => string) {
  return {
    claim: async () => {
      if (getHolder() !== "tab-A") {
        throw heldError();
      }
      return leaseResponse("tab-A");
    },
    release: async () => leaseResponse(getHolder()),
    renew: async () => {
      if (getHolder() !== "tab-A") {
        throw heldError();
      }
      return leaseResponse("tab-A");
    },
    requestTakeover: async () => leaseResponse("tab-A"),
  };
}

function pointsOf(document: NativeExamDocument | null, itemId: string): number | null {
  if (document === null) {
    throw new Error("expected an open document");
  }
  const found = document.items.find((item) => item.item_id === itemId);
  if (found === undefined) {
    throw new Error(`expected ${itemId}`);
  }
  return found.points;
}

async function settle(): Promise<void> {
  for (let index = 0; index < 10; index += 1) {
    await flushPromises();
  }
}

/** Open X editable at points 2; the caller drives the holder, the store answer and the loss. */
async function openSession(): Promise<{
  editing: EditingSession;
  server: ReturnType<typeof fakeServer>;
  setHolder: (holder: string) => void;
}> {
  const server = fakeServer(api, exam());
  let holder = "tab-A";
  const editing = inScope(() =>
    useExamWorkspaceEditing(serverExamWorkspaceStore, nullRouteProjection(), {
      server: leaseDouble(() => holder),
      tabId: "tab-A",
    }),
  );
  editing.applyCommandResponse(response(exam(), "step-0"));
  await settle();
  expect(editing.editingLocked.value).toBe(false);
  return { editing, server, setHolder: (next: string) => { holder = next; } };
}

/** Wait until the gate leaves `loading` again after a reacquisition. */
async function settleReacquired(editing: EditingSession): Promise<void> {
  for (let attempt = 0; attempt < 30 && editing.editingLocked.value; attempt += 1) {
    await vi.advanceTimersByTimeAsync(1000);
    await settle();
  }
  await settle();
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

it("a. a revert to the baseline during a committed held store ends at the revert after lease loss and reacquisition", async () => {
  const { editing, server, setHolder } = await openSession();
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
  await settle();
  expect(editing.isDirty.value).toBe(false);
  setHolder("tab-B");
  await vi.advanceTimersByTimeAsync(5000);
  await settle();
  expect(editing.leaseReadOnly.value).toBe(true);
  expect(editing.history.saveStatus.value.state).not.toBe("saved");
  ack.resolve(stored);
  await saving;
  await settle();
  setHolder("tab-A");
  await settleReacquired(editing);
  expect({
    copy: pointsOf(editing.workspaceDocument.value, "item_001"),
    server: pointsOf(server.documents.get(server.state.position) ?? null, "item_001"),
    status: editing.history.saveStatus.value.state,
  }).toEqual({ copy: 2, server: 2, status: "saved" });
});

it("b. a revert to the baseline during a committed held store ends at the revert after a pagehide and a heartbeat reacquisition", async () => {
  const { editing, server } = await openSession();
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
  await settle();
  expect(editing.isDirty.value).toBe(false);
  window.dispatchEvent(new Event("pagehide"));
  await settle();
  expect(editing.leaseReadOnly.value).toBe(true);
  expect(editing.history.saveStatus.value.state).not.toBe("saved");
  ack.resolve(stored);
  await saving;
  await settle();
  await settleReacquired(editing);
  expect({
    copy: pointsOf(editing.workspaceDocument.value, "item_001"),
    server: pointsOf(server.documents.get(server.state.position) ?? null, "item_001"),
    status: editing.history.saveStatus.value.state,
  }).toEqual({ copy: 2, server: 2, status: "saved" });
});

it("c. a held store that never commits still reaches the server after lease loss and reacquisition", async () => {
  const { editing, server, setHolder } = await openSession();
  api.storeExamWorkspaceUndoStep.mockImplementationOnce(() => deferred<unknown>().promise);
  editing.updateItemPoints("item_001", 7);
  const saving = editing.save();
  await settle();
  setHolder("tab-B");
  await vi.advanceTimersByTimeAsync(5000);
  await settle();
  expect(editing.leaseReadOnly.value).toBe(true);
  expect(editing.history.saveStatus.value.state).not.toBe("saved");
  await saving;
  await settle();
  setHolder("tab-A");
  await settleReacquired(editing);
  expect({
    copy: pointsOf(editing.workspaceDocument.value, "item_001"),
    server: pointsOf(server.documents.get(server.state.position) ?? null, "item_001"),
    status: editing.history.saveStatus.value.state,
  }).toEqual({ copy: 7, server: 7, status: "saved" });
});

it("d. a held store that never commits still reaches the server after a pagehide and a heartbeat reacquisition", async () => {
  const { editing, server } = await openSession();
  api.storeExamWorkspaceUndoStep.mockImplementationOnce(() => deferred<unknown>().promise);
  editing.updateItemPoints("item_001", 7);
  const saving = editing.save();
  await settle();
  window.dispatchEvent(new Event("pagehide"));
  await settle();
  expect(editing.leaseReadOnly.value).toBe(true);
  expect(editing.history.saveStatus.value.state).not.toBe("saved");
  await saving;
  await settle();
  await settleReacquired(editing);
  expect({
    copy: pointsOf(editing.workspaceDocument.value, "item_001"),
    server: pointsOf(server.documents.get(server.state.position) ?? null, "item_001"),
    status: editing.history.saveStatus.value.state,
  }).toEqual({ copy: 7, server: 7, status: "saved" });
});
