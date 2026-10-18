/**
 * Exam title export blocker (TASK-SKRIPT-40-04-05).
 *
 * Expected behavior:
 *   A title with no letter or digit is a red "Kan inte exporteras ännu" row
 *   before any click, with every format disabled; the row jumps to the title
 *   field in Provets uppgifter, and typing a valid title clears it. The
 *   server's own title refusal shows the same row until the title changes.
 *   The download uses the file name the server sent.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import {
  arrangeExportApis,
  exportableResponse,
  menuFormatDisabled,
  mountImported,
  openMenu,
  page,
  requirePage,
  succeededConversion,
  unmountWrappers,
} from "../ExamWorkspaceExportsSlice.specSupport";
import { arrangeStepHistory } from "../ExamWorkspaceHistory.specSupport";

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

vi.mock("../../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../../test/examCourseCatalog")).getExamCourseCatalog,
}));

const downloadMocks = vi.hoisted(() => ({ triggerBrowserDownload: vi.fn() }));

vi.mock("../exam-converter/browserDownload", () => downloadMocks);

const TITLE_ROW = "Ge provet en titel med bokstäver eller siffror";

function importTitled(title: string): void {
  apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
    const response = exportableResponse({ conversion: succeededConversion, version: 1 });
    response.document.title = title;
    response.saved_document.title = title;
    response.summary.title = title;
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(response);
    return { job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null,
      document_revision: null, questions_total: 0, questions_done: 0, units: [] };
  });
}

function savedWithTitle(title: string) {
  const response = exportableResponse({ version: 2 });
  response.document.title = title;
  response.saved_document.title = title;
  response.summary.title = title;
  return response;
}

beforeEach(() => {
  arrangeExportApis({ api: apiMocks, download: downloadMocks });
  arrangeStepHistory(apiMocks);
});

afterEach(unmountWrappers);

describe("ExamWorkspaceView title export blocker", () => {
  it.each(["?!...", "  ", " - / ", "(…)"])(
    "blocks every format before the click for the title %j and exports nothing",
    async (title) => {
      importTitled(title);
      const wrapper = await mountImported();

      await openMenu(wrapper);

      expect(requirePage("exam-workspace-blocker-title").text()).toBe(TITLE_ROW);
      expect(page("exam-workspace-blocker-fix-title")).toBeNull();
      for (const target of ["qti", "pdf", "docx"]) {
        expect(menuFormatDisabled(target)).toBe("true");
      }
      await requirePage("exam-workspace-export-qti").trigger("click");
      await flushPromises();
      expect(apiMocks.saveExamWorkspaceDocument).not.toHaveBeenCalled();
      expect(apiMocks.downloadExamWorkspaceExport).not.toHaveBeenCalled();
    },
  );

  it("leaves a title with a letter or digit unblocked even when it is mostly punctuation", async () => {
    importTitled("?! 7 ...");
    const wrapper = await mountImported();

    await openMenu(wrapper);

    expect(page("exam-workspace-blocker-title")).toBeNull();
    expect(menuFormatDisabled("qti")).toBeUndefined();
  });

  it("jumps to the title field, clears after a valid title, and then downloads under the server's name", async () => {
    importTitled("?!...");
    apiMocks.saveExamWorkspaceDocument.mockImplementation(async (_lineage, body) =>
      savedWithTitle(body.document.title),
    );
    apiMocks.downloadExamWorkspaceExport.mockResolvedValue({
      blob: new Blob(["zip"]),
      contentType: "application/zip",
      filename: "Server Prov 1.zip",
    });
    const wrapper = await mountImported();

    await openMenu(wrapper);
    await requirePage("exam-workspace-blocker-title").trigger("click");
    await flushPromises();

    expect(page("exam-workspace-export-menu")).toBeNull();
    expect(wrapper.find('[data-test="exam-workspace-drawer-details"]').exists()).toBe(true);
    expect(document.activeElement?.getAttribute("data-test")).toBe("exam-workspace-metadata-title");

    await wrapper.get('[data-test="exam-workspace-metadata-title"]').setValue("Prov 1");
    await flushPromises();
    await openMenu(wrapper);

    expect(page("exam-workspace-blocker-title")).toBeNull();
    expect(menuFormatDisabled("qti")).toBeUndefined();
    await requirePage("exam-workspace-export-qti").trigger("click");
    await flushPromises();
    expect(downloadMocks.triggerBrowserDownload).toHaveBeenCalledWith(expect.any(Blob), "Server Prov 1.zip");
  });

  it("shows the title row again when the title is emptied of letters, then clears it", async () => {
    importTitled("Prov 1");
    const wrapper = await mountImported();
    await wrapper.get('[data-test="exam-workspace-title"]').trigger("click");
    await flushPromises();
    const input = wrapper.get('[data-test="exam-workspace-metadata-title"]');

    await input.setValue("!!!");
    await openMenu(wrapper);
    expect(requirePage("exam-workspace-blocker-title").text()).toBe(TITLE_ROW);

    await input.setValue("Prov 2");
    await flushPromises();
    expect(page("exam-workspace-blocker-title")).toBeNull();
  });

  it("shows the server's title refusal as the same row until the title changes", async () => {
    importTitled("Prov 1");
    apiMocks.downloadExamWorkspaceExport.mockRejectedValue(
      new ApiError({
        code: "VALIDATION_ERROR",
        details: { blockers: [{ item_id: null, reason: "title_without_text" }] },
        message: "Provet har frågor som måste åtgärdas före export.",
        status: 422,
      }),
    );
    const wrapper = await mountImported();

    await openMenu(wrapper);
    await requirePage("exam-workspace-export-pdf").trigger("click");
    await flushPromises();

    expect(downloadMocks.triggerBrowserDownload).not.toHaveBeenCalled();
    expect(requirePage("exam-workspace-blocker-title").text()).toBe(TITLE_ROW);
    expect(menuFormatDisabled("pdf")).toBe("true");

    await requirePage("exam-workspace-blocker-title").trigger("click");
    await flushPromises();
    await wrapper.get('[data-test="exam-workspace-metadata-title"]').setValue("Prov 2");
    await flushPromises();
    await openMenu(wrapper);
    expect(page("exam-workspace-blocker-title")).toBeNull();
  });
});
