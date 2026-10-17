/**
 * Exam workspace export slice behavior.
 *
 * Slice purpose:
 *   Lock the on-demand QTI, PDF, and DOCX downloads from the saved head
 *   revision and the Swedish per-question mapping of the server export gate.
 *
 * Expected behavior:
 *   Whatever stops the export is a red "Kan inte exporteras ännu" row per
 *   question before any click, in the list's words, and disables every
 *   format; a row's in-place fix (Godkänn, Markera som granskad, Ta bort
 *   tomma, Ta bort rubrikformat) clears it, and the formats enable when the
 *   last row is gone. A format click saves unsaved changes first and exports
 *   the version just saved; a failed save exports nothing. The server's 422
 *   stays the final check: its rows hold until the teacher changes that
 *   question. A 409 reads the latest version in. A
 *   created file is reported inline (menu and drawer), never as a success
 *   toast; failures and warnings stay toasts. A successful QTI export also
 *   lists what Exam.net loses on import for the exported revision; edits,
 *   saves and new exports clear that list, and a stale response never
 *   replaces the current one. With any question at 0 points the QTI choice
 *   carries a note that Exam.net imports it as 1 point, without blocking.
 */

import { DOMWrapper, flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../api/client";
import type {
  ExamWorkspaceConversionStatus,
  ExamWorkspaceExportChecklistResponse,
} from "../../api/examWorkspace";
import { useToastStore } from "../../stores/toast";
import { plainBody } from "./exam-workspace/examWorkspaceRichText";
import {
  buildFreeTextItem,
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

vi.mock("../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../test/examCourseCatalog")).getExamCourseCatalog,
}));

const downloadMocks = vi.hoisted(() => ({ triggerBrowserDownload: vi.fn() }));

vi.mock("./exam-converter/browserDownload", () => downloadMocks);

const ZERO_POINTS_NOTE =
  "Exam.net ger frågor med 0 poäng 1 poäng. Ändra poängen i Exam.net efter importen.";

/** The finished import: its poll status, and the conversion its fetched document carries. */
const succeededConversion: ExamWorkspaceConversionStatus = {
  job_id: "job-1", lineage_id: "lineage-1", state: "succeeded", error_message: null, summary: null,
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

/**
 * The fixture exam without client-side export blockers. The default fixture
 * holds two questions whose proposed key is unreviewed, which the menu
 * blocks before any request, so exports that must reach the server use this.
 */
function exportableResponse(params: {
  conversion?: ExamWorkspaceConversionStatus | null;
  version: number;
}) {
  const response = buildResponse(params);
  for (const document of [response.document, response.saved_document]) {
    document.items = document.items.map((item) =>
      item.item_id === "item_003" || item.item_id === "item_004"
        ? buildFreeTextItem(Number(item.item_id.slice(-1)))
        : item,
    );
  }
  return response;
}

const wrappers: ViewWrapper[] = [];

beforeEach(() => {
  for (const mock of Object.values(apiMocks)) {
    mock.mockReset();
  }
  apiMocks.getExamWorkspaceConversionStatus.mockResolvedValue(succeededConversion);
  downloadMocks.triggerBrowserDownload.mockReset();
  apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(
      exportableResponse({ conversion: succeededConversion, version: 1 }),
    );
    return { job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null,
      document_revision: null, questions_total: 0, questions_done: 0, units: [] };
  });
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [], ordering: "course" });
  apiMocks.getExamWorkspaceExportChecklist.mockResolvedValue({ entries: [] });
});

afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount();
  document.body.replaceChildren();
});

/** The workspace with the fixture exam imported, attached so the body-level menu is reachable. */
async function mountImported(): Promise<ViewWrapper> {
  const { wrapper } = await mountExamWorkspace({}, "desktop", document.body);
  wrappers.push(wrapper);
  await importFixtureDocument(wrapper);
  return wrapper;
}

/** An element anywhere in the page: the Exportera menu is teleported to the body. */
function page(testId: string): DOMWrapper<HTMLElement> | null {
  const element = document.body.querySelector<HTMLElement>(`[data-test="${testId}"]`);
  return element ? new DOMWrapper(element) : null;
}

function pageAll(testId: string): DOMWrapper<HTMLElement>[] {
  return Array.from(document.body.querySelectorAll<HTMLElement>(`[data-test="${testId}"]`)).map(
    (element) => new DOMWrapper(element),
  );
}

function requirePage(testId: string): DOMWrapper<HTMLElement> {
  const found = page(testId);
  if (!found) throw new Error(`Missing [data-test="${testId}"]`);
  return found;
}

async function openMenu(wrapper: ViewWrapper): Promise<void> {
  if (!page("exam-workspace-export-menu")) {
    await wrapper.get('[data-test="exam-workspace-export"]').trigger("click");
    await flushPromises();
  }
}

/** Download `target` through the header menu. */
async function exportFromMenu(wrapper: ViewWrapper, target: "qti" | "pdf" | "docx"): Promise<void> {
  await openMenu(wrapper);
  await requirePage(`exam-workspace-export-${target}`).trigger("click");
  await flushPromises();
}

/** Open the Exportera drawer through "Fler val …". */
async function openExportDrawer(wrapper: ViewWrapper): Promise<void> {
  await openMenu(wrapper);
  await requirePage("exam-workspace-export-more").trigger("click");
  await flushPromises();
  expect(wrapper.find('[data-test="exam-workspace-drawer-export"]').exists()).toBe(true);
}

/** Open the Exportera drawer through the menu's "Det här tappar Exam.net" entry. */
async function openChecklistDrawer(wrapper: ViewWrapper): Promise<void> {
  await openMenu(wrapper);
  await requirePage("exam-workspace-export-checklist-open").trigger("click");
  await flushPromises();
  expect(wrapper.find('[data-test="exam-workspace-export-checklist"]').exists()).toBe(true);
}

function menuFormatDisabled(target: string): string | undefined {
  return requirePage(`exam-workspace-export-${target}`).attributes("aria-disabled");
}

/** Close the Exportera menu so a later `openMenu` reopens it from the current state. */
async function closeMenu(wrapper: ViewWrapper): Promise<void> {
  if (page("exam-workspace-export-menu")) {
    await wrapper.get('[data-test="exam-workspace-export"]').trigger("click");
    await flushPromises();
  }
}

describe("ExamWorkspaceView export slice", () => {
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
      filename: null,
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
      filename: null,
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
      filename: null,
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
    const download = deferred<{ blob: Blob; contentType: string; filename: null }>();
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
    download.resolve({ blob: new Blob(["zip"]), contentType: "application/zip", filename: null });
    await flushPromises();
    expect(page("exam-workspace-export-running")).toBeNull();
    expect(requirePage("exam-workspace-export-menu-result").text()).toBe("QTI-paketet är skapat.");
  });
});

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

    const pdfDownload = deferred<{ blob: Blob; contentType: string; filename: string | null }>();
    apiMocks.downloadExamWorkspaceExport.mockReturnValueOnce(pdfDownload.promise);
    await exportFromMenu(wrapper, "pdf");
    expect(findLossEntry(wrapper, "Förklara fotosyntesen.")).toBeUndefined();

    pdfDownload.resolve({ blob: new Blob(["pdf"]), contentType: "application/pdf", filename: null });
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
