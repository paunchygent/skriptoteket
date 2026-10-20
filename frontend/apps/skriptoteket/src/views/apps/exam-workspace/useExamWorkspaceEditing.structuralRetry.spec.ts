/**
 * Exam workspace editing session: the structural autosave retry (TASK-SKRIPT-40-04-14,
 * unit FF fail-first port of rereview-4 U4).
 *
 * Ported from the reviewer's failing probe, kept scenario-for-scenario with a
 * truthful name. It drives the public editing session (`structure.addItem`)
 * and asserts the store count across the contracted five seconds.
 *
 * Probe source (read-only, not edited): gate-boundaries.spec.mjs.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
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

describe("the structural autosave retry fail-first port", () => {
  it("a first failed structural autosave retries the newest copy after five seconds without another edit", async () => {
    vi.useFakeTimers();
    const base = exam();
    fakeServer(api, base);
    const editing = inScope(() =>
      useExamWorkspaceEditing(serverExamWorkspaceStore, {
        server: {
          claim: async () => ({
            holder_tab_id: "A",
            renewed_at: "2026-10-20T00:30:00Z",
            takeover_requested: false,
            takeover_requested_by: null,
          }),
          release: async () => ({
            holder_tab_id: "A",
            renewed_at: "2026-10-20T00:30:00Z",
            takeover_requested: false,
            takeover_requested_by: null,
          }),
          requestTakeover: async () => ({
            holder_tab_id: "A",
            renewed_at: "2026-10-20T00:30:00Z",
            takeover_requested: false,
            takeover_requested_by: null,
          }),
          renew: async () => ({
            holder_tab_id: "A",
            renewed_at: "2026-10-20T00:30:00Z",
            takeover_requested: false,
            takeover_requested_by: null,
          }),
        },
        tabId: "A",
      }),
    );
    editing.applyCommandResponse(response(base, "step-0"));
    await flushPromises();
    api.storeExamWorkspaceUndoStep.mockRejectedValueOnce(
      new ApiError({ code: "RATE_LIMITED", message: "limited", status: 429 }),
    );
    editing.structure.addItem("free_text");
    await flushPromises();
    expect(api.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(1);
    expect(editing.history.saveStatus.value.state).toBe("unsaved");
    await vi.advanceTimersByTimeAsync(5000);
    await flushPromises();
    expect(api.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(2);
  });
});
