/**
 * Exam workspace export slice behavior.
 *
 * Slice purpose:
 *   Lock the on-demand QTI, PDF, and DOCX downloads from the saved head
 *   revision and the Swedish per-item mapping of the server export gate.
 *
 * Expected behavior:
 *   Export buttons call the server for every target even when the client
 *   believes items still need review: the server gate decides. A 422 with
 *   `blockers` shows Swedish per-item copy in the item table; a new saved
 *   version clears it. Unsaved edits disable exports because files are built
 *   from the saved version.
 */

import { flushPromises } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../api/client";
import type { ExamWorkspaceConversionStatus } from "../../api/examWorkspace";
import {
  buildResponse,
  importFixtureDocument,
  mountExamWorkspace,
  saveDocument,
  selectItemRow,
} from "./ExamWorkspaceSlice.specSupport";

const apiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
}));

vi.mock("../../api/examWorkspace", () => apiMocks);

const downloadMocks = vi.hoisted(() => ({ triggerBrowserDownload: vi.fn() }));

vi.mock("./exam-converter/browserDownload", () => downloadMocks);

/** The finished import: its poll status, and the conversion its fetched document carries. */
const succeededConversion: ExamWorkspaceConversionStatus = {
  job_id: "job-1", lineage_id: "lineage-1", state: "succeeded", error_message: null,
  document_revision: 1, questions_total: 0, questions_done: 0, units: [],
};

beforeEach(() => {
  for (const mock of Object.values(apiMocks)) {
    mock.mockReset();
  }
  apiMocks.getExamWorkspaceConversionStatus.mockResolvedValue(succeededConversion);
  downloadMocks.triggerBrowserDownload.mockReset();
  apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(
      buildResponse({ conversion: succeededConversion, version: 1 }),
    );
    return { job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null,
      document_revision: null, questions_total: 0, questions_done: 0, units: [] };
  });
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [] });
});

describe("ExamWorkspaceView export slice", () => {
  it.each([
    ["qti", "NO-prov-qti.zip"],
    ["pdf", "NO-prov-examnet.pdf"],
    ["docx", "NO-prov.docx"],
  ] as const)(
    "downloads the %s export from the saved version with the server filename",
    async (target, filename) => {
      const blob = new Blob(["export"]);
      apiMocks.downloadExamWorkspaceExport.mockResolvedValue({
        blob,
        contentType: "application/octet-stream",
        filename,
      });
      const { wrapper } = await mountExamWorkspace();
      await importFixtureDocument(wrapper);

      await wrapper.find(`[data-test="exam-workspace-export-${target}"]`).trigger("click");
      await flushPromises();

      expect(apiMocks.downloadExamWorkspaceExport).toHaveBeenCalledWith("lineage-1", target);
      expect(downloadMocks.triggerBrowserDownload).toHaveBeenCalledWith(blob, filename);
      expect(wrapper.find('[data-test="exam-workspace-export-notice"]').exists()).toBe(false);
    },
  );

  it("asks the server even when the client sees items that still need review", async () => {
    apiMocks.downloadExamWorkspaceExport.mockResolvedValue({
      blob: new Blob(["zip"]),
      contentType: "application/zip",
      filename: null,
    });
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    const qtiButton = wrapper.find('[data-test="exam-workspace-export-qti"]');
    expect(qtiButton.attributes("disabled")).toBeUndefined();
    await qtiButton.trigger("click");
    await flushPromises();

    expect(apiMocks.downloadExamWorkspaceExport).toHaveBeenCalledTimes(1);
    expect(downloadMocks.triggerBrowserDownload).toHaveBeenCalledWith(
      expect.any(Blob),
      "prov-qti.zip",
    );
  });

  it("maps 422 export blockers to Swedish copy on each blocked item row", async () => {
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
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await wrapper.find('[data-test="exam-workspace-export-pdf"]').trigger("click");
    await flushPromises();

    expect(downloadMocks.triggerBrowserDownload).not.toHaveBeenCalled();
    const item3 = wrapper.find('[data-test="exam-workspace-item-blockers-item_003"]').text();
    expect(item3).toContain("Frågan kunde inte konverteras och visas som i källan.");
    expect(item3).toContain("Facitförslaget är inte godkänt.");
    expect(
      wrapper.find('[data-test="exam-workspace-item-blockers-item_005"]').text(),
    ).toContain("Poäng saknas.");
    expect(wrapper.find('[data-test="exam-workspace-item-blockers-item_001"]').exists()).toBe(
      false,
    );
    expect(wrapper.find('[data-test="exam-workspace-export-notice"]').text()).toContain(
      "Åtgärda de markerade frågorna",
    );
  });

  it("maps a missing answer key blocker to Swedish copy on the item row", async () => {
    apiMocks.downloadExamWorkspaceExport.mockRejectedValue(
      new ApiError({
        code: "VALIDATION_ERROR",
        details: { blockers: [{ item_id: "item_002", reason: "missing_answer_key" }] },
        message: "Provet har frågor som måste åtgärdas före export.",
        status: 422,
      }),
    );
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await wrapper.find('[data-test="exam-workspace-export-qti"]').trigger("click");
    await flushPromises();

    expect(downloadMocks.triggerBrowserDownload).not.toHaveBeenCalled();
    expect(
      wrapper.find('[data-test="exam-workspace-item-blockers-item_002"]').text(),
    ).toContain("Frågan saknar facit. Fyll i facit eller låt AI föreslå ett.");
  });

  it("clears export blockers when a new version is saved", async () => {
    apiMocks.downloadExamWorkspaceExport.mockRejectedValue(
      new ApiError({
        code: "VALIDATION_ERROR",
        details: { blockers: [{ item_id: "item_005", reason: "missing_points" }] },
        message: "blocked",
        status: 422,
      }),
    );
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 2 }));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);
    await wrapper.find('[data-test="exam-workspace-export-docx"]').trigger("click");
    await flushPromises();
    expect(wrapper.find('[data-test="exam-workspace-item-blockers-item_005"]').exists()).toBe(
      true,
    );

    await selectItemRow(wrapper, "item_005");
    await wrapper.find('[data-test="exam-workspace-item-points-input"]').setValue("3");
    await saveDocument(wrapper);

    expect(wrapper.find('[data-test="exam-workspace-item-blockers-item_005"]').exists()).toBe(
      false,
    );
    expect(wrapper.find('[data-test="exam-workspace-export-notice"]').exists()).toBe(false);
  });

  it("shows a Swedish failure notice when an export fails without item blockers", async () => {
    apiMocks.downloadExamWorkspaceExport.mockRejectedValue(
      new ApiError({ code: "INTERNAL_ERROR", message: "boom", status: 500 }),
    );
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await wrapper.find('[data-test="exam-workspace-export-qti"]').trigger("click");
    await flushPromises();

    expect(wrapper.find('[data-test="exam-workspace-export-notice"]').text()).toBe(
      "QTI-paketet kunde inte skapas. Försök igen.",
    );
  });

  it("disables exports while there are unsaved edits", async () => {
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_002");
    await wrapper
      .find('[data-test="exam-workspace-item-points-input"]')
      .setValue("7");

    for (const target of ["qti", "pdf", "docx"]) {
      expect(
        wrapper.find(`[data-test="exam-workspace-export-${target}"]`).attributes("disabled"),
      ).toBeDefined();
    }
    expect(wrapper.text()).toContain("Spara provet innan du skapar filer.");
  });
});
