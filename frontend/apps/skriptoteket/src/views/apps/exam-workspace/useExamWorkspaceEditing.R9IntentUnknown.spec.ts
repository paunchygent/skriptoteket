/**
 * R9 intent-side fail-first specs: unknown-result lifetime (TASK-SKRIPT-40-04-14,
 * ledger L13, design section 5 "Unknown-result lifetime").
 *
 * Row 1: confirmed [2,2], a store of [7,2] whose transport rejects (the answer
 * is unknown and the store is no longer in flight), a revert of q1 to 2, lease
 * loss past the 15 s TTL, another tab legitimately writing q2=9 and releasing,
 * then reacquisition. The design records q1 as published-but-unconfirmed, so
 * visible and persisted end at [2,9], and the status reads saved only after a
 * confirming store. Fails today: the rejected answer leaves no ownership, so
 * recovery installs the fresh [7,9] with no confirming store.
 *
 * Row 2 (contrast control): an edit of q1 to 7 and back to 2 that was never
 * sent claims no ownership, so the same remote q2=9 recovery ends at the
 * newest [2,9] with no store, and a later remote q1=5 stays 5. Passes today.
 *
 * Both rows drive the production editing session; doubles cover only
 * transport, clock, lease responses and server persistence.
 */

import { afterEach, beforeEach, expect, it, vi } from "vitest";

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

function withQ2(
  document: NativeExamDocument,
  points: number | null,
): NativeExamDocument {
  return {
    ...document,
    items: document.items.map((item) =>
      item.item_id === "item_002" ? { ...item, points } : item,
    ),
  };
}

function withQ1(
  document: NativeExamDocument,
  points: number | null,
): NativeExamDocument {
  return {
    ...document,
    items: document.items.map((item) =>
      item.item_id === "item_001" ? { ...item, points } : item,
    ),
  };
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

it("R9Intent row 1: a rejected store plus remote edit retains the revert", async () => {
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

  // The [7,2] store commits on the server but its transport answer rejects:
  // the outcome is unknown and the store is no longer in flight.
  const persist = api.storeExamWorkspaceUndoStep.getMockImplementation();
  if (persist === undefined) {
    throw new Error("expected the step store double");
  }
  api.storeExamWorkspaceUndoStep.mockImplementationOnce(
    async (lineageId: string, request: unknown) => {
      if (typeof lineageId !== "string") {
        throw new Error("expected a lineage id");
      }
      await persist(lineageId, request);
      throw new TypeError("network unavailable");
    },
  );
  // The revert's confirmation store never reaches the server either, so q1
  // stays unresolved into the lease loss.
  api.storeExamWorkspaceUndoStep.mockImplementationOnce(async () => {
    throw new TypeError("network unavailable");
  });
  editing.updateItemPoints("item_001", 7);
  expect(await editing.save()).toBe(false);
  editing.updateItemPoints("item_001", 2);
  await settleIntent();

  const storesBeforeRecovery = storeCallsOf(api);
  await loseIntentLease(editing, state);
  state.holder = "B";
  remoteIntentWrite(server, "step-B", (document) => withQ2(document, 9));
  await reacquireIntentLease(editing, state);

  expect(editing.editingLocked.value).toBe(false);
  await editing.save();
  await settleIntent();
  // The design's per-piece intent keeps q1=2 against the fresh [7,9].
  expect({
    persisted: persistedPointsOf(server),
    status: editing.history.saveStatus.value.state,
    visible: pointsOf(editing.workspaceDocument.value),
  }).toEqual({ persisted: [2, 9], status: "saved", visible: [2, 9] });
  // Saved only after a confirming store: recovery must have posted again.
  expect(storeCallsOf(api) > storesBeforeRecovery).toBe(true);
});

it("R9Intent row 2 (control): an edit-and-revert never sent claims nothing", async () => {
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

  // Never sent: the pause flush finds the working copy back at the baseline.
  editing.updateItemPoints("item_001", 7);
  editing.updateItemPoints("item_001", 2);
  await settleIntent();

  await loseIntentLease(editing, state);
  state.holder = "B";
  remoteIntentWrite(server, "step-B1", (document) => withQ2(document, 9));
  await reacquireIntentLease(editing, state);

  expect(editing.editingLocked.value).toBe(false);
  expect({
    persisted: persistedPointsOf(server),
    status: editing.history.saveStatus.value.state,
    visible: pointsOf(editing.workspaceDocument.value),
  }).toEqual({ persisted: [2, 9], status: "saved", visible: [2, 9] });
  expect(storeCallsOf(api)).toBe(0);

  // A remote change to the unowned q1 stays newest as well.
  await loseIntentLease(editing, state);
  state.holder = "B";
  remoteIntentWrite(server, "step-B2", (document) => withQ1(document, 5));
  await reacquireIntentLease(editing, state);

  expect({
    persisted: persistedPointsOf(server),
    visible: pointsOf(editing.workspaceDocument.value),
  }).toEqual({ persisted: [5, 9], visible: [5, 9] });
  expect(storeCallsOf(api)).toBe(0);
});
