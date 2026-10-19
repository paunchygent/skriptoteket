/**
 * Exam workspace replacing lock: live-scope accounting (TASK-SKRIPT-40-04-14,
 * rereview S2 of 2f4f121d).
 *
 * Expected behavior:
 *   - Two overlapping `replaceCopy` scopes share one lock epoch: the first
 *     scope to exit must not release the lock while the other scope is still
 *     live, in either completion order. Editing stays refused until the last
 *     live scope exits.
 *   - A properly awaited nested scope keeps sharing the outer lock: the lock
 *     holds while the inner scope runs and releases when the outer scope ends.
 *
 * The scopes run on the production editing session, so the hold covers the
 * real arrival and keying bindings; the test observes the public replacing
 * flag and edit refusal.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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

afterEach(stopScopes);

function leaseHeld(): Error {
  return new Error("lease held elsewhere");
}

function deferredUnit(): { promise: Promise<void>; resolve: () => void } {
  let resolveFn: (() => void) | null = null;
  const promise = new Promise<void>((resolve) => {
    resolveFn = resolve;
  });
  return {
    promise,
    resolve: () => {
      if (resolveFn !== null) {
        resolveFn();
      }
    },
  };
}

function pointsOf(editing: ReturnType<typeof useExamWorkspaceEditing>, itemId: string): number | null {
  const workspace = editing.workspaceDocument.value;
  if (workspace === null) {
    throw new Error("expected an open document");
  }
  const found = workspace.items.find((item) => item.item_id === itemId);
  if (found === undefined) {
    throw new Error(`expected ${itemId}`);
  }
  return found.points;
}

async function openHolding(): Promise<ReturnType<typeof useExamWorkspaceEditing>> {
  const baseline = exam();
  fakeServer(api, baseline);
  const editing = inScope(() =>
    useExamWorkspaceEditing(serverExamWorkspaceStore, {
      server: {
        claim: async () => ({
          holder_tab_id: "tab-A",
          renewed_at: "2026-10-19T12:00:00.000Z",
          takeover_requested: false,
          takeover_requested_by: null,
        }),
        release: async () => ({
          holder_tab_id: "tab-A",
          renewed_at: "2026-10-19T12:00:00.000Z",
          takeover_requested: false,
          takeover_requested_by: null,
        }),
        renew: async () => ({
          holder_tab_id: "tab-A",
          renewed_at: "2026-10-19T12:00:00.000Z",
          takeover_requested: false,
          takeover_requested_by: null,
        }),
        requestTakeover: async () => {
          throw leaseHeld();
        },
      },
      tabId: "tab-A",
    }),
  );
  editing.applyCommandResponse(response(baseline, "step-0"));
  await flushPromises();
  return editing;
}

describe("overlapping replacing scopes", () => {
  it("holds the lock until the last live scope exits when the first ends first", async () => {
    const editing = await openHolding();
    const firstGate = deferredUnit();
    const secondGate = deferredUnit();
    const first = editing.replaceCopy(() => firstGate.promise);
    const second = editing.replaceCopy(() => secondGate.promise);
    expect(editing.isReplacing.value).toBe(true);

    firstGate.resolve();
    await first;
    expect(editing.isReplacing.value).toBe(true);
    editing.updateItemPoints("item_001", 8);
    expect(pointsOf(editing, "item_001")).toBe(2);

    secondGate.resolve();
    await second;
    expect(editing.isReplacing.value).toBe(false);
    editing.updateItemPoints("item_001", 8);
    expect(pointsOf(editing, "item_001")).toBe(8);
  });

  it("holds the lock until the last live scope exits when the second ends first", async () => {
    const editing = await openHolding();
    const firstGate = deferredUnit();
    const secondGate = deferredUnit();
    const first = editing.replaceCopy(() => firstGate.promise);
    const second = editing.replaceCopy(() => secondGate.promise);
    expect(editing.isReplacing.value).toBe(true);

    secondGate.resolve();
    await second;
    expect(editing.isReplacing.value).toBe(true);
    editing.updateItemPoints("item_001", 8);
    expect(pointsOf(editing, "item_001")).toBe(2);

    firstGate.resolve();
    await first;
    expect(editing.isReplacing.value).toBe(false);
    editing.updateItemPoints("item_001", 8);
    expect(pointsOf(editing, "item_001")).toBe(8);
  });
});

describe("a properly awaited nested replacing scope", () => {
  it("shares the outer lock and releases it with the outer scope", async () => {
    const editing = await openHolding();
    const gate = deferredUnit();
    const outer = editing.replaceCopy(async () => {
      await editing.replaceCopy(async () => undefined);
      expect(editing.isReplacing.value).toBe(true);
      await gate.promise;
    });
    await flushPromises();
    expect(editing.isReplacing.value).toBe(true);
    gate.resolve();
    await outer;
    expect(editing.isReplacing.value).toBe(false);
  });
});
