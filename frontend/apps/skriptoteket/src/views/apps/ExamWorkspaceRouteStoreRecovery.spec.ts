/**
 * Exam workspace route store recovery: fail-first ports of the reviewer's
 * positive controls and the `residual:` diagnostic (TASK-SKRIPT-40-04-14,
 * rereview 8).
 *
 * Each case keeps the reviewer's scenario, assertion and name, driven
 * through the production editing, document, gate and history owners as the
 * probes do. Doubles cover only transport, clock and server. The probe
 * source is read-only and lives outside the repository:
 * `RR/scratch/2ec498b8-d165-46f0-a53c-9a9ade583ad5/route-positive.spec.mjs`.
 *
 * The `residual:` case is the one whose expectation the lead's repair may
 * restate: the repair will make a route request store the open exam's latest
 * edit before it retires, so the end state may change from "a 5 s retry
 * stores 7" to "the store reaches the server before any open, and nothing
 * reports saved early". It is ported as the reviewer wrote it now.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import type { ExamWorkspaceEditLeaseResponse } from "../../api/examWorkspace";
import { serverExamWorkspaceStore } from "./exam-workspace/examWorkspaceStore";
import { useExamWorkspaceEditing } from "./exam-workspace/useExamWorkspaceEditing";
import type { NativeExamDocument } from "../../api/examWorkspace";
import {
  exam,
  fakeServer,
  inScope,
  response,
  stopScopes,
} from "./exam-workspace/useExamWorkspaceEditing.history.specSupport";
import { deferred } from "./exam-workspace/useExamWorkspaceSyncGate.specSupport";

const api = vi.hoisted(() => ({
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));
const toast = vi.hoisted(() => ({ failure: vi.fn(), warning: vi.fn() }));

vi.mock("../../api/examWorkspace", async (original) => ({
  ...(await original<typeof import("../../api/examWorkspace")>()),
  ...api,
}));
vi.mock("../../composables/useToast", () => ({ useToast: () => toast }));
vi.mock("../../composables/useAiAccess", () => ({ useAiAccess: () => ({ canUseAi: { value: true } }) }));

type EditingSession = ReturnType<typeof useExamWorkspaceEditing>;

function held(): ExamWorkspaceEditLeaseResponse {
  return {
    holder_tab_id: "A",
    renewed_at: "2026-10-20T06:15:00Z",
    takeover_requested: false,
    takeover_requested_by: null,
  };
}

async function settle(): Promise<void> {
  for (let index = 0; index < 8; index += 1) {
    await flushPromises();
  }
}

function session(): EditingSession {
  return inScope(() =>
    useExamWorkspaceEditing(serverExamWorkspaceStore, {
      server: {
        claim: () => Promise.resolve(held()),
        release: () => Promise.resolve(held()),
        renew: () => Promise.resolve(held()),
        requestTakeover: () => Promise.resolve(held()),
      },
      tabId: "A",
    }),
  );
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

it("control: a returned store preserves and persists a later revert without route retirement", async () => {
  const server = fakeServer(api, exam());
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
  const editing = session();
  editing.applyCommandResponse(response(exam(), "step-0"));
  await settle();
  editing.updateItemPoints("item_001", 7);
  const saving = editing.save();
  await settle();
  editing.updateItemPoints("item_001", 2);
  expect(editing.isDirty.value).toBe(false);
  ack.resolve(stored);
  await saving;
  await settle();
  await vi.advanceTimersByTimeAsync(6000);
  await settle();
  expect({
    persisted: pointsOf(server.documents.get(server.state.position) ?? null, "item_001"),
    status: editing.history.saveStatus.value.state,
    visible: pointsOf(editing.workspaceDocument.value, "item_001"),
  }).toEqual({ persisted: 2, status: "saved", visible: 2 });
});

it("control: an ordinary current network store failure retries after five seconds", async () => {
  const server = fakeServer(api, exam());
  api.storeExamWorkspaceUndoStep.mockRejectedValueOnce(new Error("network"));
  const editing = session();
  editing.applyCommandResponse(response(exam(), "step-0"));
  await settle();
  editing.updateItemPoints("item_001", 7);
  expect(await editing.save()).toBe(false);
  await settle();
  expect(api.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(1);
  await vi.advanceTimersByTimeAsync(4999);
  expect(api.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(1);
  await vi.advanceTimersByTimeAsync(1);
  await settle();
  expect({
    count: api.storeExamWorkspaceUndoStep.mock.calls.length,
    points: pointsOf(server.documents.get(server.state.position) ?? null, "item_001"),
  }).toEqual({ count: 2, points: 7 });
});

it("residual: retiring a current save while a different open fails leaves its edit unconfirmed without retry", async () => {
  const server = fakeServer(api, exam());
  const ack = deferred<unknown>();
  api.storeExamWorkspaceUndoStep.mockReturnValueOnce(ack.promise);
  const editing = session();
  editing.applyCommandResponse(response(exam(), "step-0"));
  await settle();
  editing.updateItemPoints("item_001", 7);
  const saving = editing.save();
  await settle();
  api.getExamWorkspaceDocument.mockRejectedValueOnce(new Error("next exam offline"));
  await editing.openDocument("00000000-0000-4000-8000-000000000002");
  await saving;
  await settle();
  await vi.advanceTimersByTimeAsync(6000);
  await settle();
  // This exercises the public open entry directly, not the address owner's dirty guard.
  expect({
    count: api.storeExamWorkspaceUndoStep.mock.calls.length,
    points: pointsOf(server.documents.get(server.state.position) ?? null, "item_001"),
    visible: pointsOf(editing.workspaceDocument.value, "item_001"),
  }).toEqual({ count: 2, points: 7, visible: 7 });
});
