/**
 * Printed totals are advisory, live warnings, never a save or export gate
 * (user ruling 2026-10-17): a part's line and the exam total read
 * "14 p · provtexten anger 15 p" in amber while they differ. Each difference
 * is said once, on its own level: no header warning repeats it.
 */
import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ExamWorkspaceConversionStatus, NativeExamDocument } from "../../api/examWorkspace";
import {
  buildDocument,
  buildFreeTextItem,
  buildResponse,
  importFixtureDocument,
  mountExamWorkspace,
  selectItemRow,
  type ViewWrapper,
} from "./ExamWorkspaceSlice.specSupport";
import { examWorkspacePointsLine, examWorkspacePrintedDifference } from "./exam-workspace/examWorkspaceTotals";
import type { ExamWorkspaceLayout } from "./exam-workspace/useExamWorkspaceLayout";

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

const succeeded: ExamWorkspaceConversionStatus = {
  job_id: "job-1", lineage_id: "lineage-1", state: "succeeded", error_message: null, summary: null,
  document_revision: 1, questions_total: 0, questions_done: 0, units: [],
};
const mounted: ViewWrapper[] = [];
const WARNING = '[data-test="exam-workspace-points-warning"]';
const EXAM_POINTS = '[data-test="exam-workspace-exam-points"]';

function documentWithTotals(printed: number | null, points: (number | null)[]): NativeExamDocument {
  return {
    ...buildDocument(),
    header: { course_hint: "Svenska 2", printed_total: printed, tags: [] },
    items: points.map((value, index) => ({ ...buildFreeTextItem(index + 1), points: value })),
  };
}

async function openDocument(document: NativeExamDocument, layout: ExamWorkspaceLayout = "desktop") {
  apiMocks.getExamWorkspaceDocument.mockResolvedValue({
    ...buildResponse({ version: 1, conversion: succeeded }),
    document,
    saved_document: document,
  });
  // The shell's top bar slot receives the header's title and Spara on a phone.
  const slot = globalThis.document.createElement("div");
  slot.id = "app-topbar-page-slot";
  globalThis.document.body.append(slot);
  const host = globalThis.document.createElement("div");
  globalThis.document.body.append(host);
  const { wrapper } = await mountExamWorkspace({}, layout, host);
  mounted.push(wrapper);
  await importFixtureDocument(wrapper);
  return wrapper;
}

function partLine(wrapper: ViewWrapper, parentId: string) {
  return wrapper.get(`[data-test="exam-workspace-row-${parentId}"]`).find('[data-test="exam-workspace-part-points"]');
}

beforeEach(() => {
  for (const mock of Object.values(apiMocks)) mock.mockReset();
  downloadMocks.triggerBrowserDownload.mockReset();
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [], ordering: "course" });
  apiMocks.getExamWorkspaceConversionStatus.mockResolvedValue(succeeded);
  apiMocks.importExamWorkspaceDocument.mockResolvedValue({ ...succeeded, state: "queued", document_revision: null });
  apiMocks.getExamWorkspaceExportChecklist.mockResolvedValue({ entries: [] });
});
afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
  globalThis.document.body.replaceChildren();
});

describe("workspace printed exam totals", () => {
  it.each([
    { printed: null, points: [2, 3] },
    { printed: 5, points: [2, 3] },
    { printed: 7.5, points: [2.5, 5] },
    { printed: 0, points: [null, 0] },
  ])("shows no warning for an absent or matching total ($printed)", async ({ printed, points }) => {
    const wrapper = await openDocument(documentWithTotals(printed, points));
    expect(wrapper.find(WARNING).exists()).toBe(false);
    expect(wrapper.get(EXAM_POINTS).text()).not.toContain("provtexten");
    expect(wrapper.get(EXAM_POINTS).find(".list__printed").exists()).toBe(false);
  });

  it("states both decimal totals on one line, uses no jargon, and still exports", async () => {
    const wrapper = await openDocument(documentWithTotals(7.5, [2.5, 4]));
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 6,5 p · provtexten anger 7,5 p");
    expect(wrapper.get(EXAM_POINTS).get(".list__sum").text()).toBe("6,5 p");
    expect(wrapper.get(EXAM_POINTS).get(".list__printed").text()).toBe("· provtexten anger 7,5 p");
    expect(wrapper.find(WARNING).exists()).toBe(false);
    expect(wrapper.text()).not.toContain("Poängen stämmer inte");
    expect(wrapper.text()).not.toMatch(/Tryckt|TRYCKT/);

    apiMocks.downloadExamWorkspaceExport.mockResolvedValue({
      blob: new Blob(["export"]), contentType: "application/zip", filename: "prov.zip",
    });
    await wrapper.get('[data-test="exam-workspace-export"]').trigger("click");
    // The menu is teleported to the body.
    const entry = document.body.querySelector<HTMLElement>('[data-test="exam-workspace-export-qti"]')!;
    expect(entry.getAttribute("aria-disabled")).toBeNull();
    entry.click();
    await flushPromises();
    expect(apiMocks.downloadExamWorkspaceExport).toHaveBeenCalledWith("lineage-1", "qti", 1);
    expect(downloadMocks.triggerBrowserDownload).toHaveBeenCalledTimes(1);
  });

  it("recomputes the exam and part lines on a point edit without a save or reload", async () => {
    const document = documentWithTotals(7.5, [2.5, 5]);
    document.parents = [{
      parent_id: "parent_001", item_ids: ["item_001", "item_002"],
      printed_total: 7.5, instruction: [],
    }];
    const wrapper = await openDocument(document);
    expect(wrapper.find(WARNING).exists()).toBe(false);
    expect(partLine(wrapper, "parent_001").exists()).toBe(false);

    await selectItemRow(wrapper, "item_001");
    await wrapper.get('[data-test="exam-workspace-item-points-input"]').setValue("3.5");
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 8,5 p · provtexten anger 7,5 p");
    expect(partLine(wrapper, "parent_001").text()).toBe("8,5 p · provtexten anger 7,5 p");

    await wrapper.get('[data-test="exam-workspace-item-points-input"]').setValue("2.5");
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 7,5 p");
    expect(partLine(wrapper, "parent_001").exists()).toBe(false);
    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(apiMocks.saveExamWorkspaceDocument).not.toHaveBeenCalled();
  });

  it("never disables Spara for a mismatch", async () => {
    const wrapper = await openDocument(documentWithTotals(10, [2, 3]));
    await selectItemRow(wrapper, "item_001");
    await wrapper.get('[data-test="exam-workspace-item-points-input"]').setValue("4");
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 7 p · provtexten anger 10 p");
    expect(wrapper.get('[data-test="exam-workspace-save"]').attributes("disabled")).toBeUndefined();
  });

  it("shows no part line without a printed part total", async () => {
    const document = documentWithTotals(null, [2, 3]);
    document.parents = [{
      parent_id: "parent_001", item_ids: ["item_001", "item_002"],
      printed_total: null, instruction: [],
    }];
    const wrapper = await openDocument(document);
    expect(wrapper.get('[data-test="exam-workspace-row-parent_001"]').text()).toContain("5 p");
    expect(partLine(wrapper, "parent_001").exists()).toBe(false);
  });

  it("puts a part difference only on its own part and its instruction, said once per level", async () => {
    const document = documentWithTotals(null, [2, 3, 1, 4]);
    document.parents = [
      { parent_id: "parent_002", item_ids: ["item_003", "item_004"], printed_total: 8, instruction: [] },
      { parent_id: "parent_001", item_ids: ["item_001", "item_002"], printed_total: 5, instruction: [] },
    ];
    const wrapper = await openDocument(document);
    expect(partLine(wrapper, "parent_001").exists()).toBe(false);
    expect(partLine(wrapper, "parent_002").text()).toBe("5 p · provtexten anger 8 p");
    expect(wrapper.findAll('[data-test="exam-workspace-row-parent_002"] [data-test="exam-workspace-part-points"]'))
      .toHaveLength(1);
    // The meta line drops its points, so "5 p" is not said twice on the row.
    expect(wrapper.get('[data-test="exam-workspace-row-parent_002"]').text().match(/5 p/g)).toHaveLength(1);

    expect(wrapper.find(WARNING).exists()).toBe(false);
    await wrapper.get('[data-test="exam-workspace-row-parent_002"]').trigger("click");

    const editor = wrapper.get('[data-test="exam-workspace-instruction-editor"]');
    expect(editor.get('[data-test="exam-workspace-part-points"]').text()).toBe("5 p · provtexten anger 8 p");
    expect(wrapper.get('[data-test="exam-workspace-row-parent_002"]').attributes("aria-selected")).toBe("true");
  });

  it("says an exam total difference once, on the footer line, with no header warning", async () => {
    const wrapper = await openDocument(documentWithTotals(9, [2, 3]));
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 5 p · provtexten anger 9 p");
    expect(wrapper.find(WARNING).exists()).toBe(false);
    expect(wrapper.text().match(/provtexten anger/g)).toHaveLength(1);
  });
});

describe("total comparison edge cases", () => {
  it("treats a printed zero as a real total, not a missing value", () => {
    expect(examWorkspacePrintedDifference(0, [buildFreeTextItem(1)])).toBe(0);
  });

  it("keeps a sub-hundredth difference visible instead of showing identical numbers", () => {
    const item = { ...buildFreeTextItem(1), points: 7.502 };
    expect(examWorkspacePrintedDifference(7.501, [item])).toBe(7.501);
    expect(examWorkspacePointsLine(7.502, 7.501)).toBe("7,502 p · provtexten anger 7,501 p");
  });

  it("does not invent a mismatch from binary floating-point addition", () => {
    const items = [0.1, 0.2].map((points, index) => ({ ...buildFreeTextItem(index + 1), points }));
    expect(examWorkspacePrintedDifference(0.3, items)).toBeNull();
    expect(examWorkspacePrintedDifference(0.4, items)).toBe(0.4);
    expect(examWorkspacePointsLine(0.1 + 0.2, 0.4)).toBe("0,3 p · provtexten anger 0,4 p");
  });
});
