/**
 * Exam workspace export checklist and zero-points note behavior.
 *
 * Expected behavior:
 *   A successful QTI export lists what Exam.net loses on import for the
 *   exported revision; edits, saves and new exports clear that list, and a
 *   stale response never replaces the current one. With any question at 0
 *   points the QTI choice carries a note that Exam.net imports it as 1 point,
 *   without blocking.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../api/client";
import type { ExamWorkspaceExportChecklistResponse } from "../../api/examWorkspace";
import { useToastStore } from "../../stores/toast";
import {
  arrangeExportApis,
  closeMenu,
  deferred,
  exportableResponse,
  exportFromMenu,
  LOST_CHECKLIST,
  menuFormatDisabled,
  mountImported,
  openChecklistDrawer,
  openExportDrawer,
  openMenu,
  page,
  pageAll,
  requirePage,
  succeededConversion,
  unmountWrappers,
  ZERO_POINTS_NOTE,
} from "./ExamWorkspaceExportsSlice.specSupport";
import { saveDocument, selectItemRow, type ViewWrapper } from "./ExamWorkspaceSlice.specSupport";

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

describe("ExamWorkspaceView export zero-points note", () => {
  /** The fixture exam with its second question at 0 points. */
  function zeroPointsResponse() {
    const response = exportableResponse({ conversion: succeededConversion, version: 1 });
    for (const document of [response.document, response.saved_document]) {
      document.items = document.items.map((item) =>
        item.item_id === "item_002" ? { ...item, points: 0 } : item,
      );
    }
    return response;
  }

  beforeEach(() => {
    apiMocks.downloadExamWorkspaceExport.mockResolvedValue({
      blob: new Blob(["qti"]),
      contentType: "application/zip",
      filename: "prov-qti.zip",
    });
  });

  it("notes in the menu and the drawer that Exam.net imports 0 points as 1, without blocking QTI", async () => {
    apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
      apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(zeroPointsResponse());
      return { job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null,
        document_revision: null, questions_total: 0, questions_done: 0, units: [] };
    });
    const wrapper = await mountImported();

    // Menu: the note sits in the QTI entry only, and QTI stays exportable.
    await openMenu(wrapper);
    const menuNotes = pageAll("exam-workspace-export-zero-points");
    expect(menuNotes).toHaveLength(1);
    expect(menuNotes[0]?.text()).toBe(ZERO_POINTS_NOTE);
    expect(requirePage("exam-workspace-export-qti").text()).toContain(ZERO_POINTS_NOTE);
    expect(requirePage("exam-workspace-export-pdf").text()).not.toContain("0 poäng");
    expect(requirePage("exam-workspace-export-docx").text()).not.toContain("0 poäng");
    expect(menuFormatDisabled("qti")).toBeUndefined();
    await requirePage("exam-workspace-export-qti").trigger("click");
    await flushPromises();
    expect(apiMocks.downloadExamWorkspaceExport).toHaveBeenNthCalledWith(1, "lineage-1", "qti", 1);

    // Drawer: the note follows the chosen format.
    await openExportDrawer(wrapper);
    const drawer = wrapper.get('[data-test="exam-workspace-drawer-export"]');
    expect(drawer.get('[data-test="exam-workspace-export-zero-points"]').text()).toBe(
      ZERO_POINTS_NOTE,
    );
    await wrapper.get('[data-test="exam-workspace-export-format-pdf"]').trigger("click");
    expect(drawer.find('[data-test="exam-workspace-export-zero-points"]').exists()).toBe(false);
    await wrapper.get('[data-test="exam-workspace-export-format-qti"]').trigger("click");
    expect(drawer.get('[data-test="exam-workspace-export-zero-points"]').text()).toBe(
      ZERO_POINTS_NOTE,
    );
    const run = wrapper.get('[data-test="exam-workspace-export-run"]');
    expect(run.attributes("disabled")).toBeUndefined();
    await run.trigger("click");
    await flushPromises();
    expect(apiMocks.downloadExamWorkspaceExport).toHaveBeenCalledTimes(2);
    expect(apiMocks.downloadExamWorkspaceExport).toHaveBeenNthCalledWith(2, "lineage-1", "qti", 1);
  });

  it("shows no note when no question is worth 0 points", async () => {
    const wrapper = await mountImported();

    await openMenu(wrapper);
    expect(page("exam-workspace-export-zero-points")).toBeNull();
    expect(requirePage("exam-workspace-export-qti").text()).not.toContain("0 poäng");
    await closeMenu(wrapper);
    await openExportDrawer(wrapper);
    await wrapper.get('[data-test="exam-workspace-export-format-qti"]').trigger("click");
    expect(wrapper.find('[data-test="exam-workspace-export-zero-points"]').exists()).toBe(false);
    expect(wrapper.get('[data-test="exam-workspace-drawer-export"]').text()).not.toContain(
      "0 poäng",
    );
  });

  it("shows the note as soon as a question is edited to 0 points and drops it when raised", async () => {
    const wrapper = await mountImported();
    await openExportDrawer(wrapper);
    expect(wrapper.find('[data-test="exam-workspace-export-zero-points"]').exists()).toBe(false);

    await selectItemRow(wrapper, "item_002");
    const points = wrapper.get('[data-test="exam-workspace-item-points-input"]');
    await points.setValue("0");
    expect(wrapper.get('[data-test="exam-workspace-export-zero-points"]').text()).toBe(
      ZERO_POINTS_NOTE,
    );

    await points.setValue("2");
    expect(wrapper.find('[data-test="exam-workspace-export-zero-points"]').exists()).toBe(false);
  });
});

/**
 * The rendered loss entry that names `questionText`, found through its
 * listitem role. `undefined` when the checklist shows no such loss.
 */
function findLossEntry(wrapper: ViewWrapper, questionText: string) {
  return wrapper.findAll("li").find((entry) => entry.text().includes(questionText));
}

describe("ExamWorkspaceView export checklist", () => {
  beforeEach(() => {
    apiMocks.downloadExamWorkspaceExport.mockResolvedValue({
      blob: new Blob(["qti"]),
      contentType: "application/zip",
      filename: "prov-qti.zip",
    });
  });

  it("lists what Exam.net loses after a successful QTI export", async () => {
    apiMocks.getExamWorkspaceExportChecklist.mockResolvedValue(LOST_CHECKLIST);
    const wrapper = await mountImported();

    await exportFromMenu(wrapper, "qti");

    expect(apiMocks.getExamWorkspaceExportChecklist).toHaveBeenCalledWith("lineage-1", 1);
    await openMenu(wrapper);
    expect(requirePage("exam-workspace-export-checklist-open").text()).toContain(
      "Det här tappar Exam.net (3)",
    );
    await openChecklistDrawer(wrapper);
    const criteriaEntry = findLossEntry(wrapper, "Förklara fotosyntesen.");
    expect(criteriaEntry?.text()).toContain("Fråga 2: Förklara fotosyntesen.");
    expect(criteriaEntry?.text()).toContain("Tar upp koldioxid (1 p)");
    expect(criteriaEntry?.text()).toContain("Beskriver sockerbildningen (2 p)");
    expect(findLossEntry(wrapper, "Vatten kokar vid ...")?.text()).toContain("2 poäng");
    const roundedGapsEntry = findLossEntry(wrapper, "Fyll i luckorna.");
    expect(roundedGapsEntry?.text()).toContain("4 poäng");
    expect(roundedGapsEntry?.text()).toMatch(/1[.,]33\s*poäng/);
  });

  it("hides the checklist when the export loses nothing", async () => {
    const wrapper = await mountImported();

    await exportFromMenu(wrapper, "qti");

    expect(apiMocks.getExamWorkspaceExportChecklist).toHaveBeenCalledWith("lineage-1", 1);
    await openMenu(wrapper);
    expect(page("exam-workspace-export-checklist-open")).toBeNull();
    await openExportDrawer(wrapper);
    expect(wrapper.find('[data-test="exam-workspace-export-checklist"]').exists()).toBe(false);
    expect(findLossEntry(wrapper, "Förklara fotosyntesen.")).toBeUndefined();
    expect(useToastStore().warning).not.toHaveBeenCalled();
  });

  it("requests no checklist for a PDF or DOCX export", async () => {
    const wrapper = await mountImported();

    await exportFromMenu(wrapper, "pdf");
    await exportFromMenu(wrapper, "docx");

    expect(apiMocks.getExamWorkspaceExportChecklist).not.toHaveBeenCalled();
  });

  it("clears the checklist when the draft changes", async () => {
    apiMocks.getExamWorkspaceExportChecklist.mockResolvedValue(LOST_CHECKLIST);
    const wrapper = await mountImported();
    await exportFromMenu(wrapper, "qti");
    await openChecklistDrawer(wrapper);
    expect(findLossEntry(wrapper, "Förklara fotosyntesen.")).toBeDefined();

    await selectItemRow(wrapper, "item_002");
    await wrapper.find('[data-test="exam-workspace-item-points-input"]').setValue("7");
    await flushPromises();

    expect(findLossEntry(wrapper, "Förklara fotosyntesen.")).toBeUndefined();
    expect(wrapper.find('[data-test="exam-workspace-export-checklist"]').exists()).toBe(false);
    await openMenu(wrapper);
    expect(page("exam-workspace-export-checklist-open")).toBeNull();
  });

  it("clears the checklist when another export starts", async () => {
    apiMocks.getExamWorkspaceExportChecklist.mockResolvedValue(LOST_CHECKLIST);
    const wrapper = await mountImported();
    await exportFromMenu(wrapper, "qti");
    await openChecklistDrawer(wrapper);
    expect(findLossEntry(wrapper, "Förklara fotosyntesen.")).toBeDefined();

    const pdfDownload = deferred<{ blob: Blob; contentType: string; filename: string }>();
    apiMocks.downloadExamWorkspaceExport.mockReturnValueOnce(pdfDownload.promise);
    await exportFromMenu(wrapper, "pdf");
    expect(findLossEntry(wrapper, "Förklara fotosyntesen.")).toBeUndefined();

    pdfDownload.resolve({ blob: new Blob(["pdf"]), contentType: "application/pdf", filename: "Prov.pdf" });
    await flushPromises();
    expect(findLossEntry(wrapper, "Förklara fotosyntesen.")).toBeUndefined();
  });

  it("keeps the fresh checklist when a stale response arrives late", async () => {
    const staleChecklist = deferred<ExamWorkspaceExportChecklistResponse>();
    apiMocks.getExamWorkspaceExportChecklist.mockReturnValueOnce(staleChecklist.promise);
    const wrapper = await mountImported();
    await exportFromMenu(wrapper, "qti");

    await selectItemRow(wrapper, "item_002");
    await wrapper.find('[data-test="exam-workspace-item-points-input"]').setValue("7");
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(exportableResponse({ version: 2 }));
    await saveDocument(wrapper);

    const freshChecklist: ExamWorkspaceExportChecklistResponse = {
      entries: [
        {
          kind: "all_or_nothing",
          question_number: "3",
          question_text: "Ny fråga efter sparning.",
          points: 2,
        },
      ],
    };
    apiMocks.getExamWorkspaceExportChecklist.mockResolvedValueOnce(freshChecklist);
    await exportFromMenu(wrapper, "qti");
    await openChecklistDrawer(wrapper);
    expect(findLossEntry(wrapper, "Ny fråga efter sparning.")).toBeDefined();

    staleChecklist.resolve(LOST_CHECKLIST);
    await flushPromises();

    expect(findLossEntry(wrapper, "Ny fråga efter sparning.")).toBeDefined();
    expect(findLossEntry(wrapper, "Förklara fotosyntesen.")).toBeUndefined();
    expect(apiMocks.getExamWorkspaceExportChecklist).toHaveBeenNthCalledWith(1, "lineage-1", 1);
    expect(apiMocks.getExamWorkspaceExportChecklist).toHaveBeenNthCalledWith(2, "lineage-1", 2);
  });

  it("warns without claiming the export failed when the checklist request fails", async () => {
    apiMocks.getExamWorkspaceExportChecklist.mockRejectedValue(
      new ApiError({ code: "INTERNAL_ERROR", message: "boom", status: 500 }),
    );
    const wrapper = await mountImported();

    await exportFromMenu(wrapper, "qti");

    expect(downloadMocks.triggerBrowserDownload).toHaveBeenCalledWith(
      expect.any(Blob),
      "prov-qti.zip",
    );
    expect(useToastStore().warning).toHaveBeenCalledTimes(1);
    expect(useToastStore().warning).toHaveBeenCalledWith(
      "QTI-paketet är skapat. Listan över vad Exam.net tappar kunde inte hämtas.",
    );
    expect(useToastStore().failure).not.toHaveBeenCalled();
    await openExportDrawer(wrapper);
    expect(wrapper.find('[data-test="exam-workspace-export-notice"]').exists()).toBe(false);
    expect(findLossEntry(wrapper, "Förklara fotosyntesen.")).toBeUndefined();
  });

  it("warns without claiming the export failed when the saved head changed", async () => {
    apiMocks.getExamWorkspaceExportChecklist.mockRejectedValue(
      new ApiError({ code: "CONFLICT", message: "head changed", status: 409 }),
    );
    const wrapper = await mountImported();

    await exportFromMenu(wrapper, "qti");

    expect(apiMocks.downloadExamWorkspaceExport).toHaveBeenCalledWith("lineage-1", "qti", 1);
    expect(downloadMocks.triggerBrowserDownload).toHaveBeenCalledWith(
      expect.any(Blob),
      "prov-qti.zip",
    );
    expect(useToastStore().warning).toHaveBeenCalledTimes(1);
    expect(useToastStore().failure).not.toHaveBeenCalled();
    await openExportDrawer(wrapper);
    expect(wrapper.find('[data-test="exam-workspace-export-notice"]').exists()).toBe(false);
    expect(findLossEntry(wrapper, "Förklara fotosyntesen.")).toBeUndefined();
  });

  it("ignores a stale checklist failure", async () => {
    const staleChecklist = deferred<ExamWorkspaceExportChecklistResponse>();
    apiMocks.getExamWorkspaceExportChecklist.mockReturnValueOnce(staleChecklist.promise);
    const wrapper = await mountImported();
    await exportFromMenu(wrapper, "qti");

    await selectItemRow(wrapper, "item_002");
    await wrapper.find('[data-test="exam-workspace-item-points-input"]').setValue("7");
    await flushPromises();

    staleChecklist.reject(new ApiError({ code: "INTERNAL_ERROR", message: "boom", status: 500 }));
    await flushPromises();

    expect(useToastStore().warning).not.toHaveBeenCalled();
  });
});
