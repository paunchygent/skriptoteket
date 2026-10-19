/**
 * Exam workspace Förhandsgranska composable (TASK-SKRIPT-40-04-07, W5).
 *
 * Expected behavior:
 *   The panel renders nothing while closed, renders once for a burst of
 *   persisted history-cursor changes, ignores a response an older request left
 *   behind, keeps the last ready pages while the exam is blocked or a request
 *   fails, and reports a failure once. A 409 (the persisted state moved on) is
 *   dropped silently. Disposing the owning scope cancels the scheduled render
 *   and drops every pending answer without applying it or raising a toast.
 */

import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope, nextTick, ref } from "vue";

import { ApiError } from "../../../api/client";
import { useToastStore } from "../../../stores/toast";
import { PREVIEW_DEBOUNCE_MS, useExamWorkspacePrintPreview } from "./useExamWorkspacePrintPreview";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import type { ExamWorkspaceStore } from "./examWorkspaceStore";

const apiMocks = vi.hoisted(() => ({ fetchExamWorkspacePrintPreview: vi.fn() }));
vi.mock("../../../api/examWorkspaceExports", () => apiMocks);

function ready(pages: string[], questionPages: Record<string, number> = {}) {
  return { message: null, pages, question_pages: questionPages, revision: 1, status: "ready" as const };
}

function blocked(message: string) {
  return { message, pages: [], question_pages: {}, revision: 1, status: "blocked" as const };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, reject, resolve };
}

function mountPreview(store: ExamWorkspaceStore = serverExamWorkspaceStore) {
  const lineageId = ref<string | null>("lineage-1");
  const savedRevision = ref<number | null>(1);
  const historyCursor = ref<string | null>("cursor-1");
  const historyPosition = ref<string | null>("step-0");
  const open = ref(false);
  const selectedItemId = ref<string | null>(null);
  const scope = effectScope();
  const preview = scope.run(() =>
    useExamWorkspacePrintPreview({ historyCursor, historyPosition, lineageId, open, savedRevision, selectedItemId, store }),
  );
  if (!preview) throw new Error("preview composable did not mount");
  return { historyCursor, historyPosition, lineageId, open, preview, savedRevision, scope, selectedItemId };
}

describe("useExamWorkspacePrintPreview", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    setActivePinia(createPinia());
    apiMocks.fetchExamWorkspacePrintPreview.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("fetches nothing while the panel is closed", async () => {
    const { savedRevision, scope } = mountPreview();
    savedRevision.value = 2;
    await nextTick();
    await vi.advanceTimersByTimeAsync(5000);

    expect(apiMocks.fetchExamWorkspacePrintPreview).not.toHaveBeenCalled();
    scope.stop();
  });

  it("fetches once, for the last revision, after a burst of saved revisions", async () => {
    apiMocks.fetchExamWorkspacePrintPreview.mockResolvedValue(ready(["page-1"]));
    const { open, savedRevision, scope } = mountPreview();

    open.value = true;
    await nextTick();
    savedRevision.value = 2;
    await nextTick();
    savedRevision.value = 3;
    await nextTick();
    await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);

    expect(apiMocks.fetchExamWorkspacePrintPreview).toHaveBeenCalledTimes(1);
    expect(apiMocks.fetchExamWorkspacePrintPreview).toHaveBeenCalledWith("lineage-1", 3, "cursor-1", "step-0");
    scope.stop();
  });

  it("renders once with the new persisted cursor and the current revision after a Skrivyta edit", async () => {
    apiMocks.fetchExamWorkspacePrintPreview.mockResolvedValue(ready(["page-1"]));
    const { historyCursor, historyPosition, open, scope } = mountPreview();

    open.value = true;
    await nextTick();
    await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);
    // The autosave stored the edit as a new undo step; the saved revision did not move.
    historyCursor.value = "cursor-2";
    historyPosition.value = "step-1";
    await nextTick();
    await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);

    expect(apiMocks.fetchExamWorkspacePrintPreview).toHaveBeenCalledTimes(2);
    expect(apiMocks.fetchExamWorkspacePrintPreview).toHaveBeenLastCalledWith("lineage-1", 1, "cursor-2", "step-1");
    scope.stop();
  });

  it("re-renders with the retained step after an undo that leaves the cursor alone", async () => {
    apiMocks.fetchExamWorkspacePrintPreview.mockResolvedValue(ready(["page-1"]));
    const { historyCursor, historyPosition, open, scope } = mountPreview();

    open.value = true;
    await nextTick();
    await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);
    // A Skrivyta edit stored a new step: the cursor and the retained step move together.
    historyCursor.value = "cursor-2";
    historyPosition.value = "step-1";
    await nextTick();
    await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);
    // Undo: the retained step moves back while the concurrency token stays.
    historyPosition.value = "step-0";
    await nextTick();
    await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);

    expect(apiMocks.fetchExamWorkspacePrintPreview).toHaveBeenCalledTimes(3);
    expect(apiMocks.fetchExamWorkspacePrintPreview).toHaveBeenLastCalledWith("lineage-1", 1, "cursor-2", "step-0");
    scope.stop();
  });

  it("renders once for the last cursor after a burst of three cursor changes", async () => {
    apiMocks.fetchExamWorkspacePrintPreview.mockResolvedValue(ready(["page-1"]));
    const { historyCursor, historyPosition, open, scope } = mountPreview();

    open.value = true;
    await nextTick();
    for (const cursor of ["cursor-2", "cursor-3", "cursor-4"]) {
      historyCursor.value = cursor;
      await nextTick();
    }
    historyPosition.value = "step-3";
    await nextTick();
    await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);

    expect(apiMocks.fetchExamWorkspacePrintPreview).toHaveBeenCalledTimes(1);
    expect(apiMocks.fetchExamWorkspacePrintPreview).toHaveBeenCalledWith("lineage-1", 1, "cursor-4", "step-3");
    scope.stop();
  });

  it("fetches nothing while the retained step is not loaded yet", async () => {
    const { historyPosition, open, scope } = mountPreview();
    historyPosition.value = null;
    await nextTick();

    open.value = true;
    await nextTick();
    await vi.advanceTimersByTimeAsync(5000);

    expect(apiMocks.fetchExamWorkspacePrintPreview).not.toHaveBeenCalled();
    scope.stop();
  });

  it("fetches nothing while the history cursor is not persisted yet", async () => {
    const { historyCursor, open, scope } = mountPreview();
    historyCursor.value = null;
    await nextTick();

    open.value = true;
    await nextTick();
    await vi.advanceTimersByTimeAsync(5000);

    expect(apiMocks.fetchExamWorkspacePrintPreview).not.toHaveBeenCalled();
    scope.stop();
  });

  it("fetches nothing when the scope is disposed during the debounce", async () => {
    const { open, scope } = mountPreview();

    open.value = true;
    await nextTick();
    scope.stop();
    await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS + 5000);

    expect(apiMocks.fetchExamWorkspacePrintPreview).not.toHaveBeenCalled();
  });

  it("drops a failing in-flight response after disposal without a toast", async () => {
    const call = deferred<ReturnType<typeof ready>>();
    apiMocks.fetchExamWorkspacePrintPreview.mockReturnValue(call.promise);
    const { open, preview, scope } = mountPreview();

    open.value = true;
    await nextTick();
    await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);
    expect(apiMocks.fetchExamWorkspacePrintPreview).toHaveBeenCalledTimes(1);

    scope.stop();
    call.reject(new Error("boom"));
    await vi.advanceTimersByTimeAsync(0);

    expect(useToastStore().toasts).toHaveLength(0);
    expect(preview.loading.value).toBe(false);
  });

  it("keeps the pages empty when an in-flight response resolves after disposal", async () => {
    const call = deferred<ReturnType<typeof ready>>();
    apiMocks.fetchExamWorkspacePrintPreview.mockReturnValue(call.promise);
    const { open, preview, scope } = mountPreview();

    open.value = true;
    await nextTick();
    await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);

    scope.stop();
    call.resolve(ready(["late-page"]));
    await vi.advanceTimersByTimeAsync(0);

    expect(preview.pages.value).toEqual([]);
    expect(preview.loading.value).toBe(false);
  });

  it("fetches again after a close and reopen without disposal", async () => {
    apiMocks.fetchExamWorkspacePrintPreview.mockResolvedValue(ready(["page-1"]));
    const { open, preview, scope } = mountPreview();

    open.value = true;
    await nextTick();
    await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);
    open.value = false;
    await nextTick();
    open.value = true;
    await nextTick();
    await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);

    expect(apiMocks.fetchExamWorkspacePrintPreview).toHaveBeenCalledTimes(2);
    expect(preview.pages.value).toEqual(["page-1"]);
    scope.stop();
  });

  it("ignores an older response that arrives after a newer one", async () => {
    const calls: Array<ReturnType<typeof deferred>> = [];
    apiMocks.fetchExamWorkspacePrintPreview.mockImplementation(() => {
      const call = deferred();
      calls.push(call);
      return call.promise;
    });
    const { open, preview, savedRevision, scope } = mountPreview();

    open.value = true;
    await nextTick();
    await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);
    savedRevision.value = 2;
    await nextTick();
    await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);
    expect(calls).toHaveLength(2);

    calls[1].resolve(ready(["new-page"]));
    await vi.advanceTimersByTimeAsync(0);
    calls[0].resolve(ready(["old-page"]));
    await vi.advanceTimersByTimeAsync(0);

    expect(preview.pages.value).toEqual(["new-page"]);
    scope.stop();
  });

  it("keeps the last ready pages while the exam is blocked", async () => {
    apiMocks.fetchExamWorkspacePrintPreview
      .mockResolvedValueOnce(ready(["page-1"], { item_1: 0 }))
      .mockResolvedValueOnce(blocked("Bilden saknas"));
    const { open, preview, savedRevision, scope } = mountPreview();

    open.value = true;
    await nextTick();
    await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);
    savedRevision.value = 2;
    await nextTick();
    await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);

    expect(preview.pages.value).toEqual(["page-1"]);
    expect(preview.blocked.value).toBe(true);
    expect(preview.message.value).toBe("Bilden saknas");
    scope.stop();
  });

  it("keeps the pages and reports one failure when a render fails", async () => {
    apiMocks.fetchExamWorkspacePrintPreview
      .mockResolvedValueOnce(ready(["page-1"]))
      .mockRejectedValueOnce(new Error("boom"));
    const { open, preview, savedRevision, scope } = mountPreview();

    open.value = true;
    await nextTick();
    await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);
    savedRevision.value = 2;
    await nextTick();
    await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);

    expect(preview.pages.value).toEqual(["page-1"]);
    const messages = useToastStore().toasts.map((toast) => toast.message);
    expect(messages.filter((message) => message === "Förhandsgranskningen kunde inte uppdateras."))
      .toHaveLength(1);
    scope.stop();
  });

  it("keeps the pages and drops a 409 (the persisted state moved on) without a toast", async () => {
    apiMocks.fetchExamWorkspacePrintPreview
      .mockResolvedValueOnce(ready(["page-1"]))
      .mockRejectedValue(new ApiError({ code: "CONFLICT", message: "stale", status: 409 }));
    const { historyCursor, open, preview, scope } = mountPreview();

    open.value = true;
    await nextTick();
    await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);
    historyCursor.value = "cursor-2";
    await nextTick();
    await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);

    expect(preview.pages.value).toEqual(["page-1"]);
    expect(useToastStore().toasts).toHaveLength(0);
    expect(preview.loading.value).toBe(false);
    scope.stop();
  });
});
