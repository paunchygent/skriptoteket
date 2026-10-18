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
import { HISTORY_BASELINE_STEP_ID, arrangeStepHistory } from "./ExamWorkspaceHistory.specSupport";
import { examWorkspacePointsLine, examWorkspacePrintedDifference } from "./exam-workspace/examWorkspaceTotals";
import type { ExamWorkspaceLayout } from "./exam-workspace/useExamWorkspaceLayout";

const apiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
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
vi.mock("../../utils/browserDownload", () => downloadMocks);

const succeeded: ExamWorkspaceConversionStatus = {
  job_id: "job-1", lineage_id: "lineage-1", state: "succeeded", error_message: null, summary: null,
  document_revision: 1, questions_total: 0, questions_done: 0, units: [],
};
const mounted: ViewWrapper[] = [];
let history: ReturnType<typeof arrangeStepHistory>;
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
  history.documents.set(HISTORY_BASELINE_STEP_ID, document);
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
  history = arrangeStepHistory(apiMocks);
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
    // The meta line drops its points, so "5 p" is said only by the amber line and its accept button.
    expect(wrapper.get('[data-test="exam-workspace-row-parent_002"]').text().match(/5 p/g)).toHaveLength(2);

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

describe("accepting the computed totals", () => {
  const ACCEPT_EXAM = '[data-test="exam-workspace-accept-exam-total"]';
  const ACCEPT_ALL = '[data-test="exam-workspace-accept-all-totals"]';
  const acceptPart = (parentId: string) => `[data-test="exam-workspace-accept-part-total-${parentId}"]`;

  /** Items 2+3 = 5 and 1+4 = 5 (exam 10); the exam prints 14 and each part 8 or 6. */
  function twoPartsPrintingOtherTotals(examPrinted: number | null = 14): NativeExamDocument {
    const document = documentWithTotals(examPrinted, [2, 3, 1, 4]);
    document.parents = [
      { parent_id: "parent_001", item_ids: ["item_001", "item_002"], printed_total: 8, instruction: [] },
      { parent_id: "parent_002", item_ids: ["item_003", "item_004"], printed_total: 6, instruction: [] },
    ];
    return document;
  }

  async function undo(wrapper: ViewWrapper) {
    await wrapper.get('[data-test="exam-workspace-undo"]').trigger("click");
    await flushPromises();
  }

  it("clears only the exam total from the footer, and Ångra brings the printed number back", async () => {
    const wrapper = await openDocument(twoPartsPrintingOtherTotals());
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 10 p · provtexten anger 14 p");
    expect(wrapper.get(ACCEPT_EXAM).text()).toBe("Använd 10 p");

    await wrapper.get(ACCEPT_EXAM).trigger("click");
    await flushPromises();

    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 10 p");
    expect(wrapper.find(ACCEPT_EXAM).exists()).toBe(false);
    expect(partLine(wrapper, "parent_001").text()).toBe("5 p · provtexten anger 8 p");
    expect(partLine(wrapper, "parent_002").text()).toBe("5 p · provtexten anger 6 p");
    expect(apiMocks.saveExamWorkspaceDocument).not.toHaveBeenCalled();

    await undo(wrapper);
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 10 p · provtexten anger 14 p");
  });

  it("clears only one part from its row without selecting it, and from the instruction editor", async () => {
    const wrapper = await openDocument(twoPartsPrintingOtherTotals());
    await wrapper.get('[data-test="exam-workspace-row-parent_002"]').trigger("click");
    expect(wrapper.get('[data-test="exam-workspace-row-parent_002"]').attributes("aria-selected")).toBe("true");
    const selectedBefore = wrapper.get('[aria-selected="true"]').attributes("data-entry-id");

    expect(wrapper.get(acceptPart("parent_001")).text()).toBe("Använd 5 p");
    await wrapper.get(acceptPart("parent_001")).trigger("click");
    await flushPromises();

    expect(partLine(wrapper, "parent_001").exists()).toBe(false);
    expect(partLine(wrapper, "parent_002").text()).toBe("5 p · provtexten anger 6 p");
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 10 p · provtexten anger 14 p");
    expect(wrapper.get('[aria-selected="true"]').attributes("data-entry-id")).toBe(selectedBefore);

    await undo(wrapper);
    expect(partLine(wrapper, "parent_001").text()).toBe("5 p · provtexten anger 8 p");

    const editor = wrapper.get('[data-test="exam-workspace-instruction-editor"]');
    expect(editor.get('[data-test="exam-workspace-accept-part-total"]').text()).toBe("Använd 5 p");
    await editor.get('[data-test="exam-workspace-accept-part-total"]').trigger("click");
    await flushPromises();
    expect(partLine(wrapper, "parent_002").exists()).toBe(false);
    expect(partLine(wrapper, "parent_001").text()).toBe("5 p · provtexten anger 8 p");
    expect(wrapper.find('[data-test="exam-workspace-accept-part-total"]').exists()).toBe(false);
  });

  it("clears the exam and every part in one step that one Ångra restores", async () => {
    const wrapper = await openDocument(twoPartsPrintingOtherTotals());

    await wrapper.get(ACCEPT_ALL).trigger("click");
    await flushPromises();

    expect(wrapper.text()).not.toContain("provtexten anger");
    expect(wrapper.find(ACCEPT_ALL).exists()).toBe(false);
    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(1);

    await undo(wrapper);
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 10 p · provtexten anger 14 p");
    expect(partLine(wrapper, "parent_001").text()).toBe("5 p · provtexten anger 8 p");
    expect(partLine(wrapper, "parent_002").text()).toBe("5 p · provtexten anger 6 p");
    expect(wrapper.get('[data-test="exam-workspace-undo"]').attributes("disabled")).toBeDefined();
  });

  it("offers the footer action only while a level differs, also when only a part does", async () => {
    const equal = await openDocument(documentWithTotals(5, [2, 3]));
    expect(equal.find(ACCEPT_ALL).exists()).toBe(false);
    expect(equal.find(ACCEPT_EXAM).exists()).toBe(false);

    const onlyPart = await openDocument(twoPartsPrintingOtherTotals(10));
    expect(onlyPart.find(ACCEPT_EXAM).exists()).toBe(false);
    expect(onlyPart.get(ACCEPT_ALL).text()).toBe("Använd beräknade summor");
    await onlyPart.get(ACCEPT_ALL).trigger("click");
    await flushPromises();
    expect(onlyPart.find(ACCEPT_ALL).exists()).toBe(false);
  });

  it("names a decimal sum as the line shows it", async () => {
    const document = documentWithTotals(9, [2.5, 5]);
    document.parents = [{
      parent_id: "parent_001", item_ids: ["item_001", "item_002"], printed_total: 9, instruction: [],
    }];
    const wrapper = await openDocument(document);
    expect(wrapper.get(ACCEPT_EXAM).text()).toBe("Använd 7,5 p");
    expect(wrapper.get(acceptPart("parent_001")).text()).toBe("Använd 7,5 p");
  });
});
