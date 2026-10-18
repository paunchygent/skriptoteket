/**
 * Exam workspace Förhandsgranska composable (TASK-SKRIPT-40-04-07, W5).
 *
 * Expected behavior:
 *   The panel renders nothing while closed, renders once for a burst of
 *   persisted history-cursor changes, ignores a response an older request left
 *   behind, keeps the last ready pages while the exam is blocked or a request
 *   fails, and reports a failure once. A 409 (the persisted state moved on) is
 *   dropped silently.
 */

import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope, nextTick, ref } from "vue";

import { ApiError } from "../../../api/client";
import { useToastStore } from "../../../stores/toast";
import { PREVIEW_DEBOUNCE_MS, useExamWorkspacePrintPreview } from "./useExamWorkspacePrintPreview";

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

function mountPreview() {
  const lineageId = ref<string | null>("lineage-1");
  const savedRevision = ref<number | null>(1);
  const historyCursor = ref<string | null>("cursor-1");
  const open = ref(false);
  const selectedItemId = ref<string | null>(null);
  const scope = effectScope();
  const preview = scope.run(() =>
    useExamWorkspacePrintPreview({ historyCursor, lineageId, open, savedRevision, selectedItemId }),
  );
  if (!preview) throw new Error("preview composable did not mount");
  return { historyCursor, lineageId, open, preview, savedRevision, scope, selectedItemId };
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
    expect(apiMocks.fetchExamWorkspacePrintPreview).toHaveBeenCalledWith("lineage-1", 3, "cursor-1");
    scope.stop();
  });

  it("renders once with the new persisted cursor and the current revision after a Skrivyta edit", async () => {
    apiMocks.fetchExamWorkspacePrintPreview.mockResolvedValue(ready(["page-1"]));
    const { historyCursor, open, scope } = mountPreview();

    open.value = true;
    await nextTick();
    await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);
    // The autosave stored the edit as a new undo step; the saved revision did not move.
    historyCursor.value = "cursor-2";
    await nextTick();
    await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);

    expect(apiMocks.fetchExamWorkspacePrintPreview).toHaveBeenCalledTimes(2);
    expect(apiMocks.fetchExamWorkspacePrintPreview).toHaveBeenLastCalledWith("lineage-1", 1, "cursor-2");
    scope.stop();
  });

  it("renders once for the last cursor after a burst of three cursor changes", async () => {
    apiMocks.fetchExamWorkspacePrintPreview.mockResolvedValue(ready(["page-1"]));
    const { historyCursor, open, scope } = mountPreview();

    open.value = true;
    await nextTick();
    for (const cursor of ["cursor-2", "cursor-3", "cursor-4"]) {
      historyCursor.value = cursor;
      await nextTick();
    }
    await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);

    expect(apiMocks.fetchExamWorkspacePrintPreview).toHaveBeenCalledTimes(1);
    expect(apiMocks.fetchExamWorkspacePrintPreview).toHaveBeenCalledWith("lineage-1", 1, "cursor-4");
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
