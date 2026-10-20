/**
 * The exam workspace store seam in guest mode.
 *
 * Expected behavior:
 *   A store whose `teacher` half is null makes every teacher-only action do
 *   nothing and call no server: Spara som (copy), save export to Mina filer,
 *   and the saved-exams list load. The shared half stays available.
 */

import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope, ref } from "vue";

import type { ExamWorkspaceDocumentSummary, NativeExamDocument } from "../../../api/examWorkspace";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
import type { ExamWorkspaceStore } from "./examWorkspaceStore";
import { createSyncFence } from "./examWorkspaceSyncFence";
import { buildResponse, buildSavedExamSummary } from "./useExamWorkspaceDocument.specSupport";
import { useExamWorkspaceDocument } from "./useExamWorkspaceDocument";
import * as exportsModule from "./useExamWorkspaceExports";
import { useExamWorkspaceSavedList } from "./useExamWorkspaceSavedList";

const apiMocks = vi.hoisted(() => ({
  copyExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  saveExamWorkspaceExport: vi.fn(),
}));

vi.mock("../../../api/examWorkspace", () => apiMocks);

/** The guest store: shared services only, no teacher or guest half. */
const guestStore: ExamWorkspaceStore = {
  shared: serverExamWorkspaceStore.shared,
  teacher: null,
  guest: null,
};

beforeEach(() => {
  setActivePinia(createPinia());
  for (const mock of Object.values(apiMocks)) mock.mockReset();
});

describe("teacher actions in guest mode", () => {
  it("does nothing for Spara som and never copies the exam", async () => {
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(buildResponse());
    const scope = effectScope();
    const state = scope.run(() => useExamWorkspaceDocument({ store: guestStore }))!;
    try {
      await state.openDocument("lineage-1");
      await flushPromises();

      await expect(state.saveDocumentAs("Kopia", createSyncFence().begin())).resolves.toBe("failed");
      expect(apiMocks.copyExamWorkspaceDocument).not.toHaveBeenCalled();
    } finally {
      scope.stop();
    }
  });

  it("does nothing for save to Mina filer and never saves the export", async () => {
    const summary = ref<ExamWorkspaceDocumentSummary | null>(buildSavedExamSummary({ title: "Prov" }));
    const workspaceDocument = ref<NativeExamDocument | null>(buildResponse().document);
    const scope = effectScope();
    const exports = scope.run(() =>
      exportsModule.useExamWorkspaceExports(summary, workspaceDocument, {
        historyPosition: ref(null),
        noteBlockers: vi.fn(),
        readLatest: async () => undefined,
        saveFirst: async () => true,
        savedVersion: () => 1,
        store: guestStore,
      }),
    )!;
    try {
      await exports.saveExportToFiles("pdf");

      expect(apiMocks.saveExamWorkspaceExport).not.toHaveBeenCalled();
      expect(exports.exportResult.value).toBeNull();
      expect(exports.exportNotice.value).toBeNull();
    } finally {
      scope.stop();
    }
  });

  it("loads no saved exams and calls no api", async () => {
    const list = useExamWorkspaceSavedList({
      beginSummaryRead: () => (summary) => summary,
      teacher: null,
    });

    await list.loadSavedDocuments();

    expect(apiMocks.listExamWorkspaceDocuments).not.toHaveBeenCalled();
    expect(list.savedDocuments.value).toEqual([]);
  });
});
