/**
 * Exam workspace editing session: the save status never reads Sparat while a
 * kept edit is unstored (TASK-SKRIPT-40-04-14, unit KS part 1).
 *
 * Expected behavior:
 *   An edit is refused with EDIT_LEASE_HELD, so the gate keeps it and the
 *   status reads Inte sparat with the lease reason. Then the tab takes over
 *   and the fresh load's history GET fails. The loader's failure reset clears
 *   the step document, but the status must still never read Sparat while the
 *   kept edit has not been stored: it keeps Inte sparat with the lease reason
 *   until the merged store succeeds, then reads Sparat.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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

afterEach(() => {
  stopScopes();
  vi.useRealTimers();
});

function leaseHeld(): ApiError {
  return new ApiError({
    code: "EDIT_LEASE_HELD",
    message: "Provet redigeras i en annan flik.",
    status: 409,
  });
}

function leaseResponse(holder: string): ExamWorkspaceEditLeaseResponse {
  return {
    holder_tab_id: holder,
    renewed_at: "2026-10-19T12:00:00.000Z",
    takeover_requested: false,
    takeover_requested_by: null,
  };
}

function pointsOf(document: NativeExamDocument, itemId: string): number | null {
  const found = document.items.find((item) => item.item_id === itemId);
  if (found === undefined) {
    throw new Error(`expected ${itemId}`);
  }
  return found.points;
}

describe("the save status with an unstored kept edit", () => {
  it("never reads Sparat from the refusal until the merged store succeeds", async () => {
    vi.useFakeTimers();
    const baseline = exam();
    const server = fakeServer(api, baseline);
    const holder = { current: "tab-A" };
    const editing = inScope(() =>
      useExamWorkspaceEditing(serverExamWorkspaceStore, nullRouteProjection(), {
        server: {
          claim: async () => {
            if (holder.current !== "tab-A") {
              throw leaseHeld();
            }
            return leaseResponse("tab-A");
          },
          release: async () => leaseResponse(holder.current),
          renew: async () => {
            if (holder.current !== "tab-A") {
              throw leaseHeld();
            }
            return leaseResponse("tab-A");
          },
          requestTakeover: async () => leaseResponse("tab-B"),
        },
        tabId: "tab-A",
      }),
    );
    editing.applyCommandResponse(response(baseline, "step-0"));
    await flushPromises();

    // The status is sampled after every step and every flush. Until the
    // merged store is sent, no sample may read Sparat; afterwards Sparat is
    // legitimate, so the flag below lifts the check once the store is sent
    // (the kept edit still pins Inte sparat while that store is in flight).
    const seen: string[] = [];
    let mergedStoreSent = false;
    function sample(): void {
      const text = editing.history.saveText.value;
      seen.push(text);
      if (!mergedStoreSent) {
        expect(text).not.toMatch(/^Sparat/);
      }
    }

    editing.updateItemPoints("item_001", 5);
    expect(await editing.save()).toBe(true);
    // The clean state reads Sparat; the rule below covers only the span in
    // which the gate holds an unstored kept edit, so sampling starts at the
    // refusal.
    seen.length = 0;

    // The other tab takes the lease: this tab's next store is refused with
    // EDIT_LEASE_HELD, the gate keeps the edit, and the status leaves
    // Sparat for Inte sparat with the lease reason.
    holder.current = "tab-B";
    api.storeExamWorkspaceUndoStep.mockRejectedValueOnce(leaseHeld());
    editing.updateItemPoints("item_001", 7);
    expect(await editing.save()).toBe(false);
    await flushPromises();
    sample();
    expect(editing.history.saveText.value).toBe("Inte sparat");

    // The other tab meanwhile stores a change to question 2.
    const saved = server.documents.get(server.state.cursor);
    if (saved === undefined) {
      throw new Error("expected tab A's stored step");
    }
    const other: NativeExamDocument = {
      ...saved,
      items: saved.items.map((item) =>
        item.item_id === "item_002" ? { ...item, points: 9 } : item,
      ),
    };
    server.documents.set("step-B", other);
    server.state.steps = [...server.state.steps, "step-B"];
    server.state.cursor = "step-B";
    server.state.position = "step-B";

    // The tab takes over, but the fresh load's history GET fails.
    api.getExamWorkspaceDocument.mockImplementation(async () =>
      response(JSON.parse(JSON.stringify(other)), "step-B"),
    );
    api.getExamWorkspaceHistory.mockRejectedValue(new Error("history unavailable"));
    holder.current = "tab-A";
    const taking = editing.requestTakeover();
    let taken = false;
    void taking.then(() => {
      taken = true;
    });
    for (let attempt = 0; attempt < 20 && !taken; attempt += 1) {
      await vi.advanceTimersByTimeAsync(1000);
      await flushPromises();
      sample();
    }
    await taking;
    await flushPromises();
    sample();

    // The kept edit is still unstored. The failed read cleared the step list,
    // so the history's pending flag reads false (the gate, not that flag,
    // carries the kept edit) — but the status must still keep Inte sparat
    // with the lease reason instead of reading Sparat.
    expect(editing.history.pending.value).toBe(false);
    expect(editing.history.saveText.value).toBe("Inte sparat");

    // The history recovers: the retry merges the kept edit at the merge point
    // and stores it through the normal save path.
    const storesBefore = api.storeExamWorkspaceUndoStep.mock.calls.length;
    api.getExamWorkspaceHistory.mockImplementation(async () => ({
      baseline_step_id: "step-0",
      cursor: server.state.cursor,
      position_step_id: server.state.position,
      step_ids: [...server.state.steps],
    }));
    for (
      let attempt = 0;
      attempt < 20 && api.storeExamWorkspaceUndoStep.mock.calls.length === storesBefore;
      attempt += 1
    ) {
      await vi.advanceTimersByTimeAsync(1000);
      await flushPromises();
      mergedStoreSent = api.storeExamWorkspaceUndoStep.mock.calls.length > storesBefore;
      sample();
    }
    await flushPromises();
    sample();
    for (let attempt = 0; attempt < 20 && editing.editingLocked.value; attempt += 1) {
      await vi.advanceTimersByTimeAsync(1000);
      await flushPromises();
      sample();
    }

    const workspace = editing.workspaceDocument.value;
    if (workspace === null) {
      throw new Error("expected an open document");
    }
    expect(pointsOf(workspace, "item_001")).toBe(7);
    expect(pointsOf(workspace, "item_002")).toBe(9);
    expect(editing.history.pending.value).toBe(false);
    expect(editing.history.saveText.value).toMatch(/^Sparat \d{2}:\d{2}$/);
    expect(seen.length).toBeGreaterThan(0);
  });
});
