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
 *   from the saved version. A successful QTI export also lists what Exam.net
 *   loses on import for the exported revision; edits, saves and new exports
 *   clear that list, and a stale response never replaces the current one.
 */

import { flushPromises } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../api/client";
import type {
  ExamWorkspaceConversionStatus,
  ExamWorkspaceExportChecklistResponse,
} from "../../api/examWorkspace";
import { useToastStore } from "../../stores/toast";
import {
  buildResponse,
  importFixtureDocument,
  mountExamWorkspace,
  saveDocument,
  selectItemRow,
  type ViewWrapper,
} from "./ExamWorkspaceSlice.specSupport";

const apiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceExportChecklist: vi.fn(),
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

function deferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, reject, resolve };
}

/** One entry per loss the checklist lists, as the server sends them. */
const LOST_CHECKLIST: ExamWorkspaceExportChecklistResponse = {
  entries: [
    {
      kind: "free_text_criteria",
      question_number: "2",
      question_text: "Förklara fotosyntesen.",
      points: 3,
      criteria: [
        { text: "Tar upp koldioxid", points: 1 },
        { text: "Beskriver sockerbildningen", points: 2 },
      ],
    },
    {
      kind: "all_or_nothing",
      question_number: "4",
      question_text: "Vatten kokar vid ...",
      points: 2,
    },
    {
      kind: "rounded_gaps",
      question_number: "6",
      question_text: "Fyll i luckorna.",
      points: 4,
      gap_points: 1.33,
    },
  ],
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
  apiMocks.getExamWorkspaceExportChecklist.mockResolvedValue({ entries: [] });
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

      expect(apiMocks.downloadExamWorkspaceExport).toHaveBeenCalledWith("lineage-1", target, 1);
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

  it("points to the reload control when a save elsewhere moved the saved exam", async () => {
    apiMocks.downloadExamWorkspaceExport.mockRejectedValue(
      new ApiError({ code: "CONFLICT", message: "stale", status: 409 }),
    );
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await wrapper.find('[data-test="exam-workspace-export-qti"]').trigger("click");
    await flushPromises();

    const notice = wrapper.find('[data-test="exam-workspace-export-notice"]').text();
    expect(notice).toContain("Läs in på nytt");
    expect(notice).not.toContain("Försök igen");
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
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await wrapper.find('[data-test="exam-workspace-export-qti"]').trigger("click");
    await flushPromises();

    expect(apiMocks.getExamWorkspaceExportChecklist).toHaveBeenCalledWith("lineage-1", 1);
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
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await wrapper.find('[data-test="exam-workspace-export-qti"]').trigger("click");
    await flushPromises();

    expect(apiMocks.getExamWorkspaceExportChecklist).toHaveBeenCalledWith("lineage-1", 1);
    expect(findLossEntry(wrapper, "Förklara fotosyntesen.")).toBeUndefined();
    expect(useToastStore().warning).not.toHaveBeenCalled();
  });

  it("requests no checklist for a PDF or DOCX export", async () => {
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await wrapper.find('[data-test="exam-workspace-export-pdf"]').trigger("click");
    await flushPromises();
    await wrapper.find('[data-test="exam-workspace-export-docx"]').trigger("click");
    await flushPromises();

    expect(apiMocks.getExamWorkspaceExportChecklist).not.toHaveBeenCalled();
  });

  it("clears the checklist when the draft changes", async () => {
    apiMocks.getExamWorkspaceExportChecklist.mockResolvedValue(LOST_CHECKLIST);
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);
    await wrapper.find('[data-test="exam-workspace-export-qti"]').trigger("click");
    await flushPromises();
    expect(findLossEntry(wrapper, "Förklara fotosyntesen.")).toBeDefined();

    await selectItemRow(wrapper, "item_002");
    await wrapper.find('[data-test="exam-workspace-item-points-input"]').setValue("7");
    await flushPromises();

    expect(findLossEntry(wrapper, "Förklara fotosyntesen.")).toBeUndefined();
  });

  it("clears the checklist when another export starts", async () => {
    apiMocks.getExamWorkspaceExportChecklist.mockResolvedValue(LOST_CHECKLIST);
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);
    await wrapper.find('[data-test="exam-workspace-export-qti"]').trigger("click");
    await flushPromises();
    expect(findLossEntry(wrapper, "Förklara fotosyntesen.")).toBeDefined();

    const pdfDownload = deferred<{ blob: Blob; contentType: string; filename: string | null }>();
    apiMocks.downloadExamWorkspaceExport.mockReturnValueOnce(pdfDownload.promise);
    await wrapper.find('[data-test="exam-workspace-export-pdf"]').trigger("click");
    await flushPromises();
    expect(findLossEntry(wrapper, "Förklara fotosyntesen.")).toBeUndefined();

    pdfDownload.resolve({ blob: new Blob(["pdf"]), contentType: "application/pdf", filename: null });
    await flushPromises();
    expect(findLossEntry(wrapper, "Förklara fotosyntesen.")).toBeUndefined();
  });

  it("keeps the fresh checklist when a stale response arrives late", async () => {
    const staleChecklist = deferred<ExamWorkspaceExportChecklistResponse>();
    apiMocks.getExamWorkspaceExportChecklist.mockReturnValueOnce(staleChecklist.promise);
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);
    await wrapper.find('[data-test="exam-workspace-export-qti"]').trigger("click");
    await flushPromises();

    await selectItemRow(wrapper, "item_002");
    await wrapper.find('[data-test="exam-workspace-item-points-input"]').setValue("7");
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 2 }));
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
    await wrapper.find('[data-test="exam-workspace-export-qti"]').trigger("click");
    await flushPromises();
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
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await wrapper.find('[data-test="exam-workspace-export-qti"]').trigger("click");
    await flushPromises();

    expect(downloadMocks.triggerBrowserDownload).toHaveBeenCalledWith(
      expect.any(Blob),
      "prov-qti.zip",
    );
    expect(useToastStore().warning).toHaveBeenCalledTimes(1);
    expect(useToastStore().failure).not.toHaveBeenCalled();
    expect(wrapper.find('[data-test="exam-workspace-export-notice"]').exists()).toBe(false);
    expect(findLossEntry(wrapper, "Förklara fotosyntesen.")).toBeUndefined();
  });

  it("warns without claiming the export failed when the saved head changed", async () => {
    apiMocks.getExamWorkspaceExportChecklist.mockRejectedValue(
      new ApiError({ code: "CONFLICT", message: "head changed", status: 409 }),
    );
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await wrapper.find('[data-test="exam-workspace-export-qti"]').trigger("click");
    await flushPromises();

    expect(apiMocks.downloadExamWorkspaceExport).toHaveBeenCalledWith("lineage-1", "qti", 1);
    expect(downloadMocks.triggerBrowserDownload).toHaveBeenCalledWith(
      expect.any(Blob),
      "prov-qti.zip",
    );
    expect(useToastStore().warning).toHaveBeenCalledTimes(1);
    expect(useToastStore().failure).not.toHaveBeenCalled();
    expect(wrapper.find('[data-test="exam-workspace-export-notice"]').exists()).toBe(false);
    expect(findLossEntry(wrapper, "Förklara fotosyntesen.")).toBeUndefined();
  });

  it("ignores a stale checklist failure", async () => {
    const staleChecklist = deferred<ExamWorkspaceExportChecklistResponse>();
    apiMocks.getExamWorkspaceExportChecklist.mockReturnValueOnce(staleChecklist.promise);
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);
    await wrapper.find('[data-test="exam-workspace-export-qti"]').trigger("click");
    await flushPromises();

    await selectItemRow(wrapper, "item_002");
    await wrapper.find('[data-test="exam-workspace-item-points-input"]').setValue("7");
    await flushPromises();

    staleChecklist.reject(new ApiError({ code: "INTERNAL_ERROR", message: "boom", status: 500 }));
    await flushPromises();

    expect(useToastStore().warning).not.toHaveBeenCalled();
  });
});
