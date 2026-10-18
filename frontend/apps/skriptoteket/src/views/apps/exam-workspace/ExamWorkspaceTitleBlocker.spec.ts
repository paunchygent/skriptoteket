/**
 * Exam title export blocker (TASK-SKRIPT-40-04-05).
 *
 * Expected behavior:
 *   The workspace owns no title rule: a title the server's export gate judged
 *   without a letter or digit (on open, Spara, the autosave after a typing
 *   pause, or a refused export) is a red "Kan inte exporteras ännu" row before
 *   any click, with every format disabled; the row jumps to the title field in
 *   Provets uppgifter, and changing the title clears it at once. The refusal
 *   names the title, not the questions. The download uses the file name the
 *   server sent.
 *
 *   The server here is a test double: `judge` stands in for the gate's
 *   `title_without_text` verdict. It is synthetic, not observed server behavior.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import { useToastStore } from "../../../stores/toast";
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
import { EXAM_WORKSPACE_TYPING_PAUSE_MS } from "./useExamWorkspaceHistory";

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

vi.mock("../../../api/examWorkspaceExports", () => apiMocks);
vi.mock("../../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../../test/examCourseCatalog")).getExamCourseCatalog,
}));

const downloadMocks = vi.hoisted(() => ({ triggerBrowserDownload: vi.fn() }));

vi.mock("../../../utils/browserDownload", () => downloadMocks);

const TITLE_ROW = "Ge provet en titel med bokstäver eller siffror";
const TITLE_REFUSAL = {
  code: "VALIDATION_ERROR",
  details: { blockers: [{ item_id: null, reason: "title_without_text" }] },
  message: "Ge provet en titel med bokstäver eller siffror.",
  status: 422,
} as const;

/** The test double's verdict: the server's `title_without_text` for this title. */
function judge(title: string) {
  return /[\p{L}\p{N}]/u.test(title) ? [] : [{ item_id: null, reason: "title_without_text" as const }];
}

function importTitled(title: string): void {
  apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
    const response = exportableResponse({ conversion: succeededConversion, version: 1 });
    response.document.title = title;
    response.saved_document.title = title;
    response.summary.title = title;
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce({ ...response, export_blockers: judge(title) });
    return { job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null,
      document_revision: null, questions_total: 0, questions_done: 0, units: [] };
  });
}

function savedWithTitle(title: string) {
  const response = exportableResponse({ version: 2 });
  response.document.title = title;
  response.saved_document.title = title;
  response.summary.title = title;
  return { ...response, export_blockers: judge(title) };
}

/** The autosave double judges the stored step like the server does. */
function judgeAutosaves(): void {
  const store = apiMocks.storeExamWorkspaceUndoStep.getMockImplementation()!;
  apiMocks.storeExamWorkspaceUndoStep.mockImplementation(async (lineage, request) => ({
    ...(await store(lineage, request)),
    export_blockers: judge(request.document.title),
  }));
}

beforeEach(() => {
  arrangeExportApis({ api: apiMocks, download: downloadMocks });
  arrangeStepHistory(apiMocks);
  judgeAutosaves();
  apiMocks.saveExamWorkspaceDocument.mockImplementation(async (_lineage, body) =>
    savedWithTitle(body.document.title),
  );
});

afterEach(() => {
  vi.useRealTimers();
  unmountWrappers();
});

async function typeTitle(wrapper: Awaited<ReturnType<typeof mountImported>>, title: string): Promise<void> {
  await wrapper.get('[data-test="exam-workspace-metadata-title"]').setValue(title);
}

async function openTitleField(wrapper: Awaited<ReturnType<typeof mountImported>>) {
  await wrapper.get('[data-test="exam-workspace-title"]').trigger("click");
  await flushPromises();
}

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

  it("leaves a title the server accepted unblocked even when it is mostly punctuation", async () => {
    importTitled("?! 7 ...");
    const wrapper = await mountImported();

    await openMenu(wrapper);

    expect(page("exam-workspace-blocker-title")).toBeNull();
    expect(menuFormatDisabled("qti")).toBeUndefined();
  });

  it("jumps to the title field, clears at once on a changed title, and then downloads under the server's name", async () => {
    importTitled("?!...");
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

    await typeTitle(wrapper, "Prov 1");
    await flushPromises();
    await openMenu(wrapper);

    expect(page("exam-workspace-blocker-title")).toBeNull();
    expect(menuFormatDisabled("qti")).toBeUndefined();
    await requirePage("exam-workspace-export-qti").trigger("click");
    await flushPromises();
    expect(downloadMocks.triggerBrowserDownload).toHaveBeenCalledWith(expect.any(Blob), "Server Prov 1.zip");
  });

  it("shows the row once the autosave after the typing pause has judged an emptied title, then clears it on the next edit", async () => {
    importTitled("Prov 1");
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    const wrapper = await mountImported();
    await openTitleField(wrapper);

    await typeTitle(wrapper, "!!!");
    await openMenu(wrapper);
    expect(page("exam-workspace-blocker-title")).toBeNull();

    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_TYPING_PAUSE_MS);
    await flushPromises();
    expect(requirePage("exam-workspace-blocker-title").text()).toBe(TITLE_ROW);
    expect(menuFormatDisabled("pdf")).toBe("true");

    await typeTitle(wrapper, "Prov 2");
    await flushPromises();
    expect(page("exam-workspace-blocker-title")).toBeNull();
  });

  it.each(["", "   "])(
    "stores the emptied title %j with the autosave, shows the red row with every format disabled and no failure toast",
    async (title) => {
      importTitled("Prov 1");
      vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
      const wrapper = await mountImported();
      await openTitleField(wrapper);

      await typeTitle(wrapper, title);
      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_TYPING_PAUSE_MS);
      await flushPromises();

      const stored = apiMocks.storeExamWorkspaceUndoStep.mock.calls.at(-1)?.[1];
      expect(stored?.document.title).toBe(title);
      expect(useToastStore().failure).not.toHaveBeenCalled();
      await openMenu(wrapper);
      expect(requirePage("exam-workspace-blocker-title").text()).toBe(TITLE_ROW);
      for (const target of ["qti", "pdf", "docx"]) {
        expect(menuFormatDisabled(target)).toBe("true");
      }
    },
  );

  it("saves an emptied title with Spara, shows the red row and raises no failure toast", async () => {
    importTitled("Prov 1");
    const wrapper = await mountImported();
    await openTitleField(wrapper);

    await typeTitle(wrapper, "   ");
    await wrapper.get('[data-test="exam-workspace-save"]').trigger("click");
    await flushPromises();

    expect(apiMocks.saveExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(apiMocks.saveExamWorkspaceDocument.mock.calls[0]?.[1].document.title).toBe("   ");
    expect(useToastStore().failure).not.toHaveBeenCalled();
    await openMenu(wrapper);
    expect(requirePage("exam-workspace-blocker-title").text()).toBe(TITLE_ROW);
    expect(menuFormatDisabled("qti")).toBe("true");
  });

  it("shows the row when the server refuses an export clicked before the autosave judged the title", async () => {
    importTitled("Prov 1");
    apiMocks.downloadExamWorkspaceExport.mockRejectedValue(new ApiError(TITLE_REFUSAL));
    const wrapper = await mountImported();
    await openTitleField(wrapper);

    await typeTitle(wrapper, "!!!");
    await openMenu(wrapper);
    expect(menuFormatDisabled("pdf")).toBeUndefined();
    await requirePage("exam-workspace-export-pdf").trigger("click");
    await flushPromises();

    expect(downloadMocks.triggerBrowserDownload).not.toHaveBeenCalled();
    expect(requirePage("exam-workspace-blocker-title").text()).toBe(TITLE_ROW);
    expect(menuFormatDisabled("pdf")).toBe("true");
  });

  it("names the title, not the questions, when the title is the only refusal", async () => {
    importTitled("Prov 1");
    apiMocks.downloadExamWorkspaceExport.mockRejectedValue(new ApiError(TITLE_REFUSAL));
    const wrapper = await mountImported();

    await openMenu(wrapper);
    await requirePage("exam-workspace-export-pdf").trigger("click");
    await flushPromises();

    const [notice] = vi.mocked(useToastStore().warning).mock.calls[0] ?? [];
    expect(notice).toContain("titel");
    expect(notice).not.toContain("frågorna");
    expect(requirePage("exam-workspace-blocker-title").text()).toBe(TITLE_ROW);

    await requirePage("exam-workspace-blocker-title").trigger("click");
    await flushPromises();
    await typeTitle(wrapper, "Prov 2");
    await flushPromises();
    await openMenu(wrapper);
    expect(page("exam-workspace-blocker-title")).toBeNull();
  });

  it("names the title and the questions when both refuse", async () => {
    importTitled("Prov 1");
    apiMocks.downloadExamWorkspaceExport.mockRejectedValue(
      new ApiError({
        ...TITLE_REFUSAL,
        details: {
          blockers: [
            { item_id: null, reason: "title_without_text" },
            { item_id: "item_003", reason: "unbuilt_question" },
          ],
        },
      }),
    );
    const wrapper = await mountImported();

    await openMenu(wrapper);
    await requirePage("exam-workspace-export-pdf").trigger("click");
    await flushPromises();

    const [notice] = vi.mocked(useToastStore().warning).mock.calls[0] ?? [];
    expect(notice).toContain("titeln");
    expect(notice).toContain("frågorna");
  });
});
