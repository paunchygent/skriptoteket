/**
 * Export file names follow the exam title (TASK-SKRIPT-40-04-05, D1).
 *
 * Expected behavior:
 *   The fallback name used when the server sends none is the title without
 *   punctuation plus the format's extension; QTI, PDF and DOCX share one base
 *   and carry no format suffix.
 */

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope, ref } from "vue";

import type { ExamWorkspaceDocumentSummary, NativeExamDocument } from "../../../api/examWorkspace";
import { buildSavedExamSummary } from "./useExamWorkspaceDocument.specSupport";
import { examWorkspaceExportFilename, useExamWorkspaceExports } from "./useExamWorkspaceExports";

const apiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
  getExamWorkspaceExportChecklist: vi.fn(),
  saveExamWorkspaceExport: vi.fn(),
}));

const downloadMock = vi.hoisted(() => ({ triggerBrowserDownload: vi.fn() }));

vi.mock("../../../api/examWorkspace", () => apiMocks);
vi.mock("../exam-converter/browserDownload", () => downloadMock);

describe("examWorkspaceExportFilename", () => {
  it("drops punctuation, keeps å, ä, ö and digits, and collapses spaces", () => {
    expect(examWorkspaceExportFilename("  Prov: Svenska 2 – åk. 9 (Ö/Ä)!  ", "qti")).toBe(
      "Prov Svenska 2 åk 9 ÖÄ.zip",
    );
  });

  it("keeps a decomposed å", () => {
    expect(examWorkspaceExportFilename("Bårk", "pdf")).toBe("Bårk.pdf");
  });

  it("gives all three formats one base and no format suffix", () => {
    const names = (["qti", "pdf", "docx"] as const).map((target) =>
      examWorkspaceExportFilename("Fysik: Rörelse!", target),
    );
    expect(names).toEqual(["Fysik Rörelse.zip", "Fysik Rörelse.pdf", "Fysik Rörelse.docx"]);
  });
});

describe("useExamWorkspaceExports download fallback", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    apiMocks.getExamWorkspaceExportChecklist.mockResolvedValue({ entries: [] });
  });

  it("names a download without a server file name after the saved exam's title", async () => {
    apiMocks.downloadExamWorkspaceExport.mockResolvedValue({ blob: new Blob(["x"]), filename: null });
    const summary = ref<ExamWorkspaceDocumentSummary | null>(
      buildSavedExamSummary({ title: "Läsförståelse, åk 7." }),
    );
    const workspaceDocument = ref<NativeExamDocument | null>(null);
    const scope = effectScope();
    const exports = scope.run(() =>
      useExamWorkspaceExports(summary, workspaceDocument, {
        readLatest: async () => undefined,
        saveFirst: async () => true,
      }),
    );

    for (const target of ["qti", "pdf", "docx"] as const) {
      await exports?.exportDocument(target);
    }

    expect(downloadMock.triggerBrowserDownload.mock.calls.map((call) => call[1])).toEqual([
      "Läsförståelse åk 7.zip",
      "Läsförståelse åk 7.pdf",
      "Läsförståelse åk 7.docx",
    ]);
    scope.stop();
  });
});
