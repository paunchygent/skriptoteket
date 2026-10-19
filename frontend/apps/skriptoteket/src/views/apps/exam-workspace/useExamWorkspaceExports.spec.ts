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
import { flushPromises } from "@vue/test-utils";

import type { ExamWorkspaceDocumentSummary, NativeExamDocument } from "../../../api/examWorkspace";
import { serverExamWorkspaceStore } from "./examWorkspaceStore";
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

function mountExports(title: string, saveFirst: () => Promise<boolean> = async () => true) {
  const summary = ref<ExamWorkspaceDocumentSummary | null>(buildSavedExamSummary({ title }));
  const workspaceDocument = ref<NativeExamDocument | null>(null);
  const scope = effectScope();
  const exports = scope.run(() =>
    exportsModule.useExamWorkspaceExports(summary, workspaceDocument, {
      historyPosition: ref(null),
      noteBlockers: vi.fn(),
      readLatest: async () => undefined,
      saveFirst,
      savedVersion: () => 1,
      store: serverExamWorkspaceStore,
    }),
  );
  if (!exports) throw new Error("exports composable did not mount");
  return { exports, scope };
}

/** A promise the test resolves by hand, so the export stays running while asserted. */
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
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

describe("useExamWorkspaceExports running destination", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    apiMocks.getExamWorkspaceExportChecklist.mockResolvedValue({ entries: [] });
  });

  it("reports the download destination while a download runs and clears both after success", async () => {
    const { promise, resolve } = deferred<{ blob: Blob; contentType: null; filename: string }>();
    apiMocks.downloadExamWorkspaceExport.mockReturnValue(promise);
    const { exports, scope } = mountExports("Prov");
    try {
      const running = exports.exportDocument("pdf");
      await flushPromises();

      expect(exports.exportingTarget.value).toBe("pdf");
      expect(exports.exportingDestination.value).toBe("download");

      resolve({ blob: new Blob(["pdf"]), contentType: null, filename: "Server.pdf" });
      await running;

      expect(exports.exportingTarget.value).toBeNull();
      expect(exports.exportingDestination.value).toBeNull();
    } finally {
      scope.stop();
    }
  });

  it("reports the files destination while a save to Mina filer runs and clears both after success", async () => {
    const { promise, resolve } = deferred<{ created_at: string }>();
    apiMocks.saveExamWorkspaceExport.mockReturnValue(promise);
    const { exports, scope } = mountExports("Prov");
    try {
      const running = exports.saveExportToFiles("docx");
      await flushPromises();

      expect(exports.exportingTarget.value).toBe("docx");
      expect(exports.exportingDestination.value).toBe("files");

      resolve({ created_at: "2026-10-19T12:00:00Z" });
      await running;

      expect(exports.exportingTarget.value).toBeNull();
      expect(exports.exportingDestination.value).toBeNull();
    } finally {
      scope.stop();
    }
  });

  it("clears both after a failed save-first", async () => {
    const { exports, scope } = mountExports("Prov", async () => false);
    try {
      await exports.exportDocument("pdf");

      expect(apiMocks.downloadExamWorkspaceExport).not.toHaveBeenCalled();
      expect(exports.exportingTarget.value).toBeNull();
      expect(exports.exportingDestination.value).toBeNull();
    } finally {
      scope.stop();
    }
  });

  it("clears both after a failed export request", async () => {
    apiMocks.downloadExamWorkspaceExport.mockRejectedValue(new Error("no filename"));
    const { exports, scope } = mountExports("Prov");
    try {
      await exports.exportDocument("pdf");

      expect(exports.exportingTarget.value).toBeNull();
      expect(exports.exportingDestination.value).toBeNull();
    } finally {
      scope.stop();
    }
  });

  it("keeps the running target and destination when a second export starts", async () => {
    const { promise, resolve } = deferred<{ blob: Blob; contentType: null; filename: string }>();
    apiMocks.downloadExamWorkspaceExport.mockReturnValue(promise);
    const { exports, scope } = mountExports("Prov");
    try {
      const running = exports.exportDocument("pdf");
      await flushPromises();

      await exports.exportDocument("docx");

      expect(apiMocks.downloadExamWorkspaceExport).toHaveBeenCalledTimes(1);
      expect(exports.exportingTarget.value).toBe("pdf");
      expect(exports.exportingDestination.value).toBe("download");

      resolve({ blob: new Blob(["pdf"]), contentType: null, filename: "Server.pdf" });
      await running;

      expect(exports.exportingTarget.value).toBeNull();
      expect(exports.exportingDestination.value).toBeNull();
    } finally {
      scope.stop();
    }
  });
});
