/**
 * R9 intent-side fail-first specs: recovery commit and acknowledgement coverage
 * (TASK-SKRIPT-40-04-14, ledger L13, design section 5).
 *
 * Row 4 (control): with no owned pieces, fresh data and history replace the
 * old display coherently — the visible copy, the undo position and the status
 * agree with the server. Passes today.
 *
 * Row 5: an owned patch already equal to fresh needs a real cursor-checked
 * confirmation store before the status reads saved. Fails today: the
 * content-equality shortcut reports stored with no POST.
 *
 * Row 6 (control): an older snapshot of the same generation acknowledged
 * after newer typing leaves the newer typing pending, stored next. Passes
 * today through the newer-typing follow-up.
 *
 * Row 7 (control, TK2 reuse): delayed normalisation with newer typing settles,
 * and after a second refusal plus recovery a remote-only q2 change is still
 * the other tab's value — it never becomes locally owned. Passes today.
 *
 * All rows drive the production editing session; doubles cover only
 * transport, clock, lease responses and server persistence. The seam the
 * design will change is the history store's confirmation rule: content
 * equality alone must not clear outstanding intent.
 */

import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import type { NativeExamDocument } from "../../../api/examWorkspace";
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
import {
  intentLeaseDouble,
  intentLeaseState,
  loseIntentLease,
  persistedPointsOf,
  pointsOf,
  reacquireIntentLease,
  remoteIntentWrite,
  resetIntentMocks,
  settleIntent,
  storeCallsOf,
} from "./useExamWorkspaceEditing.R9Intent.specSupport";

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

function leaseHeldError(): ApiError {
  return new ApiError({
    code: "EDIT_LEASE_HELD",
    message: "Provet redigeras i en annan flik.",
    status: 409,
  });
}

/** The q1/q2 points the n-th store POST carried. */
function postedPointsOf(apiMocks: EditingApiMocks, index: number): Array<number | null> {
  const call = apiMocks.storeExamWorkspaceUndoStep.mock.calls[index];
  if (!Array.isArray(call)) {
    throw new Error("expected a store call");
  }
  const request = call[1];
  if (typeof request !== "object" || request === null || !("document" in request)) {
    throw new Error("expected a store request document");
  }
  const document = request.document;
  if (typeof document !== "object" || document === null || !("items" in document)) {
    throw new Error("expected store document items");
  }
  const items = document.items;
  if (!Array.isArray(items)) {
    throw new Error("expected store document items");
  }
  return items.map((item) => {
    if (typeof item !== "object" || item === null || !("points" in item)) {
      throw new Error("expected a store item");
    }
    const points = item.points;
    if (typeof points !== "number" && points !== null) {
      throw new Error("expected item points");
    }
    return points;
  });
}

beforeEach(() => {
  vi.useFakeTimers();
  resetIntentMocks(api);
  for (const mock of Object.values(toast)) {
    mock.mockReset();
  }
});

afterEach(() => {
  stopScopes();
  vi.useRealTimers();
});

it("R9Intent row 4 (control): recovery with no owned piece installs fresh coherently", async () => {
  const baseline = exam();
  const server = fakeServer(api, baseline);
  const state = intentLeaseState();
  const editing = inScope(() =>
    useExamWorkspaceEditing(serverExamWorkspaceStore, nullRouteProjection(), {
      server: intentLeaseDouble(state),
      tabId: "A",
    }),
  );
  editing.applyCommandResponse(response(baseline, "step-0"));
  await settleIntent();

  await loseIntentLease(editing, state);
  state.holder = "B";
  remoteIntentWrite(server, "step-B", (document) => ({
    ...document,
    items: document.items.map((item) =>
      item.item_id === "item_002" ? { ...item, points: 9 } : item,
    ),
  }));
  await reacquireIntentLease(editing, state);

  expect(editing.editingLocked.value).toBe(false);
  expect({
    cursor: editing.historyCursor.value,
    persisted: persistedPointsOf(server),
    status: editing.history.saveStatus.value.state,
    stores: storeCallsOf(api),
    visible: pointsOf(editing.workspaceDocument.value),
  }).toEqual({
    cursor: "step-B",
    persisted: [2, 9],
    status: "saved",
    stores: 0,
    visible: [2, 9],
  });
});

it("R9Intent row 5: an owned patch equal to fresh still sends a confirmation store", async () => {
  const baseline = exam();
  const server = fakeServer(api, baseline);
  const state = intentLeaseState();
  const editing = inScope(() =>
    useExamWorkspaceEditing(serverExamWorkspaceStore, nullRouteProjection(), {
      server: intentLeaseDouble(state),
      tabId: "A",
    }),
  );
  editing.applyCommandResponse(response(baseline, "step-0"));
  await settleIntent();

  // A definite non-commit: the refused edit stays pending, read-only.
  state.holder = "B";
  api.storeExamWorkspaceUndoStep.mockRejectedValueOnce(leaseHeldError());
  editing.updateItemPoints("item_001", 7);
  expect(await editing.save()).toBe(false);
  expect(editing.leaseReadOnly.value).toBe(true);

  // The other tab happens to write the same q1 value plus its own q2 change.
  const storedA = server.documents.get(server.state.cursor);
  if (storedA === undefined) {
    throw new Error("expected the served document");
  }
  const storedB: NativeExamDocument = {
    ...storedA,
    items: storedA.items.map((item) => {
      if (item.item_id === "item_001") {
        return { ...item, points: 7 };
      }
      if (item.item_id === "item_002") {
        return { ...item, points: 9 };
      }
      return { ...item };
    }),
  };
  server.documents.set("step-B", storedB);
  server.state.steps.push("step-B");
  server.state.cursor = "step-B";
  server.state.position = "step-B";

  const storesBeforeRecovery = storeCallsOf(api);
  state.holder = "A";
  await editing.requestTakeover();
  await settleIntent();
  for (let attempt = 0; attempt < 30 && editing.editingLocked.value; attempt += 1) {
    await vi.advanceTimersByTimeAsync(1000);
    await settleIntent();
  }
  await settleIntent();

  expect({
    persisted: persistedPointsOf(server),
    status: editing.history.saveStatus.value.state,
    visible: pointsOf(editing.workspaceDocument.value),
  }).toEqual({ persisted: [7, 9], status: "saved", visible: [7, 9] });
  // The merged copy already equals fresh, yet saved requires a real store.
  expect(storeCallsOf(api) > storesBeforeRecovery).toBe(true);
});

it("R9Intent row 6 (control): an older snapshot ack keeps newer typing pending and stored next", async () => {
  const baseline = exam();
  const server = fakeServer(api, baseline);
  const state = intentLeaseState();
  const editing = inScope(() =>
    useExamWorkspaceEditing(serverExamWorkspaceStore, nullRouteProjection(), {
      server: intentLeaseDouble(state),
      tabId: "A",
    }),
  );
  editing.applyCommandResponse(response(baseline, "step-0"));
  await settleIntent();

  // The older [7,2] snapshot is held; newer typing to 8 arrives meanwhile.
  const persist = api.storeExamWorkspaceUndoStep.getMockImplementation();
  if (persist === undefined) {
    throw new Error("expected the step store double");
  }
  const ack = deferred<unknown>();
  const heldBox: { current: { lineage: string; request: unknown } | null } = { current: null };
  api.storeExamWorkspaceUndoStep.mockImplementationOnce((lineageId: string, request: unknown) => {
    heldBox.current = { lineage: lineageId, request };
    return ack.promise;
  });
  editing.updateItemPoints("item_001", 7);
  const saving = editing.save();
  await settleIntent();
  editing.updateItemPoints("item_001", 8);
  await vi.advanceTimersByTimeAsync(1000);
  await settleIntent();

  // The older snapshot is acknowledged after the newer typing: it commits,
  // and the newer copy is stored next instead of being cleared.
  const captured: { lineage: string; request: unknown } | null = heldBox.current;
  if (captured === null) {
    throw new Error("expected the held store");
  }
  ack.resolve(persist(captured.lineage, captured.request));
  expect(await saving).toBe(true);
  await settleIntent();
  for (let attempt = 0; attempt < 30 && editing.history.pending.value; attempt += 1) {
    await vi.advanceTimersByTimeAsync(1000);
    await settleIntent();
  }

  expect({
    lastPost: postedPointsOf(api, storeCallsOf(api) - 1),
    persisted: persistedPointsOf(server),
    status: editing.history.saveStatus.value.state,
    stores: storeCallsOf(api) >= 2,
    visible: pointsOf(editing.workspaceDocument.value),
  }).toEqual({
    lastPost: [8, 2],
    persisted: [8, 2],
    status: "saved",
    stores: true,
    visible: [8, 2],
  });
});

it("R9Intent row 7 (control): TK2 normalisation plus a second refusal keeps remote-only q2 newest", async () => {
  const baseline = exam();
  const server = fakeServer(api, baseline);
  const state = intentLeaseState();
  const editing = inScope(() =>
    useExamWorkspaceEditing(serverExamWorkspaceStore, nullRouteProjection(), {
      server: intentLeaseDouble(state),
      tabId: "A",
    }),
  );
  editing.applyCommandResponse(response(baseline, "step-0"));
  await settleIntent();

  // The server trims the title, as the backend tag rule normalises stores.
  const persist = api.storeExamWorkspaceUndoStep.getMockImplementation();
  if (persist === undefined) {
    throw new Error("expected the step store double");
  }
  type StoreRequest = {
    afterStepId: string | null;
    document: NativeExamDocument;
    expectedCursor: string;
  };
  const ack = deferred<unknown>();
  let holdFirst = true;
  const heldBox: { current: { lineage: string; request: StoreRequest } | null } = { current: null };
  api.storeExamWorkspaceUndoStep.mockImplementation(
    (lineageId: string, request: StoreRequest) => {
      if (holdFirst) {
        holdFirst = false;
        heldBox.current = { lineage: lineageId, request };
        return ack.promise;
      }
      const trimmed: NativeExamDocument = {
        ...request.document,
        title: request.document.title.trim(),
      };
      return persist(lineageId, { ...request, document: trimmed });
    },
  );

  // Delayed normalisation with newer typing: the held [7] store is
  // acknowledged after q1 moved to 8; the newer copy is stored next.
  editing.setTitle("Ny titel ");
  editing.updateItemPoints("item_001", 7);
  const firstSaving = editing.save();
  await settleIntent();
  editing.updateItemPoints("item_001", 8);
  await vi.advanceTimersByTimeAsync(1000);
  await settleIntent();
  const captured: { lineage: string; request: StoreRequest } | null = heldBox.current;
  if (captured === null) {
    throw new Error("expected the held store");
  }
  const trimmedSent: NativeExamDocument = {
    ...captured.request.document,
    title: captured.request.document.title.trim(),
  };
  ack.resolve(persist(captured.lineage, { ...captured.request, document: trimmedSent }));
  expect(await firstSaving).toBe(true);
  await settleIntent();
  for (let attempt = 0; attempt < 30 && editing.history.pending.value; attempt += 1) {
    await vi.advanceTimersByTimeAsync(1000);
    await settleIntent();
  }
  expect({
    persisted: persistedPointsOf(server),
    status: editing.history.saveStatus.value.state,
    title: editing.workspaceDocument.value?.title ?? null,
    visible: pointsOf(editing.workspaceDocument.value),
  }).toEqual({ persisted: [8, 2], status: "saved", title: "Ny titel", visible: [8, 2] });

  // First refusal and recovery: the other tab changes only q2.
  state.holder = "B";
  api.storeExamWorkspaceUndoStep.mockRejectedValueOnce(leaseHeldError());
  editing.updateItemPoints("item_001", 5);
  expect(await editing.save()).toBe(false);
  remoteIntentWrite(server, "step-C", (document) => ({
    ...document,
    items: document.items.map((item) =>
      item.item_id === "item_002" ? { ...item, points: 9 } : item,
    ),
  }));
  state.holder = "A";
  await editing.requestTakeover();
  await settleIntent();
  for (let attempt = 0; attempt < 30 && editing.editingLocked.value; attempt += 1) {
    await vi.advanceTimersByTimeAsync(1000);
    await settleIntent();
  }
  await settleIntent();
  expect({
    persisted: persistedPointsOf(server),
    status: editing.history.saveStatus.value.state,
    visible: pointsOf(editing.workspaceDocument.value),
  }).toEqual({ persisted: [5, 9], status: "saved", visible: [5, 9] });

  // Second refusal and recovery: the other tab moves q2 again. The
  // remote-only q2 value was never locally owned, so it stays newest.
  state.holder = "B";
  api.storeExamWorkspaceUndoStep.mockRejectedValueOnce(leaseHeldError());
  editing.updateItemPoints("item_001", 6);
  expect(await editing.save()).toBe(false);
  remoteIntentWrite(server, "step-D", (document) => ({
    ...document,
    items: document.items.map((item) =>
      item.item_id === "item_002" ? { ...item, points: 4 } : item,
    ),
  }));
  state.holder = "A";
  await editing.requestTakeover();
  await settleIntent();
  for (let attempt = 0; attempt < 30 && editing.editingLocked.value; attempt += 1) {
    await vi.advanceTimersByTimeAsync(1000);
    await settleIntent();
  }
  await settleIntent();
  expect({
    persisted: persistedPointsOf(server),
    status: editing.history.saveStatus.value.state,
    visible: pointsOf(editing.workspaceDocument.value),
  }).toEqual({ persisted: [6, 4], status: "saved", visible: [6, 4] });
});
