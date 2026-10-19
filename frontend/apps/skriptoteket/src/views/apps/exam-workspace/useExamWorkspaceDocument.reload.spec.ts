/**
 * Exam workspace document: reload waits for a running operation, and a
 * read-only tab refuses edits.
 *
 * Expected behavior (TASK-SKRIPT-40-04-14 behaviour item 7, decision D4,
 * unit K8):
 *   A 409 that arrives while an operation runs no longer skips the reload:
 *   `reloadDocument` waits for the running operation to end instead. A tab
 *   that does not hold the edit lease is read-only: title, course, item and
 *   whole-copy edits refuse without touching the copy.
 */

import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { effectScope, ref } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { buildResponse, deferred } from "./useExamWorkspaceDocument.specSupport";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import { useExamWorkspaceDocument } from "./useExamWorkspaceDocument";

const api = vi.hoisted(() => ({
  getExamWorkspaceDocument: vi.fn(),
}));
vi.mock("../../../api/examWorkspace", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../../api/examWorkspace")>()),
  ...api,
}));

beforeEach(() => {
  setActivePinia(createPinia());
  vi.clearAllMocks();
});

describe("reloadDocument while an operation runs", () => {
  it("waits for the running open instead of skipping the reload", async () => {
    const first = buildResponse();
    api.getExamWorkspaceDocument.mockResolvedValue(first);
    const scope = effectScope();
    const state = scope.run(() => useExamWorkspaceDocument({ store: serverExamWorkspaceStore }))!;
    try {
      await state.openDocument("lineage-1");

      const gate = deferred<ReturnType<typeof buildResponse>>();
      api.getExamWorkspaceDocument.mockImplementationOnce(() => gate.promise);
      const opening = state.openDocument("lineage-1");
      await flushPromises();
      expect(api.getExamWorkspaceDocument).toHaveBeenCalledTimes(2);

      const reloaded = { ...first, history_cursor: "reloaded-cursor" };
      api.getExamWorkspaceDocument.mockImplementationOnce(async () => reloaded);
      const reloading = state.reloadDocument();
      await flushPromises();
      expect(api.getExamWorkspaceDocument).toHaveBeenCalledTimes(2);

      gate.resolve(first);
      await opening;
      await reloading;
      expect(api.getExamWorkspaceDocument).toHaveBeenCalledTimes(3);
      expect(state.workspaceDocument.value).toEqual(reloaded.document);
    } finally {
      scope.stop();
    }
  });

  it("reloads at once when nothing runs", async () => {
    const first = buildResponse();
    api.getExamWorkspaceDocument.mockResolvedValue(first);
    const scope = effectScope();
    const state = scope.run(() => useExamWorkspaceDocument({ store: serverExamWorkspaceStore }))!;
    try {
      await state.openDocument("lineage-1");
      const reloaded = { ...first, history_cursor: "reloaded-cursor" };
      api.getExamWorkspaceDocument.mockResolvedValueOnce(reloaded);

      await state.reloadDocument();

      expect(state.workspaceDocument.value).toEqual(reloaded.document);
    } finally {
      scope.stop();
    }
  });
});

describe("read-only editing", () => {
  it("refuses title, course, item and whole-copy edits without touching the copy", async () => {
    const first = buildResponse();
    api.getExamWorkspaceDocument.mockResolvedValue(first);
    const readOnly = ref(true);
    const scope = effectScope();
    const state = scope.run(() =>
      useExamWorkspaceDocument({
        isReadOnly: () => readOnly.value,
        store: serverExamWorkspaceStore,
      }),
    )!;
    try {
      await state.openDocument("lineage-1");
      const before = state.workspaceDocument.value;

      state.setTitle("Försök");
      state.setCourse(null);
      const itemId = before!.items[0]!.item_id;
      state.markItemReviewed(itemId);
      const edited = state.editDocument((document) => ({ ...document, title: "Försök" }));

      expect(edited).toBe(false);
      expect(state.workspaceDocument.value).toBe(before);
      expect(state.workspaceDocument.value!.title).not.toBe("Försök");

      readOnly.value = false;
      state.setTitle("Tillåten");
      expect(state.workspaceDocument.value!.title).toBe("Tillåten");
    } finally {
      scope.stop();
    }
  });
});
