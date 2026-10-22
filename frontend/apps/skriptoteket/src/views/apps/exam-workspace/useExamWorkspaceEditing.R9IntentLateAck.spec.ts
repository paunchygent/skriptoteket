/**
 * R9 intent-side fail-first spec: late acknowledgement after recovery
 * (TASK-SKRIPT-40-04-14, ledger L13, design section 5 "Recovery commit and
 * acknowledgement coverage").
 *
 * Row 8: a plain kept edit (no revert, so recovery itself is correct today)
 * merges onto the other tab's q2 change and confirms through a real store.
 * The old store's acknowledgement, delivered only after that recovery, must
 * change nothing visible, persisted, or in the status: it has no authority
 * once its intent was retired and re-confirmed.
 *
 * Drives the production editing session; doubles cover only transport, clock,
 * lease responses and server persistence. The seam the design will change is
 * the acknowledgement admission: attempt identity and remaining intent decide,
 * never the fence generation alone.
 */

import { afterEach, beforeEach, expect, it, vi } from "vitest";

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

it("R9Intent row 8: the old store ack delivered after recovery changes nothing", async () => {
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

  // The [7,2] store commits but its acknowledgement is held past recovery.
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

  await editing.save();
  await settleIntent();
  expect({
    persisted: persistedPointsOf(server),
    status: editing.history.saveStatus.value.state,
    visible: pointsOf(editing.workspaceDocument.value),
  }).toEqual({ persisted: [7, 9], status: "saved", visible: [7, 9] });

  // The old acknowledgement arrives only now: nothing may move.
  const cursorAfterRecovery = editing.historyCursor.value;
  const storesAfterRecovery = storeCallsOf(api);
  ack.resolve(stored);
  await saving;
  await settleIntent();
  await vi.advanceTimersByTimeAsync(6000);
  await settleIntent();

  expect({
    cursor: editing.historyCursor.value,
    persisted: persistedPointsOf(server),
    status: editing.history.saveStatus.value.state,
    stores: storeCallsOf(api),
    visible: pointsOf(editing.workspaceDocument.value),
  }).toEqual({
    cursor: cursorAfterRecovery,
    persisted: [7, 9],
    status: "saved",
    stores: storesAfterRecovery,
    visible: [7, 9],
  });
});
