/**
 * Exam workspace editing session: typing negative points refuses the save
 * (TASK-SKRIPT-40-04-14, C3 and the `unsaved-rule.png` evidence defect).
 *
 * Expected behavior:
 *   Typing −1 into points through the real editing session refuses the
 *   store locally: no request reaches the server and the status reads
 *   `Inte sparat` with `<list label> har negativa poäng. Ange 0 poäng eller
 *   mer.` at once, so the status can never read `Sparat` while the refused
 *   edit is pending.
 *
 * Transport is a named double of the server's step store plus a lease
 * double that holds the edit lease, so the session is writable; the
 * composables are the production ones.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ExamWorkspaceEditLeaseResponse } from "../../../api/examWorkspace";
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

afterEach(stopScopes);

function heldLease(tabId: string) {
  const lease: ExamWorkspaceEditLeaseResponse = {
    holder_tab_id: tabId,
    renewed_at: null,
    takeover_requested: false,
    takeover_requested_by: null,
  };
  return {
    claim: async () => lease,
    release: async () => lease,
    renew: async () => lease,
    requestTakeover: async () => lease,
  };
}

describe("typing negative points", () => {
  it("refuses the save locally and reads Inte sparat with the points reason", async () => {
    const baseline = exam();
    fakeServer(api, baseline);
    const editing = inScope(() =>
      useExamWorkspaceEditing(serverExamWorkspaceStore, nullRouteProjection(), {
        server: heldLease("tab-cp1"),
        tabId: "tab-cp1",
      }),
    );
    // The lease reclaim after the open reads the newest document before the
    // gate reaches editing.
    api.getExamWorkspaceDocument.mockImplementation(async () => response(baseline, "step-0"));
    editing.applyCommandResponse(response(baseline, "step-0"));
    for (let attempt = 0; attempt < 50 && editing.editingLocked.value; attempt += 1) {
      await flushPromises();
    }
    expect(editing.editingLocked.value).toBe(false);

    editing.updateItemPoints("item_001", -1);
    expect(editing.workspaceDocument.value!.items[0]!.points).toBe(-1);

    await editing.save();

    expect(api.storeExamWorkspaceUndoStep).not.toHaveBeenCalled();
    expect(editing.history.saveStatus.value).toEqual({
      state: "unsaved",
      detail: "Fråga 1 har negativa poäng. Ange 0 poäng eller mer.",
    });
  });
});
