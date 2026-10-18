/**
 * Exam workspace export blocker behavior.
 *
 * Expected behavior:
 *   Whatever stops the export is a red "Kan inte exporteras ännu" row per
 *   question before any click, in the list's words, and disables every
 *   format; a row's in-place fix (Godkänn, Markera som granskad, Ta bort
 *   tomma, Ta bort rubrikformat) clears it, and the formats enable when the
 *   last row is gone. The server's 422 stays the final check: its rows hold
 *   until the teacher changes that question.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../api/client";
import { useToastStore } from "../../stores/toast";
import { plainBody } from "./exam-workspace/examWorkspaceRichText";
import {
  arrangeExportApis,
  exportableResponse,
  exportFromMenu,
  menuFormatDisabled,
  mountImported,
  openExportDrawer,
  openMenu,
  page,
  pageAll,
  requirePage,
  succeededConversion,
  unmountWrappers,
} from "./ExamWorkspaceExportsSlice.specSupport";
import { buildResponse, saveDocument, selectItemRow } from "./ExamWorkspaceSlice.specSupport";

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

describe("ExamWorkspaceView export blockers", () => {
  /** The default fixture: questions 3 and 4 hold an unreviewed proposed key. */
  function importDefaultFixture() {
    apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
      apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(
        buildResponse({ conversion: succeededConversion, version: 1 }),
      );
      return { job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null,
        document_revision: null, questions_total: 0, questions_done: 0, units: [] };
    });
  }

  it("blocks every format before the click and enables them when the last in-place fix clears the panel", async () => {
    apiMocks.downloadExamWorkspaceExport.mockResolvedValue({
      blob: new Blob(["zip"]),
      contentType: "application/zip",
      filename: "NO-prov HT25.zip",
    });
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(exportableResponse({ version: 2 }));
    importDefaultFixture();
    const wrapper = await mountImported();

    await openMenu(wrapper);
    expect(requirePage("exam-workspace-export-blockers").text()).toContain("Kan inte exporteras ännu");
    expect(requirePage("exam-workspace-blocker-item_003").text()).toBe("Fråga 3: facit ej granskat");
    expect(requirePage("exam-workspace-blocker-item_004").text()).toBe("Fråga 4: facit ej granskat");
    for (const target of ["qti", "pdf", "docx"]) {
      expect(menuFormatDisabled(target)).toBe("true");
      expect(requirePage(`exam-workspace-export-save-${target}`).attributes("disabled")).toBeDefined();
    }
    await requirePage("exam-workspace-export-qti").trigger("click");
    await flushPromises();
    expect(apiMocks.downloadExamWorkspaceExport).not.toHaveBeenCalled();

    expect(requirePage("exam-workspace-blocker-fix-item_003").text()).toBe("Godkänn");
    await requirePage("exam-workspace-blocker-fix-item_003").trigger("click");
    await flushPromises();
    // The fix keeps the menu open; the next row stays and still blocks.
    expect(page("exam-workspace-blocker-item_003")).toBeNull();
    expect(menuFormatDisabled("qti")).toBe("true");
    await requirePage("exam-workspace-blocker-fix-item_004").trigger("click");
    await flushPromises();

    expect(page("exam-workspace-export-blockers")).toBeNull();
    expect(menuFormatDisabled("qti")).toBeUndefined();
    // One click on the enabled format saves the approvals and exports that version.
    await requirePage("exam-workspace-export-qti").trigger("click");
    await flushPromises();
    expect(apiMocks.saveExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    const saved = apiMocks.saveExamWorkspaceDocument.mock.calls[0]![1].document;
    for (const itemId of ["item_003", "item_004"]) {
      expect(saved.items.find((item: { item_id: string }) => item.item_id === itemId).answer_key.origin)
        .toBe("reviewed_advisory");
    }
    expect(apiMocks.downloadExamWorkspaceExport).toHaveBeenCalledWith("lineage-1", "qti", 2);
    expect(apiMocks.saveExamWorkspaceDocument.mock.invocationCallOrder[0]!).toBeLessThan(
      apiMocks.downloadExamWorkspaceExport.mock.invocationCallOrder[0]!,
    );
    expect(requirePage("exam-workspace-export-menu-result").text()).toBe("QTI-paketet är skapat.");
  });

  it("removes question 2's empty choice in place, and its row leads to that choice", async () => {
    apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
      const response = exportableResponse({ conversion: succeededConversion, version: 1 });
      for (const document of [response.document, response.saved_document]) {
        document.items = document.items.map((item) =>
          item.item_id === "item_002"
            ? { ...item, choices: [...item.choices, { body: plainBody(" "), choice_id: "choice_004" }] }
            : item,
        );
      }
      apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(response);
      return { job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null,
        document_revision: null, questions_total: 0, questions_done: 0, units: [] };
    });
    const wrapper = await mountImported();

    await openMenu(wrapper);
    expect(requirePage("exam-workspace-blocker-item_002").text()).toBe("Fråga 2: tomt svarsalternativ");
    await requirePage("exam-workspace-blocker-item_002").trigger("click");
    await flushPromises();
    expect(document.activeElement?.getAttribute("data-test")).toBe("exam-workspace-choice-text-choice_004");

    await openMenu(wrapper);
    expect(requirePage("exam-workspace-blocker-fix-item_002").text()).toBe("Ta bort tomma");
    await requirePage("exam-workspace-blocker-fix-item_002").trigger("click");
    await flushPromises();

    expect(page("exam-workspace-export-blockers")).toBeNull();
    expect(menuFormatDisabled("qti")).toBeUndefined();
    expect(wrapper.find('[data-test="exam-workspace-choice-text-choice_004"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-choice-text-choice_003"]').exists()).toBe(true);
  });

  it("leads a row to its question and focuses the field that holds the problem", async () => {
    importDefaultFixture();
    const wrapper = await mountImported();

    await openMenu(wrapper);
    await requirePage("exam-workspace-blocker-item_004").trigger("click");
    await flushPromises();

    expect(page("exam-workspace-export-menu")).toBeNull();
    expect(wrapper.get('[data-test="exam-workspace-row-item_004"]').attributes("aria-selected")).toBe("true");
    expect(document.activeElement?.getAttribute("data-test")).toBe("exam-workspace-review");
  });

  it("maps 422 export blockers to Swedish copy per blocked question in the drawer and menu", async () => {
    apiMocks.downloadExamWorkspaceExport.mockRejectedValue(
      new ApiError({
        code: "VALIDATION_ERROR",
        details: {
          blockers: [
            { item_id: "item_003", reason: "unbuilt_question" },
            { item_id: "item_003", reason: "machine_proposed_key_unreviewed" },
            { item_id: "item_004", reason: "unbuilt_question" },
            { item_id: "item_005", reason: "missing_points" },
          ],
        },
        message: "Provet har frågor som måste åtgärdas före export.",
        status: 422,
      }),
    );
    const wrapper = await mountImported();

    await exportFromMenu(wrapper, "pdf");

    expect(downloadMocks.triggerBrowserDownload).not.toHaveBeenCalled();
    expect(useToastStore().warning).toHaveBeenCalledWith(
      "Filen kan inte skapas ännu. Åtgärda frågorna i listan och exportera igen.",
    );
    // The menu stays open on the refusal: one row per question, its first reason.
    expect(pageAll("exam-workspace-blocker-item_003").map((row) => row.text())).toEqual([
      "Fråga 3: kunde inte konverteras",
    ]);
    expect(requirePage("exam-workspace-blocker-fix-item_003").text()).toBe("Markera som granskad");
    expect(requirePage("exam-workspace-blocker-item_004").text()).toBe("Fråga 4: kunde inte konverteras");
    expect(requirePage("exam-workspace-blocker-item_005").text()).toBe("Fråga 5: poäng saknas");
    expect(page("exam-workspace-blocker-fix-item_005")).toBeNull();
    expect(page("exam-workspace-blocker-item_001")).toBeNull();
    for (const target of ["qti", "pdf", "docx"]) {
      expect(menuFormatDisabled(target)).toBe("true");
    }
    await openExportDrawer(wrapper);
    expect(wrapper.get('[data-test="exam-workspace-blocker-item_005"]').text()).toBe("Fråga 5: poäng saknas");
    expect(wrapper.get('[data-test="exam-workspace-export-run"]').attributes("disabled")).toBeDefined();
    expect(wrapper.get('[data-test="exam-workspace-export-notice"]').text()).toBe(
      "Filen kan inte skapas ännu. Åtgärda frågorna i listan och exportera igen.",
    );
  });

  it.each([
    ["missing_answer_key", "Fråga 2: facit saknas", "Föreslå facit"],
    ["inline_choice_option_heading", "Fråga 2: rubrik i rullista", "Ta bort rubrikformat"],
  ])("names %s in the list's words with its fix on the blocked question", async (reason, row, fix) => {
    apiMocks.downloadExamWorkspaceExport.mockRejectedValue(
      new ApiError({
        code: "VALIDATION_ERROR",
        details: { blockers: [{ item_id: "item_002", reason }] },
        message: "Provet har frågor som måste åtgärdas före export.",
        status: 422,
      }),
    );
    const wrapper = await mountImported();

    await exportFromMenu(wrapper, "qti");

    expect(downloadMocks.triggerBrowserDownload).not.toHaveBeenCalled();
    await openExportDrawer(wrapper);
    expect(wrapper.get('[data-test="exam-workspace-blocker-item_002"]').text()).toBe(row);
    expect(wrapper.get('[data-test="exam-workspace-blocker-fix-item_002"]').text()).toBe(fix);
  });

  it.each([false, true])(
    "keeps all empty-content blockers actionable in a 422 (mixed: %s)", async (mixed) => {
      apiMocks.downloadExamWorkspaceExport.mockRejectedValue(
        new ApiError({
          code: "VALIDATION_ERROR",
          details: {
            blockers: [
              { item_id: "item_002", reason: "empty_choice" },
              { item_id: "item_003", reason: "empty_gap_option" },
              { item_id: "item_004", reason: "empty_match_entry" },
              ...(mixed ? [{ item_id: "item_002", reason: "missing_answer_key" }] : []),
            ],
          },
          message: "blocked",
          status: 422,
        }),
      );
      const wrapper = await mountImported();
      await exportFromMenu(wrapper, "qti");

      expect(downloadMocks.triggerBrowserDownload).not.toHaveBeenCalled();
      await openExportDrawer(wrapper);
      const notice = wrapper.get('[data-test="exam-workspace-export-notice"]').text();
      const blockerText = (itemId: string) =>
        wrapper.findAll(`[data-test="exam-workspace-blocker-${itemId}"]`).map((entry) => entry.text()).join(" ");
      for (const [itemId, row] of [
        ["item_002", "Fråga 2: tomt svarsalternativ"],
        ["item_003", "Fråga 3: tomt alternativ i rullista"],
        ["item_004", "Fråga 4: tom rad eller kategori"],
      ]) {
        // One row per question, even when the server gave it two reasons.
        expect(blockerText(itemId)).toBe(row);
      }
      expect(notice).toBe("Filen kan inte skapas ännu. Åtgärda frågorna i listan och exportera igen.");
      expect(notice).not.toContain("Försök igen");
      expect(useToastStore().warning).toHaveBeenCalledWith(notice);
      expect(useToastStore().failure).not.toHaveBeenCalled();
      expect(downloadMocks.triggerBrowserDownload).not.toHaveBeenCalled();
    },
  );

  it("clears export blockers when a new version is saved", async () => {
    apiMocks.downloadExamWorkspaceExport.mockRejectedValue(
      new ApiError({
        code: "VALIDATION_ERROR",
        details: { blockers: [{ item_id: "item_005", reason: "missing_points" }] },
        message: "blocked",
        status: 422,
      }),
    );
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(exportableResponse({ version: 2 }));
    const wrapper = await mountImported();
    await exportFromMenu(wrapper, "docx");
    await openExportDrawer(wrapper);
    expect(wrapper.find('[data-test="exam-workspace-blocker-item_005"]').exists()).toBe(true);

    await selectItemRow(wrapper, "item_005");
    await wrapper.find('[data-test="exam-workspace-item-points-input"]').setValue("3");
    // Changing the refused question drops its refusal, so the next export can ask again.
    expect(wrapper.find('[data-test="exam-workspace-blocker-item_005"]').exists()).toBe(false);
    await saveDocument(wrapper);

    expect(wrapper.find('[data-test="exam-workspace-blocker-item_005"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-export-notice"]').exists()).toBe(false);
    await openMenu(wrapper);
    expect(page("exam-workspace-export-blockers")).toBeNull();
    expect(menuFormatDisabled("docx")).toBeUndefined();
  });
});
