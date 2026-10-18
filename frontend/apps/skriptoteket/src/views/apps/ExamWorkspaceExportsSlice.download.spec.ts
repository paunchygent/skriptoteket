/**
 * Exam workspace export download behavior.
 *
 * Expected behavior:
 *   A format click saves unsaved changes first and exports the version just
 *   saved; a failed save exports nothing. A created file is reported inline
 *   (menu and drawer), never as a success toast; failures stay toasts. A 409
 *   reads the latest version in.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../api/client";
import { useToastStore } from "../../stores/toast";
import {
  arrangeExportApis,
  deferred,
  exportableResponse,
  exportFromMenu,
  menuFormatDisabled,
  mountImported,
  openExportDrawer,
  openMenu,
  page,
  requirePage,
  unmountWrappers,
} from "./ExamWorkspaceExportsSlice.specSupport";
import { selectItemRow } from "./ExamWorkspaceSlice.specSupport";

import { arrangeStepHistory } from "./ExamWorkspaceHistory.specSupport";

const apiMocks = vi.hoisted(() => ({
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
  downloadExamWorkspaceExport: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceExportChecklist: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
}));

vi.mock("../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../test/examCourseCatalog")).getExamCourseCatalog,
}));

const downloadMocks = vi.hoisted(() => ({ triggerBrowserDownload: vi.fn() }));

vi.mock("./exam-converter/browserDownload", () => downloadMocks);


beforeEach(() => {
  arrangeExportApis({ api: apiMocks, download: downloadMocks });
  arrangeStepHistory(apiMocks);
});

afterEach(unmountWrappers);

describe("ExamWorkspaceView export download", () => {
  it.each([
    ["qti", "NO-prov-qti.zip", "QTI-paketet är skapat."],
    ["pdf", "NO-prov-examnet.pdf", "PDF-filen är skapad."],
    ["docx", "NO-prov.docx", "Word-filen är skapad."],
  ] as const)(
    "downloads the %s export from the saved version with the server filename and reports it inline",
    async (target, filename, created) => {
      const blob = new Blob(["export"]);
      apiMocks.downloadExamWorkspaceExport.mockResolvedValue({
        blob,
        contentType: "application/octet-stream",
        filename,
      });
      const wrapper = await mountImported();

      await exportFromMenu(wrapper, target);

      expect(apiMocks.downloadExamWorkspaceExport).toHaveBeenCalledWith("lineage-1", target, 1);
      expect(downloadMocks.triggerBrowserDownload).toHaveBeenCalledWith(blob, filename);
      expect(useToastStore().success).not.toHaveBeenCalled();
      await openMenu(wrapper);
      expect(requirePage("exam-workspace-export-menu-result").text()).toBe(created);
      await openExportDrawer(wrapper);
      expect(wrapper.get('[data-test="exam-workspace-export-result"]').text()).toBe(created);
      expect(wrapper.find('[data-test="exam-workspace-export-notice"]').exists()).toBe(false);
    },
  );

  it("exports from the drawer with the chosen format and reports it inline", async () => {
    apiMocks.downloadExamWorkspaceExport.mockResolvedValue({
      blob: new Blob(["pdf"]),
      contentType: "application/pdf",
      filename: "NO-prov-examnet.pdf",
    });
    const wrapper = await mountImported();
    await openExportDrawer(wrapper);

    await wrapper.get('[data-test="exam-workspace-export-format-pdf"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-export-run"]').trigger("click");
    await flushPromises();

    expect(apiMocks.downloadExamWorkspaceExport).toHaveBeenCalledTimes(1);
    expect(apiMocks.downloadExamWorkspaceExport).toHaveBeenCalledWith("lineage-1", "pdf", 1);
    expect(downloadMocks.triggerBrowserDownload).toHaveBeenCalledWith(
      expect.any(Blob),
      "NO-prov-examnet.pdf",
    );
    expect(wrapper.get('[data-test="exam-workspace-export-result"]').text()).toBe(
      "PDF-filen är skapad.",
    );
    expect(useToastStore().success).not.toHaveBeenCalled();
  });

  it("shows a Swedish failure notice and toast when an export fails without question blockers", async () => {
    apiMocks.downloadExamWorkspaceExport.mockRejectedValue(
      new ApiError({ code: "INTERNAL_ERROR", message: "boom", status: 500 }),
    );
    const wrapper = await mountImported();

    await exportFromMenu(wrapper, "qti");

    await openExportDrawer(wrapper);
    expect(wrapper.get('[data-test="exam-workspace-export-notice"]').text()).toBe(
      "QTI-paketet kunde inte skapas. Försök igen.",
    );
    expect(wrapper.find('[data-test="exam-workspace-export-result"]').exists()).toBe(false);
    expect(useToastStore().failure).toHaveBeenCalledWith(
      "QTI-paketet kunde inte skapas. Försök igen.",
    );
    expect(downloadMocks.triggerBrowserDownload).not.toHaveBeenCalled();
  });

  it("reads the latest version in when a save elsewhere moved the saved exam", async () => {
    apiMocks.downloadExamWorkspaceExport.mockRejectedValue(
      new ApiError({ code: "CONFLICT", message: "stale", status: 409 }),
    );
    const wrapper = await mountImported();
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(exportableResponse({ version: 3 }));

    await exportFromMenu(wrapper, "qti");

    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenLastCalledWith("lineage-1");
    await openExportDrawer(wrapper);
    expect(wrapper.get('[data-test="exam-workspace-export-notice"]').text()).toBe(
      "Provet hade sparats någon annanstans. Den senaste versionen är inläst. Exportera igen.",
    );
  });

  it("saves unsaved edits first and exports the version just saved, in one click", async () => {
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(exportableResponse({ version: 2 }));
    apiMocks.downloadExamWorkspaceExport.mockResolvedValue({
      blob: new Blob(["pdf"]),
      contentType: "application/pdf",
      filename: "Prov.pdf",
    });
    const wrapper = await mountImported();
    await selectItemRow(wrapper, "item_002");
    await wrapper.find('[data-test="exam-workspace-item-points-input"]').setValue("7");

    await openMenu(wrapper);
    expect(menuFormatDisabled("pdf")).toBeUndefined();
    expect(requirePage("exam-workspace-export-menu").text()).not.toContain("Spara provet först");
    await requirePage("exam-workspace-export-pdf").trigger("click");
    await flushPromises();

    const saved = apiMocks.saveExamWorkspaceDocument.mock.calls[0]![1].document;
    expect(saved.items.find((item: { item_id: string }) => item.item_id === "item_002").points).toBe(7);
    expect(apiMocks.downloadExamWorkspaceExport).toHaveBeenCalledWith("lineage-1", "pdf", 2);
    expect(wrapper.get('[data-test="exam-workspace-save-state"]').text()).toMatch(/^Sparat /);
  });

  it("exports a clean exam without saving it again", async () => {
    apiMocks.downloadExamWorkspaceExport.mockResolvedValue({
      blob: new Blob(["docx"]),
      contentType: "application/octet-stream",
      filename: "Prov.docx",
    });
    const wrapper = await mountImported();

    await exportFromMenu(wrapper, "docx");

    expect(apiMocks.saveExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(apiMocks.downloadExamWorkspaceExport).toHaveBeenCalledWith("lineage-1", "docx", 1);
  });

  it("exports nothing when the save before it fails, and toasts the save failure", async () => {
    apiMocks.saveExamWorkspaceDocument.mockRejectedValue(
      new ApiError({ code: "INTERNAL_ERROR", message: "boom", status: 500 }),
    );
    const wrapper = await mountImported();
    await selectItemRow(wrapper, "item_002");
    await wrapper.find('[data-test="exam-workspace-item-points-input"]').setValue("7");

    await exportFromMenu(wrapper, "qti");

    expect(apiMocks.downloadExamWorkspaceExport).not.toHaveBeenCalled();
    expect(useToastStore().failure).toHaveBeenCalledTimes(1);
    expect(useToastStore().failure).toHaveBeenCalledWith("Det gick inte att spara provet. Försök igen.");
    expect(page("exam-workspace-export-running")).toBeNull();
    expect(menuFormatDisabled("qti")).toBeUndefined();
  });

  it("shows the export running on the format and the drawer while the save and the export run", async () => {
    const save = deferred<ReturnType<typeof exportableResponse>>();
    apiMocks.saveExamWorkspaceDocument.mockReturnValue(save.promise);
    const download = deferred<{ blob: Blob; contentType: string; filename: string }>();
    apiMocks.downloadExamWorkspaceExport.mockReturnValue(download.promise);
    const wrapper = await mountImported();
    await selectItemRow(wrapper, "item_002");
    await wrapper.find('[data-test="exam-workspace-item-points-input"]').setValue("7");

    await exportFromMenu(wrapper, "qti");
    // Saving: the format already shows the export running, and no format starts another.
    expect(requirePage("exam-workspace-export-running").text()).toBe("Exporterar …");
    expect(requirePage("exam-workspace-export-qti").attributes("aria-busy")).toBe("true");
    expect(menuFormatDisabled("pdf")).toBe("true");
    save.resolve(exportableResponse({ version: 2 }));
    await flushPromises();
    expect(apiMocks.downloadExamWorkspaceExport).toHaveBeenCalledWith("lineage-1", "qti", 2);
    expect(requirePage("exam-workspace-export-running").text()).toBe("Exporterar …");
    download.resolve({ blob: new Blob(["zip"]), contentType: "application/zip", filename: "Prov.zip" });
    await flushPromises();
    expect(page("exam-workspace-export-running")).toBeNull();
    expect(requirePage("exam-workspace-export-menu-result").text()).toBe("QTI-paketet är skapat.");
  });
});
