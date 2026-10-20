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
import type { ExamWorkspaceExportTarget } from "../../api/examWorkspaceExports";
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
import { EXAM_WORKSPACE_EXPORT_FORMATS } from "./exam-workspace/examWorkspaceExportFormats";
import { AUTOSAVE_FAILURE_COPY } from "./exam-workspace/useExamWorkspaceSaveStatus";

import { arrangeStepHistory } from "./ExamWorkspaceHistory.specSupport";

const apiMocks = vi.hoisted(() => ({
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
}));
const exportApiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
  getExamWorkspaceExportChecklist: vi.fn(),
}));

vi.mock("../../api/examWorkspaceExports", () => exportApiMocks);
vi.mock("../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../test/examCourseCatalog")).getExamCourseCatalog,
}));

const downloadMocks = vi.hoisted(() => ({ triggerBrowserDownload: vi.fn() }));
const unreadable = vi.hoisted(() => ({ listUnreadableExamWorkspaceDocuments: vi.fn() }));

vi.mock("../../utils/browserDownload", () => downloadMocks);
vi.mock("../../api/examWorkspaceUnreadableFiles", () => unreadable);

/** The server filename and the inline created copy per offered format. */
const DOWNLOAD_CASES: Record<ExamWorkspaceExportTarget, { created: string; filename: string }> = {
  qti: { created: "QTI-paketet är skapat.", filename: "NO-prov-qti.zip" },
  pdf: { created: "PDF-filen är skapad.", filename: "NO-prov-examnet.pdf" },
  pdf_facit: { created: "PDF-filen med facit är skapad.", filename: "NO-prov-facit.pdf" },
  docx: { created: "Word-filen är skapad.", filename: "NO-prov.docx" },
  examnet_pdf: { created: "PDF-filen för Exam.net är skapad.", filename: "NO-prov-Exam.net.pdf" },
};


beforeEach(() => {
  arrangeExportApis({ api: apiMocks, exportApi: exportApiMocks, download: downloadMocks });
  arrangeStepHistory(apiMocks);
  unreadable.listUnreadableExamWorkspaceDocuments.mockReset();
  unreadable.listUnreadableExamWorkspaceDocuments.mockResolvedValue({ documents: [] });
});

afterEach(unmountWrappers);

describe("ExamWorkspaceView export download", () => {
  it.each(EXAM_WORKSPACE_EXPORT_FORMATS.map((format) => format.target))(
    "downloads the %s export from the saved version with the server filename and reports it inline",
    async (target: ExamWorkspaceExportTarget) => {
      const { created, filename } = DOWNLOAD_CASES[target];
      const blob = new Blob(["export"]);
      exportApiMocks.downloadExamWorkspaceExport.mockResolvedValue({
        blob,
        contentType: "application/octet-stream",
        filename,
      });
      const wrapper = await mountImported();

      await exportFromMenu(wrapper, target);

      expect(exportApiMocks.downloadExamWorkspaceExport).toHaveBeenCalledWith("lineage-1", target, 1);
      expect(downloadMocks.triggerBrowserDownload).toHaveBeenCalledWith(blob, filename);
      expect(useToastStore().success).not.toHaveBeenCalled();
      await openMenu(wrapper);
      expect(requirePage("exam-workspace-export-menu-result").text()).toBe(created);
      await openExportDrawer(wrapper);
      expect(wrapper.get('[data-test="exam-workspace-export-result"]').text()).toBe(created);
      expect(wrapper.find('[data-test="exam-workspace-export-notice"]').exists()).toBe(false);
    },
  );

  it("offers the formats as a radio list and exports the chosen format", async () => {
    exportApiMocks.downloadExamWorkspaceExport.mockResolvedValue({
      blob: new Blob(["pdf"]),
      contentType: "application/pdf",
      filename: "NO-prov-examnet.pdf",
    });
    const wrapper = await mountImported();
    await openExportDrawer(wrapper);

    const drawer = wrapper.get('[data-test="exam-workspace-drawer-export"]');
    const fieldset = drawer.get("fieldset");
    expect(fieldset.get("legend").text()).toBe("Format");
    const inputs = fieldset.findAll('input[type="radio"]');
    expect(inputs.map((input) => input.attributes("data-test"))).toEqual(
      EXAM_WORKSPACE_EXPORT_FORMATS.map((format) => `exam-workspace-export-format-${format.target}`),
    );
    expect(fieldset.findAll('input[type="radio"]:checked')).toHaveLength(1);
    expect(
      drawer.get<HTMLInputElement>('[data-test="exam-workspace-export-format-qti"]').element.checked,
    ).toBe(true);

    await drawer.get<HTMLInputElement>('[data-test="exam-workspace-export-format-pdf"]').setValue(true);
    expect(
      drawer.get<HTMLInputElement>('[data-test="exam-workspace-export-format-pdf"]').element.checked,
    ).toBe(true);
    expect(
      drawer.get<HTMLInputElement>('[data-test="exam-workspace-export-format-qti"]').element.checked,
    ).toBe(false);

    await wrapper.get('[data-test="exam-workspace-export-run"]').trigger("click");
    await flushPromises();

    expect(exportApiMocks.downloadExamWorkspaceExport).toHaveBeenCalledTimes(1);
    expect(exportApiMocks.downloadExamWorkspaceExport).toHaveBeenCalledWith("lineage-1", "pdf", 1);
    expect(wrapper.get('[data-test="exam-workspace-export-result"]').text()).toBe(
      "PDF-filen är skapad.",
    );
  });

  it("exports from the drawer with the chosen format and reports it inline", async () => {
    exportApiMocks.downloadExamWorkspaceExport.mockResolvedValue({
      blob: new Blob(["pdf"]),
      contentType: "application/pdf",
      filename: "NO-prov-examnet.pdf",
    });
    const wrapper = await mountImported();
    await openExportDrawer(wrapper);

    await wrapper.get<HTMLInputElement>('[data-test="exam-workspace-export-format-pdf"]').setValue(true);
    await wrapper.get('[data-test="exam-workspace-export-run"]').trigger("click");
    await flushPromises();

    expect(exportApiMocks.downloadExamWorkspaceExport).toHaveBeenCalledTimes(1);
    expect(exportApiMocks.downloadExamWorkspaceExport).toHaveBeenCalledWith("lineage-1", "pdf", 1);
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
    exportApiMocks.downloadExamWorkspaceExport.mockRejectedValue(
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
    exportApiMocks.downloadExamWorkspaceExport.mockRejectedValue(
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
    exportApiMocks.downloadExamWorkspaceExport.mockResolvedValue({
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

    const stores = apiMocks.storeExamWorkspaceUndoStep.mock.calls;
    const saved = stores[stores.length - 1]![1].document;
    expect(saved.items.find((item: { item_id: string }) => item.item_id === "item_002").points).toBe(7);
    expect(exportApiMocks.downloadExamWorkspaceExport).toHaveBeenCalledWith("lineage-1", "pdf", 1);
    expect(wrapper.get('[data-test="exam-workspace-save-state"]').text()).toMatch(/^Sparat /);
  });

  it("exports a clean exam without saving it again", async () => {
    exportApiMocks.downloadExamWorkspaceExport.mockResolvedValue({
      blob: new Blob(["docx"]),
      contentType: "application/octet-stream",
      filename: "Prov.docx",
    });
    const wrapper = await mountImported();

    await exportFromMenu(wrapper, "docx");

    expect(apiMocks.storeExamWorkspaceUndoStep).not.toHaveBeenCalled();
    expect(exportApiMocks.downloadExamWorkspaceExport).toHaveBeenCalledWith("lineage-1", "docx", 1);
  });

  it("exports nothing when the save before it fails, and toasts the save failure", async () => {
    apiMocks.storeExamWorkspaceUndoStep.mockRejectedValue(
      new ApiError({ code: "INTERNAL_ERROR", message: "boom", status: 500 }),
    );
    const wrapper = await mountImported();
    await selectItemRow(wrapper, "item_002");
    await wrapper.find('[data-test="exam-workspace-item-points-input"]').setValue("7");

    await exportFromMenu(wrapper, "qti");

    expect(exportApiMocks.downloadExamWorkspaceExport).not.toHaveBeenCalled();
    expect(useToastStore().failure).toHaveBeenCalledTimes(1);
    expect(useToastStore().failure).toHaveBeenCalledWith(AUTOSAVE_FAILURE_COPY);
    expect(page("exam-workspace-export-running")).toBeNull();
    expect(requirePage("exam-workspace-export-qti").attributes("aria-busy")).toBeUndefined();
    expect(requirePage("exam-workspace-export-save-qti").attributes("aria-busy")).toBeUndefined();
    expect(menuFormatDisabled("qti")).toBeUndefined();
  });

  it("shows the export running on the format and the drawer while the save and the export run", async () => {
    const inner = apiMocks.storeExamWorkspaceUndoStep.getMockImplementation();
    if (!inner) {
      throw new Error("expected the step store double");
    }
    let release!: () => void;
    apiMocks.storeExamWorkspaceUndoStep.mockImplementationOnce(
      (...args: unknown[]) =>
        new Promise((resolve) => {
          release = () => resolve((inner as (...innerArgs: unknown[]) => unknown)(...args));
        }),
    );
    const download = deferred<{ blob: Blob; contentType: string; filename: string }>();
    exportApiMocks.downloadExamWorkspaceExport.mockReturnValue(download.promise);
    const wrapper = await mountImported();
    await selectItemRow(wrapper, "item_002");
    await wrapper.find('[data-test="exam-workspace-item-points-input"]').setValue("7");

    await exportFromMenu(wrapper, "qti");
    // Saving: the download part already shows the export running, and no format starts another.
    expect(page("exam-workspace-export-running")).toBeNull();
    expect(requirePage("exam-workspace-export-qti").attributes("aria-busy")).toBe("true");
    expect(requirePage("exam-workspace-export-qti").attributes("aria-disabled")).toBe("true");
    expect(requirePage("exam-workspace-export-save-qti").attributes("aria-busy")).toBeUndefined();
    expect(requirePage("exam-workspace-export-save-qti").attributes("aria-disabled")).toBe("true");
    expect(menuFormatDisabled("pdf")).toBe("true");
    expect(requirePage("exam-workspace-export-save-pdf").attributes("aria-disabled")).toBe("true");
    release();
    await flushPromises();
    expect(exportApiMocks.downloadExamWorkspaceExport).toHaveBeenCalledWith("lineage-1", "qti", 1);
    expect(page("exam-workspace-export-running")).toBeNull();
    expect(requirePage("exam-workspace-export-qti").attributes("aria-busy")).toBe("true");
    expect(requirePage("exam-workspace-export-save-qti").attributes("aria-busy")).toBeUndefined();
    download.resolve({ blob: new Blob(["zip"]), contentType: "application/zip", filename: "Prov.zip" });
    await flushPromises();
    expect(page("exam-workspace-export-running")).toBeNull();
    expect(requirePage("exam-workspace-export-qti").attributes("aria-busy")).toBeUndefined();
    expect(requirePage("exam-workspace-export-save-qti").attributes("aria-busy")).toBeUndefined();
    expect(requirePage("exam-workspace-export-menu-result").text()).toBe("QTI-paketet är skapat.");
  });
});
