/**
 * The printed-total difference is information, never a save or export gate
 * (user ruling 2026-10-17): the footer reads "Totalt N p" with the amber
 * points note below it while the exam text prints another total. The note
 * names one row per differing part and question with its point difference,
 * jumps to each on a click, and is answered with two glyph-only buttons: no
 * keeps the printed numbers and dismisses the note, yes clears the printed
 * totals. Every Använd action is gone.
 */
import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ExamWorkspaceConversionStatus, NativeExamDocument, NativeExamItem } from "../../api/examWorkspace";
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
import { examWorkspaceFormatPoints, examWorkspacePrintedDifference } from "./exam-workspace/examWorkspaceTotals";
import type { ExamWorkspaceLayout } from "./exam-workspace/useExamWorkspaceLayout";

const apiMocks = vi.hoisted(() => ({
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
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
vi.mock("../../utils/browserDownload", () => downloadMocks);

const succeeded: ExamWorkspaceConversionStatus = {
  job_id: "job-1", lineage_id: "lineage-1", state: "succeeded", error_message: null, summary: null,
  document_revision: 1, questions_total: 0, questions_done: 0, units: [],
};
const mounted: ViewWrapper[] = [];
let history: ReturnType<typeof arrangeStepHistory>;
const NOTE = '[data-test="exam-workspace-points-note"]';
const NOTE_ROW = '[data-test="exam-workspace-points-note-row"]';
const NOTE_KEEP = '[data-test="exam-workspace-points-keep"]';
const NOTE_USE = '[data-test="exam-workspace-points-use-computed"]';
const EXAM_POINTS = '[data-test="exam-workspace-exam-points"]';
const PART_POINTS_LINE = '[data-test="exam-workspace-part-points-line"]';

function itemWithTotals(sequence: number, points: number | null, source: number | null): NativeExamItem {
  return { ...buildFreeTextItem(sequence), points, source_points: source };
}

function documentWithTotals(
  printed: number | null,
  points: (number | null)[],
  sources?: (number | null)[],
): NativeExamDocument {
  return {
    ...buildDocument(),
    header: { course_hint: "Svenska 2", printed_total: printed, printed_total_dismissed: false, tags: [] },
    items: points.map((value, index) => itemWithTotals(index + 1, value, sources?.[index] ?? null)),
  };
}

/**
 * The mockup case (evidence/design/points-banner-v2-yes-no-glyphs.png):
 * the exam prints 70 p over questions summing to 67 p, with a differing
 * part (labels 3/3a/3b), a changed question (label 5) and a question
 * missing its points (label 8).
 */
function mockupDocument(): NativeExamDocument {
  const document = documentWithTotals(
    70,
    [10, 9, 10, 10, 8, 10, 5, 5, null],
    [10, 9, 10, 10, 8, 12, 5, 5, 4],
  );
  document.parents = [{
    parent_id: "parent_001",
    item_ids: ["item_003", "item_004"],
    place: 2,
    printed_total: 22,
    instruction: [
      { heading_level: null, segments: [{ kind: "text", marks: [], text: "Del 2: Satslösning" }] },
    ],
  }];
  return document;
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

function rowLine(parentId: string) {
  return `[data-test="exam-workspace-row-${parentId}"] ${PART_POINTS_LINE}`;
}

/** The element tags and classes of a row's lines, top to bottom: what must not change when the note is answered. */
function rowShape(wrapper: ViewWrapper, id: string): string[] {
  const body = wrapper.get(`[data-test="exam-workspace-row-${id}"]`).element.querySelector(".row__body");
  return Array.from(body?.children ?? []).map((line) => `${line.tagName}.${line.className}`);
}

/** The note's row texts in order, whitespace-normalised. */
function noteRows(wrapper: ViewWrapper): string[] {
  return wrapper.findAll(NOTE_ROW).map((row) => row.text().replace(/\s+/g, " ").trim());
}

async function undo(wrapper: ViewWrapper) {
  await wrapper.get('[data-test="exam-workspace-undo"]').trigger("click");
  await flushPromises();
}

beforeEach(() => {
  for (const mock of [...Object.values(apiMocks), ...Object.values(exportApiMocks)]) mock.mockReset();
  downloadMocks.triggerBrowserDownload.mockReset();
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [], ordering: "course" });
  apiMocks.getExamWorkspaceConversionStatus.mockResolvedValue(succeeded);
  apiMocks.importExamWorkspaceDocument.mockResolvedValue({ ...succeeded, state: "queued", document_revision: null });
  exportApiMocks.getExamWorkspaceExportChecklist.mockResolvedValue({ entries: [] });
  history = arrangeStepHistory(apiMocks);
});
afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
  globalThis.document.body.replaceChildren();
});

describe("workspace printed totals note", () => {
  it.each([
    { printed: null, points: [2, 3] },
    { printed: 5, points: [2, 3] },
    { printed: 7.5, points: [2.5, 5] },
    { printed: 0, points: [null, 0] },
  ])("shows no note for an absent or matching total ($printed)", async ({ printed, points }) => {
    const wrapper = await openDocument(documentWithTotals(printed, points));
    expect(wrapper.find(NOTE).exists()).toBe(false);
    expect(wrapper.get(EXAM_POINTS).text()).not.toContain("provtexten");
    expect(wrapper.find(".list__dismissed").exists()).toBe(false);
  });

  it("states the mockup case: the heading, one jump row per difference in order, and no Använd anywhere", async () => {
    const wrapper = await openDocument(mockupDocument());
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 67 p");
    expect(wrapper.get(NOTE).find(".list__note-head").text())
      .toBe("Provtexten anger 70 p. Dessa skiljer sig:");
    expect(noteRows(wrapper)).toEqual([
      "Del 2: Satslösning — provtexten 22 p, nu 20 p",
      "Fråga 5 — provtexten 12 p, nu 10 p",
      "Fråga 8 — provtexten 4 p, saknar poäng",
      "5 p fler än provtexten anger",
    ]);
    expect(wrapper.find('[data-test^="exam-workspace-accept-"]').exists()).toBe(false);
    // The decide line is plain text; no button in the list offers an Använd action.
    expect(wrapper.get(".list__note-question").text()).toBe("Använd beräknade poäng?");
    const list = wrapper.get('[data-test="exam-workspace-question-list"]');
    expect(list.findAll("button").filter((button) => button.text().startsWith("Använd"))).toHaveLength(0);
  });

  it("states the remainder for points no question explains", async () => {
    const wrapper = await openDocument(documentWithTotals(70, [30, 37], [30, 37]));
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 67 p");
    expect(wrapper.get(NOTE).find(".list__note-head").text())
      .toBe("Provtexten anger 70 p. Dessa skiljer sig:");
    expect(noteRows(wrapper)).toEqual(["Övriga 3 p finns inte i någon fråga"]);
  });

  it("names only the differing parts when the exam total is absent", async () => {
    const document = documentWithTotals(null, [2, 3]);
    document.parents = [{
      parent_id: "parent_001", item_ids: ["item_001", "item_002"], place: 0,
      printed_total: 8,
      instruction: [
        { heading_level: null, segments: [{ kind: "text", marks: [], text: "Del 1" }] },
      ],
    }];
    const wrapper = await openDocument(document);
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 5 p");
    expect(wrapper.get(NOTE).find(".list__note-head").text())
      .toBe("Dessa skiljer sig från provtexten:");
    expect(noteRows(wrapper)).toEqual(["Del 1 — provtexten 8 p, nu 5 p"]);
  });

  it("states both decimal totals in the note and still exports", async () => {
    const wrapper = await openDocument(documentWithTotals(7.5, [2.5, 4], [2.5, 4]));
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 6,5 p");
    expect(wrapper.get(NOTE).find(".list__note-head").text())
      .toBe("Provtexten anger 7,5 p. Dessa skiljer sig:");
    expect(noteRows(wrapper)).toEqual(["Övriga 1 p finns inte i någon fråga"]);
    expect(wrapper.text()).not.toContain("Poängen stämmer inte");
    expect(wrapper.text()).not.toMatch(/Tryckt|TRYCKT/);

    exportApiMocks.downloadExamWorkspaceExport.mockResolvedValue({
      blob: new Blob(["export"]), contentType: "application/zip", filename: "prov.zip",
    });
    await wrapper.get('[data-test="exam-workspace-export"]').trigger("click");
    // The menu is teleported to the body.
    const entry = document.body.querySelector<HTMLElement>('[data-test="exam-workspace-export-qti"]')!;
    expect(entry.getAttribute("aria-disabled")).toBeNull();
    entry.click();
    await flushPromises();
    expect(exportApiMocks.downloadExamWorkspaceExport).toHaveBeenCalledWith("lineage-1", "qti", 1);
    expect(downloadMocks.triggerBrowserDownload).toHaveBeenCalledTimes(1);
  });

  it("recomputes the note on a point edit without a save or reload", async () => {
    const wrapper = await openDocument(mockupDocument());

    await selectItemRow(wrapper, "item_006");
    await wrapper.get('[data-test="exam-workspace-item-points-input"]').setValue("9");
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 66 p");
    expect(noteRows(wrapper)).toContain("Fråga 5 — provtexten 12 p, nu 9 p");

    await wrapper.get('[data-test="exam-workspace-item-points-input"]').setValue("10");
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 67 p");
    expect(noteRows(wrapper)).toContain("Fråga 5 — provtexten 12 p, nu 10 p");
    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(apiMocks.saveExamWorkspaceDocument).not.toHaveBeenCalled();
  });

  it("never disables Spara for a mismatch", async () => {
    const wrapper = await openDocument(documentWithTotals(10, [2, 3]));
    await selectItemRow(wrapper, "item_001");
    await wrapper.get('[data-test="exam-workspace-item-points-input"]').setValue("4");
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 7 p");
    expect(wrapper.find(NOTE).exists()).toBe(true);
    expect(wrapper.get('[data-test="exam-workspace-save"]').attributes("disabled")).toBeUndefined();
  });

  it("shows plain points on a differing part's row and in its instruction editor", async () => {
    const document = documentWithTotals(null, [2, 3]);
    document.parents = [{
      parent_id: "parent_001", item_ids: ["item_001", "item_002"], place: 0,
      printed_total: 8, instruction: [],
    }];
    const wrapper = await openDocument(document);
    expect(wrapper.get(rowLine("parent_001")).text()).toBe("5 p");
    expect(wrapper.get(rowLine("parent_001")).get('[data-test="exam-workspace-part-points"]').text()).toBe("5 p");

    await wrapper.get('[data-test="exam-workspace-row-parent_001"]').trigger("click");
    const editor = wrapper.get('[data-test="exam-workspace-instruction-editor"]');
    expect(editor.get('[data-test="exam-workspace-part-points"]').text()).toBe("5 p");
    expect(editor.findAll("button").filter((button) => button.text().startsWith("Använd"))).toHaveLength(0);
    // The difference is said once, on the note's row.
    expect(noteRows(wrapper)).toHaveLength(1);
    expect(noteRows(wrapper)[0]).toContain("provtexten 8 p, nu 5 p");
  });

  it("says an exam total difference once, on the note, with a plain footer", async () => {
    const wrapper = await openDocument(documentWithTotals(9, [2, 3]));
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 5 p");
    expect(wrapper.get(NOTE).find(".list__note-head").text())
      .toBe("Provtexten anger 9 p. Dessa skiljer sig:");
    expect(wrapper.get(EXAM_POINTS).text()).not.toContain("provtexten");
  });
});

describe("total comparison edge cases", () => {
  it("treats a printed zero as a real total, not a missing value", () => {
    expect(examWorkspacePrintedDifference(0, [buildFreeTextItem(1)])).toBe(0);
  });

  it("detects a sub-hundredth difference while the shared format rounds both readings", () => {
    const item = { ...buildFreeTextItem(1), points: 7.502 };
    expect(examWorkspacePrintedDifference(7.501, [item])).toBe(7.501);
    expect(examWorkspaceFormatPoints(7.502)).toBe("7,5");
    expect(examWorkspaceFormatPoints(7.501)).toBe("7,5");
  });

  it("does not invent a mismatch from binary floating-point addition", () => {
    const items = [0.1, 0.2].map((points, index) => ({ ...buildFreeTextItem(index + 1), points }));
    expect(examWorkspacePrintedDifference(0.3, items)).toBeNull();
    expect(examWorkspacePrintedDifference(0.4, items)).toBe(0.4);
  });
});

describe("answering the points note", () => {
  it("no keeps the printed numbers in one undo step, hides the note and greys the footer", async () => {
    const wrapper = await openDocument(mockupDocument());
    expect(wrapper.find(NOTE).exists()).toBe(true);

    await wrapper.get(NOTE_KEEP).trigger("click");
    await flushPromises();

    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(1);
    const stored = apiMocks.storeExamWorkspaceUndoStep.mock.calls.at(-1)![1].document as NativeExamDocument;
    expect(stored.header.printed_total_dismissed).toBe(true);
    expect(stored.header.printed_total).toBe(70);
    expect(stored.parents.map((parent) => parent.printed_total)).toEqual([22]);
    expect(stored.items.map((item) => item.points))
      .toEqual([10, 9, 10, 10, 8, 10, 5, 5, null]);

    expect(wrapper.find(NOTE).exists()).toBe(false);
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 67 p · provtexten anger 70 p");
    expect(wrapper.get(EXAM_POINTS).get(".list__dismissed").text()).toBe("· provtexten anger 70 p");

    await undo(wrapper);
    expect(wrapper.find(NOTE).exists()).toBe(true);
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 67 p");
    expect(noteRows(wrapper)).toHaveLength(4);
  });

  it("yes clears the exam and part printed totals in one undo step", async () => {
    const wrapper = await openDocument(mockupDocument());

    await wrapper.get(NOTE_USE).trigger("click");
    await flushPromises();

    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(1);
    const stored = apiMocks.storeExamWorkspaceUndoStep.mock.calls.at(-1)![1].document as NativeExamDocument;
    expect(stored.header.printed_total).toBeNull();
    expect(stored.parents.map((parent) => parent.printed_total)).toEqual([null]);
    expect(stored.header.printed_total_dismissed).toBe(false);

    expect(wrapper.find(NOTE).exists()).toBe(false);
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 67 p");

    await undo(wrapper);
    expect(wrapper.find(NOTE).exists()).toBe(true);
    expect(noteRows(wrapper)).toHaveLength(4);
  });

  it("names the answers in the tooltip and aria-label only, with no visible text", async () => {
    const wrapper = await openDocument(mockupDocument());
    const keep = wrapper.get(NOTE_KEEP);
    const use = wrapper.get(NOTE_USE);

    expect(keep.text()).toBe("");
    expect(keep.attributes("aria-label")).toBe("Nej, behåll provtextens poäng");
    expect(keep.attributes("title")).toBe("Nej, behåll provtextens poäng");
    expect(use.text()).toBe("");
    expect(use.attributes("aria-label")).toBe("Ja, använd beräknade poäng");
    expect(use.attributes("title")).toBe("Ja, använd beräknade poäng");
  });

  it("selects the part or question when its note row is clicked", async () => {
    const wrapper = await openDocument(mockupDocument());

    await wrapper.findAll(NOTE_ROW).at(0)!.trigger("click");
    expect(wrapper.get('[data-test="exam-workspace-row-parent_001"]').attributes("aria-selected")).toBe("true");
    expect(wrapper.find('[data-test="exam-workspace-instruction-editor"]').exists()).toBe(true);

    await wrapper.findAll(NOTE_ROW).at(1)!.trigger("click");
    expect(wrapper.get('[data-test="exam-workspace-row-item_006"]').attributes("aria-selected")).toBe("true");
  });

  it("disables the note's buttons and jump rows while the workspace is busy", async () => {
    const document = documentWithTotals(10, [2, 3]);
    document.parents = [{
      parent_id: "parent_001",
      item_ids: ["item_001", "item_002"],
      place: 0,
      printed_total: 8,
      instruction: [
        { heading_level: null, segments: [{ kind: "text", marks: [], text: "Del 1" }] },
      ],
    }];
    const wrapper = await openDocument(document);
    await selectItemRow(wrapper, "item_001");
    await wrapper.get('[data-test="exam-workspace-item-points-input"]').setValue("4");
    expect(wrapper.find(NOTE).exists()).toBe(true);

    let releaseSave!: (response: unknown) => void;
    apiMocks.saveExamWorkspaceDocument.mockReturnValueOnce(
      new Promise((resolve) => { releaseSave = resolve as (response: unknown) => void; }),
    );
    await wrapper.get('[data-test="exam-workspace-save"]').trigger("click");
    await flushPromises();

    expect(wrapper.get(NOTE_KEEP).attributes("disabled")).toBeDefined();
    expect(wrapper.get(NOTE_USE).attributes("disabled")).toBeDefined();
    expect(wrapper.findAll(NOTE_ROW).at(0)!.attributes("disabled")).toBeDefined();

    releaseSave(buildResponse({ conversion: succeeded, version: 2 }));
    await flushPromises();
    expect(wrapper.get('[data-test="exam-workspace-save"]').attributes("disabled")).toBeUndefined();
  });
});

describe("the note never moves a list row", () => {
  function noteShape(wrapper: ViewWrapper) {
    return {
      foot: Array.from(wrapper.get(".list__foot").element.children).map((child) => `${child.tagName}.${child.classList[0]}`),
      rows: wrapper.findAll(NOTE_ROW).map((row) => row.attributes("data-test")),
    };
  }

  it("keeps every row's lines when no dismisses the note", async () => {
    const wrapper = await openDocument(mockupDocument());
    const before = ["parent_001", "item_006"].map((id) => rowShape(wrapper, id));
    const total = wrapper.get(EXAM_POINTS).element;

    await wrapper.get(NOTE_KEEP).trigger("click");
    await flushPromises();

    expect(["parent_001", "item_006"].map((id) => rowShape(wrapper, id))).toEqual(before);
    expect(wrapper.get(EXAM_POINTS).element).toBe(total);
    expect(noteShape(wrapper).foot).toEqual(["SPAN.list__total"]);
  });

  it("keeps every row's lines when yes clears the printed totals", async () => {
    const wrapper = await openDocument(mockupDocument());
    const before = ["parent_001", "item_006"].map((id) => rowShape(wrapper, id));

    await wrapper.get(NOTE_USE).trigger("click");
    await flushPromises();

    expect(["parent_001", "item_006"].map((id) => rowShape(wrapper, id))).toEqual(before);
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 67 p");
  });

  it("keeps the parent row's three lines for a part that never printed a total", async () => {
    const document = documentWithTotals(null, [2, 3]);
    document.parents = [{
      parent_id: "parent_001", item_ids: ["item_001", "item_002"], place: 0, printed_total: null, instruction: [],
    }];
    const wrapper = await openDocument(document);

    expect(rowShape(wrapper, "parent_001")).toHaveLength(3);
    expect(wrapper.get(rowLine("parent_001")).text()).toBe("5 p");
  });
});
