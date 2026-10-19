/**
 * Export file names come from the server (TASK-SKRIPT-40-04-05, D1).
 *
 * Expected behavior:
 *   The download uses the file name the server sent in Content-Disposition,
 *   whatever the exam's title is; the frontend never builds a name. A
 *   response without a name is a failed export, not a download under a
 *   guessed name.
 */

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope, ref } from "vue";

import type { ExamWorkspaceDocumentSummary, NativeExamDocument } from "../../../api/examWorkspace";
import { buildSavedExamSummary } from "./useExamWorkspaceDocument.specSupport";
import * as exportsModule from "./useExamWorkspaceExports";

const apiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
  getExamWorkspaceExportChecklist: vi.fn(),
  saveExamWorkspaceExport: vi.fn(),
}));

const downloadMock = vi.hoisted(() => ({ triggerBrowserDownload: vi.fn() }));

vi.mock("../../../api/examWorkspaceExports", () => apiMocks);
vi.mock("../../../utils/browserDownload", () => downloadMock);

function mountExports(title: string) {
  const summary = ref<ExamWorkspaceDocumentSummary | null>(buildSavedExamSummary({ title }));
  const workspaceDocument = ref<NativeExamDocument | null>(null);
  const scope = effectScope();
  const exports = scope.run(() =>
    exportsModule.useExamWorkspaceExports(summary, workspaceDocument, {
      noteBlockers: vi.fn(),
      readLatest: async () => undefined,
      saveFirst: async () => true,
    }),
  );
  if (!exports) throw new Error("exports composable did not mount");
  return { exports, scope };
}

describe("useExamWorkspaceExports download names", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    apiMocks.getExamWorkspaceExportChecklist.mockResolvedValue({ entries: [] });
  });

  it("downloads each format under the server's name, not under one derived from the title", async () => {
    const { exports, scope } = mountExports("Läsförståelse, åk 7.");
    const serverNames = { qti: "Server A.zip", pdf: "Server B.pdf", docx: "Server C.docx" } as const;
    apiMocks.downloadExamWorkspaceExport.mockImplementation(async (_lineage, target: keyof typeof serverNames) => ({
      blob: new Blob([target]),
      contentType: null,
      filename: serverNames[target],
    }));

    for (const target of ["qti", "pdf", "docx"] as const) {
      await exports.exportDocument(target);
    }

    expect(downloadMock.triggerBrowserDownload.mock.calls.map((call) => call[1])).toEqual([
      "Server A.zip",
      "Server B.pdf",
      "Server C.docx",
    ]);
    scope.stop();
  });

  it("downloads nothing and reports a failed export when the response has no file name", async () => {
    const { exports, scope } = mountExports("Läsförståelse åk 7");
    apiMocks.downloadExamWorkspaceExport.mockRejectedValue(
      new Error("The export response carries no file name in Content-Disposition."),
    );

    await exports.exportDocument("pdf");

    expect(downloadMock.triggerBrowserDownload).not.toHaveBeenCalled();
    expect(exports.exportResult.value).toBeNull();
    expect(exports.exportNotice.value).toContain("kunde inte skapas");
    scope.stop();
  });
});
