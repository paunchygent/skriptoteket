/**
 * Exam workspace Förhandsgranska follows the persisted editor state (TASK-SKRIPT-40-04-07, W5; R3).
 *
 * Expected behavior:
 *   A real Skrivyta edit stored as an undo step — not a saved revision bump —
 *   moves the persisted history cursor, and the open preview renders the stored
 *   working state after its debounce with that new cursor and the unchanged
 *   saved revision. Transport is the named double of the server's step store
 *   and a bound preview fetch double; the editing and preview composables are
 *   the production ones.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { computed, effectScope, nextTick, ref } from "vue";

import { exam, LINEAGE, openEditing, stopScopes } from "./useExamWorkspaceEditing.history.specSupport";
import { PREVIEW_DEBOUNCE_MS, useExamWorkspacePrintPreview } from "./useExamWorkspacePrintPreview";

const api = vi.hoisted(() => ({
  changeExamWorkspaceItemType: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));
const previewApi = vi.hoisted(() => ({ fetchExamWorkspacePrintPreview: vi.fn() }));
const toast = vi.hoisted(() => ({ failure: vi.fn(), warning: vi.fn() }));

vi.mock("../../../api/examWorkspace", async (original) => ({
  ...(await original<typeof import("../../../api/examWorkspace")>()),
  ...api,
}));
vi.mock("../../../api/examWorkspaceExports", () => previewApi);
vi.mock("../../../composables/useToast", () => ({ useToast: () => toast }));

function ready(pages: string[]) {
  return { message: null, pages, question_pages: {}, revision: 1, status: "ready" as const };
}

async function elapse(ms: number): Promise<void> {
  await vi.advanceTimersByTimeAsync(ms);
  await flushPromises();
}

beforeEach(() => {
  for (const fn of [...Object.values(api), ...Object.values(previewApi), ...Object.values(toast)]) {
    fn.mockReset();
  }
  vi.useFakeTimers();
});

afterEach(() => {
  stopScopes();
  vi.useRealTimers();
});

describe("the preview follows the persisted history cursor after a real edit (R3)", () => {
  it("re-renders the stored Skrivyta edit with its new cursor and the unchanged saved revision", async () => {
    previewApi.fetchExamWorkspacePrintPreview.mockResolvedValue(ready(["page-1"]));
    const { editing, server } = await openEditing(api);
    expect(editing.historyCursor.value).toBe("step-0");
    expect(editing.savedRevision.value).toBe(1);

    const open = ref(true);
    const scope = effectScope();
    const preview = scope.run(() =>
      useExamWorkspacePrintPreview({
        historyCursor: editing.historyCursor,
        historyPosition: editing.history.position,
        lineageId: computed(() => editing.summary.value?.lineage_id ?? null),
        open,
        savedRevision: editing.savedRevision,
        selectedItemId: editing.selectedItemId,
      }),
    );
    if (!preview) throw new Error("preview composable did not mount");
    await nextTick();
    await elapse(PREVIEW_DEBOUNCE_MS);
    expect(previewApi.fetchExamWorkspacePrintPreview).toHaveBeenCalledWith(LINEAGE, 1, "step-0", "step-0");
    expect(preview.pages.value).toEqual(["page-1"]);

    // A real Skrivyta stepper click: one structural undo step, and the saved file does not move.
    previewApi.fetchExamWorkspacePrintPreview.mockResolvedValueOnce(ready(["page-2"]));
    editing.updateItemWritingLines("item_001", 9);
    await elapse(0);
    expect(server.state.cursor).toBe("step-1");
    expect(editing.savedRevision.value).toBe(1);

    await elapse(PREVIEW_DEBOUNCE_MS);
    expect(previewApi.fetchExamWorkspacePrintPreview).toHaveBeenLastCalledWith(LINEAGE, 1, "step-1", "step-1");
    expect(preview.pages.value).toEqual(["page-2"]);
    scope.stop();
  });

  it("re-renders after Använd för alla fritextfrågor with its own new cursor", async () => {
    previewApi.fetchExamWorkspacePrintPreview.mockResolvedValue(ready(["page-1"]));
    const { editing } = await openEditing(api, exam("Original", 2));

    const open = ref(true);
    const scope = effectScope();
    const preview = scope.run(() =>
      useExamWorkspacePrintPreview({
        historyCursor: editing.historyCursor,
        historyPosition: editing.history.position,
        lineageId: computed(() => editing.summary.value?.lineage_id ?? null),
        open,
        savedRevision: editing.savedRevision,
        selectedItemId: editing.selectedItemId,
      }),
    );
    if (!preview) throw new Error("preview composable did not mount");
    await nextTick();
    await elapse(PREVIEW_DEBOUNCE_MS);

    previewApi.fetchExamWorkspacePrintPreview.mockResolvedValueOnce(ready(["page-2"]));
    editing.applyWritingLinesToAllFreeText(9);
    await elapse(0);
    const storedCursor = editing.historyCursor.value;
    expect(storedCursor).toBe("step-1");

    await elapse(PREVIEW_DEBOUNCE_MS);
    expect(previewApi.fetchExamWorkspacePrintPreview).toHaveBeenLastCalledWith(LINEAGE, 1, storedCursor, "step-1");
    expect(preview.pages.value).toEqual(["page-2"]);
    scope.stop();
  });

  it("re-renders the retained step the editor stands on after undo and redo", async () => {
    const { editing, server } = await openEditing(api);
    const baselineLines = editing.workspaceDocument.value!.items[0]!.writing_lines;
    previewApi.fetchExamWorkspacePrintPreview.mockImplementation(
      async (_lineage: string, _revision: number, _cursor: string, stepId: string) =>
        ready([`writing-lines:${server.documents.get(stepId)!.items[0]!.writing_lines}`]),
    );

    const open = ref(true);
    const scope = effectScope();
    const preview = scope.run(() =>
      useExamWorkspacePrintPreview({
        historyCursor: editing.historyCursor,
        historyPosition: editing.history.position,
        lineageId: computed(() => editing.summary.value?.lineage_id ?? null),
        open,
        savedRevision: editing.savedRevision,
        selectedItemId: editing.selectedItemId,
      }),
    );
    if (!preview) throw new Error("preview composable did not mount");
    await nextTick();
    await elapse(PREVIEW_DEBOUNCE_MS);
    expect(preview.pages.value).toEqual([`writing-lines:${baselineLines}`]);

    editing.updateItemWritingLines("item_001", 9);
    await elapse(0);
    await elapse(PREVIEW_DEBOUNCE_MS);
    expect(preview.pages.value).toEqual(["writing-lines:9"]);

    await editing.history.undo();
    await nextTick();
    expect(editing.history.position.value).toBe("step-0");
    await elapse(PREVIEW_DEBOUNCE_MS);
    expect(previewApi.fetchExamWorkspacePrintPreview).toHaveBeenLastCalledWith(
      LINEAGE,
      1,
      editing.historyCursor.value,
      "step-0",
    );
    expect(preview.pages.value).toEqual([`writing-lines:${baselineLines}`]);

    await editing.history.redo();
    await nextTick();
    expect(editing.history.position.value).toBe("step-1");
    await elapse(PREVIEW_DEBOUNCE_MS);
    expect(previewApi.fetchExamWorkspacePrintPreview).toHaveBeenLastCalledWith(
      LINEAGE,
      1,
      editing.historyCursor.value,
      "step-1",
    );
    expect(preview.pages.value).toEqual(["writing-lines:9"]);
    scope.stop();
  });
});
