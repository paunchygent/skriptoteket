/**
 * R2: redo survives a reload (frontend regression).
 *
 * Mounts the production history from a history response whose position sits
 * behind its newest step (the server state after an undo): Gör om is
 * enabled, moves forward, and is disabled at the newest. A second mount
 * from the reloaded history (same server position) agrees.
 */
import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { effectScope, ref } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { NativeExamDocument } from "../../../api/examWorkspace";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { useExamWorkspaceHistory } from "./useExamWorkspaceHistory";

const apiMocks = vi.hoisted(() => ({
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));
vi.mock("../../../api/examWorkspace", () => apiMocks);

function documents(): { one: NativeExamDocument; two: NativeExamDocument } {
  const baseline = buildParentDocument();
  return { one: { ...baseline, title: "one" }, two: { ...baseline, title: "two" } };
}

function mountFromHistory(
  history: { baseline_step_id: string; cursor: string; position_step_id: string; step_ids: string[] },
  document: NativeExamDocument,
) {
  apiMocks.getExamWorkspaceHistory.mockResolvedValue(history);
  const workspaceDocument = ref<NativeExamDocument | null>(document);
  const serverDocument = ref<NativeExamDocument | null>(document);
  const historyCursor = ref<string | null>(history.cursor);
  const historyState = effectScope().run(() =>
    useExamWorkspaceHistory({
      historyCursor,
      install: (next) => {
        workspaceDocument.value = next;
      },
      isBlocked: () => false,
      isGuest: () => false,
      isReadOnly: () => false,
      isReplacing: () => false,
      replaceCopy: (run) => run(),
      lineageId: () => "lineage-1",
      noteExportBlockers: vi.fn(),
      noteLeaseLost: vi.fn(),
      noteStored: vi.fn(),
      onConflict: vi.fn(async () => undefined),
      savedRevision: () => 1,
      serverDocument,
      shared: serverExamWorkspaceStore.shared,
      tabId: () => "tab-1",
      workspaceDocument,
    }),
  )!;
  return { historyState, workspaceDocument };
}

beforeEach(() => {
  setActivePinia(createPinia());
  for (const mock of Object.values(apiMocks)) mock.mockReset();
  apiMocks.getExamWorkspaceHistoryStep.mockRejectedValue(new Error("no step reads in R2"));
});
afterEach(() => {
  vi.useRealTimers();
});

describe("R2 redo across a reload", () => {
  it("mounts behind the newest step with Gör om enabled", async () => {
    const { one } = documents();
    const { historyState } = mountFromHistory(
      { baseline_step_id: "step-0", cursor: "move-1", position_step_id: "step-1", step_ids: ["step-1", "step-2"] },
      one,
    );
    await flushPromises();
    await flushPromises();
    expect(historyState.position.value).toBe("step-1");
    expect(historyState.canRedo.value).toBe(true);
    expect(historyState.canUndo.value).toBe(true);
  });

  it("Gör om moves forward and is disabled at the newest", async () => {
    const { one, two } = documents();
    apiMocks.moveExamWorkspaceHistoryPosition.mockResolvedValue({
      document: two,
      export_blockers: [],
      history: { baseline_step_id: "step-0", cursor: "move-2", position_step_id: "step-2", step_ids: ["step-1", "step-2"] },
    });
    const { historyState, workspaceDocument } = mountFromHistory(
      { baseline_step_id: "step-0", cursor: "move-1", position_step_id: "step-1", step_ids: ["step-1", "step-2"] },
      one,
    );
    await flushPromises();
    await flushPromises();
    await historyState.redo();
    expect(apiMocks.moveExamWorkspaceHistoryPosition).toHaveBeenCalledOnce();
    expect(workspaceDocument.value!.title).toBe("two");
    expect(historyState.position.value).toBe("step-2");
    expect(historyState.canRedo.value).toBe(false);
  });

  it("a reloaded mount from the same server position agrees", async () => {
    const { one, two } = documents();
    apiMocks.moveExamWorkspaceHistoryPosition.mockResolvedValue({
      document: two,
      export_blockers: [],
      history: { baseline_step_id: "step-0", cursor: "move-2", position_step_id: "step-2", step_ids: ["step-1", "step-2"] },
    });
    const first = mountFromHistory(
      { baseline_step_id: "step-0", cursor: "move-1", position_step_id: "step-1", step_ids: ["step-1", "step-2"] },
      one,
    );
    await flushPromises();
    await flushPromises();
    await first.historyState.redo();
    const reloadedHistory = {
      baseline_step_id: "step-0",
      cursor: "move-2",
      position_step_id: "step-2",
      step_ids: ["step-1", "step-2"],
    };
    const second = mountFromHistory(reloadedHistory, two);
    await flushPromises();
    await flushPromises();
    expect(second.historyState.position.value).toBe("step-2");
    expect(second.historyState.canRedo.value).toBe(false);
    expect(second.historyState.canUndo.value).toBe(true);
  });
});
