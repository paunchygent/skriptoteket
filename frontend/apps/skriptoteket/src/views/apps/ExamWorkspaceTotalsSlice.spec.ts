/**
 * The printed-total mismatch lines are information, never a save or export
 * gate (user ruling 2026-10-17): the footer reads "Totalt N p" with one
 * neutral line below it per printed total that differs from its questions'
 * sum. Each line is followed by two glyph-only buttons: confirm ("Godta
 * frågornas summa, {sum} p", clears that line's own level) and continue
 * ("Visa frågorna", jumps to the first question carrying the difference).
 * Every Använd action is gone.
 */
import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  ExamWorkspaceConversionStatus,
  NativeExamDocument,
  NativeExamItem,
  storeExamWorkspaceUndoStep,
} from "../../api/examWorkspace";
import {
  buildDocument,
  buildFreeTextItem,
  buildResponse,
  importFixtureDocument,
  mountExamWorkspace,
  resetSliceApiMocks,
  selectItemRow,
  type ViewWrapper,
} from "./ExamWorkspaceSlice.specSupport";
import { HISTORY_BASELINE_STEP_ID } from "./ExamWorkspaceHistory.specSupport";
import { examWorkspaceFormatPoints, examWorkspacePrintedDifference } from "./exam-workspace/examWorkspaceTotals";
import type { ExamWorkspaceLayout } from "./exam-workspace/useExamWorkspaceLayout";

const apiMocks = vi.hoisted(() => ({
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn<typeof storeExamWorkspaceUndoStep>(),
  importExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
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
let history: ReturnType<typeof resetSliceApiMocks>;
const LINE = '[data-test="exam-workspace-printed-total-line"]';
const CHANGE = '[data-test="exam-workspace-printed-total-change"]';
const SHOW = '[data-test="exam-workspace-printed-total-show"]';
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
    header: { course_hint: "Svenska 2", printed_total: printed, tags: [] },
    items: points.map((value, index) => itemWithTotals(index + 1, value, sources?.[index] ?? null)),
  };
}

/**
 * The mockup case: the exam prints 70 p over questions summing to 66 p, with
 * a differing part (list number 3, children 3a/3b), earlier and later changed
 * questions (labels 1 and 5) and a question missing its points (label 8).
 */
function mockupDocument(): NativeExamDocument {
  const document = documentWithTotals(
    70,
    [10, 9, 9, 10, 8, 10, 5, 5, null],
    [12, 9, 10, 10, 8, 12, 5, 5, 4],
  );
  document.parents = [{
    parent_id: "parent_001",
    item_ids: ["item_003", "item_004"],
    place: 2,
    printed_total: 22,
    instruction: [
      { heading_level: null, segments: [{ kind: "text", marks: [], text: "Del 3: Satslösning" }] },
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

/** The element tags and classes of a row's lines, top to bottom: what must not change when a line is answered. */
function rowShape(wrapper: ViewWrapper, id: string): string[] {
  const body = wrapper.get(`[data-test="exam-workspace-row-${id}"]`).element.querySelector(".row__body");
  return Array.from(body?.children ?? []).map((line) => `${line.tagName}.${line.className}`);
}

/** The footer lines' aria-labels in order, whitespace-normalised: each names its difference. */
function lineLabels(wrapper: ViewWrapper): string[] {
  return wrapper.findAll(LINE).map((line) => (line.attributes("aria-label") ?? "").replace(/\s+/g, " ").trim());
}

async function undo(wrapper: ViewWrapper) {
  await wrapper.get('[data-test="exam-workspace-undo"]').trigger("click");
  await flushPromises();
}

beforeEach(() => {
  history = resetSliceApiMocks(apiMocks);
  for (const mock of Object.values(exportApiMocks)) mock.mockReset();
  downloadMocks.triggerBrowserDownload.mockReset();
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [], ordering: "course" });
  apiMocks.getExamWorkspaceConversionStatus.mockResolvedValue(succeeded);
  apiMocks.importExamWorkspaceDocument.mockResolvedValue({ ...succeeded, state: "queued", document_revision: null });
  exportApiMocks.getExamWorkspaceExportChecklist.mockResolvedValue({ entries: [] });
});
afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
  globalThis.document.body.replaceChildren();
});

describe("workspace printed-total lines", () => {
  it.each([
    { printed: null, points: [2, 3] },
    { printed: 5, points: [2, 3] },
    { printed: 7.5, points: [2.5, 5] },
    { printed: 0, points: [null, 0] },
    { printed: 0.3, points: [0.1, 0.2] },
  ])("shows no line for an absent or matching total ($printed)", async ({ printed, points }) => {
    const wrapper = await openDocument(documentWithTotals(printed, points));
    expect(wrapper.find(LINE).exists()).toBe(false);
    expect(wrapper.get(EXAM_POINTS).text()).not.toContain("provtexten");
    expect(wrapper.find(SHOW).exists()).toBe(false);
  });

  it("states the exam difference with exact numbers and no note element", async () => {
    const wrapper = await openDocument(mockupDocument());
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 66 p");
    expect(lineLabels(wrapper)[0]).toBe("Provtexten säger 70 p, frågorna ger 66 p.");
    expect(wrapper.find('[data-test="exam-workspace-points-note"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-points-keep"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-points-use-computed"]').exists()).toBe(false);
  });

  it("lists the exam line first, then one line per differing part in document order", async () => {
    const document = documentWithTotals(
      70,
      [10, 9, 9, 10, 8, 10, 5, 5, null],
      [12, 9, 10, 10, 8, 12, 5, 5, 4],
    );
    document.parents = [
      {
        parent_id: "parent_001", item_ids: ["item_001", "item_002"], place: 0,
        printed_total: 22, instruction: [],
      },
      {
        parent_id: "parent_002", item_ids: ["item_003", "item_004"], place: 2,
        printed_total: 12,
        instruction: [
          { heading_level: null, segments: [{ kind: "text", marks: [], text: "Del 2" }] },
        ],
      },
    ];
    const wrapper = await openDocument(document);
    expect(lineLabels(wrapper)).toEqual([
      "Provtexten säger 70 p, frågorna ger 66 p.",
      "Del 1 i provtexten säger 22 p, frågorna ger 19 p.",
      "Del 2 i provtexten säger 12 p, frågorna ger 19 p.",
    ]);
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
    expect(lineLabels(wrapper)).toEqual(["Del 1 i provtexten säger 8 p, frågorna ger 5 p."]);
  });

  it("states a third-decimal difference instead of two equal numbers", async () => {
    const wrapper = await openDocument(documentWithTotals(12.001, [12], [12.001]));
    expect(lineLabels(wrapper)).toEqual(["Provtexten säger 12,001 p, frågorna ger 12 p."]);
    expect(wrapper.find(CHANGE).attributes("aria-label")).toBe("Godta frågornas summa, 12 p");
  });

  it("states both decimal totals in the footer and still exports", async () => {
    const wrapper = await openDocument(documentWithTotals(7.5, [2.5, 4], [2.5, 4]));
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 6,5 p");
    expect(lineLabels(wrapper)).toEqual(["Provtexten säger 7,5 p, frågorna ger 6,5 p."]);
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

  it("recomputes the lines on a point edit without a save or reload", async () => {
    const wrapper = await openDocument(mockupDocument());

    await selectItemRow(wrapper, "item_006");
    await wrapper.get('[data-test="exam-workspace-item-points-input"]').setValue("9");
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 65 p");
    expect(lineLabels(wrapper)).toContain("Provtexten säger 70 p, frågorna ger 65 p.");

    await wrapper.get('[data-test="exam-workspace-item-points-input"]').setValue("10");
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 66 p");
    expect(wrapper.findAll(LINE)).toHaveLength(2);
    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(apiMocks.storeExamWorkspaceUndoStep).not.toHaveBeenCalled();
  });

  it("never disables Spara som for a mismatch", async () => {
    const wrapper = await openDocument(documentWithTotals(10, [2, 3]));
    await selectItemRow(wrapper, "item_001");
    await wrapper.get('[data-test="exam-workspace-item-points-input"]').setValue("4");
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 7 p");
    expect(wrapper.find(LINE).exists()).toBe(true);
    expect(wrapper.get('[data-test="exam-workspace-save-as-command"]').attributes("disabled")).toBeUndefined();
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
    // The difference is said once, on the line.
    expect(wrapper.findAll(LINE)).toHaveLength(1);
    expect(lineLabels(wrapper)[0]).toContain("provtexten säger 8 p, frågorna ger 5 p");
  });

  it("says an exam total difference once, on the line, with a plain footer", async () => {
    const wrapper = await openDocument(documentWithTotals(9, [2, 3]));
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 5 p");
    expect(lineLabels(wrapper)).toEqual(["Provtexten säger 9 p, frågorna ger 5 p."]);
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

describe("answering a mismatch line", () => {
  it("change on the exam line clears only the header in one undo step, and undo restores the line", async () => {
    const wrapper = await openDocument(mockupDocument());

    await wrapper.findAll(CHANGE).at(0)!.trigger("click");
    await flushPromises();

    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(1);
    const stored = apiMocks.storeExamWorkspaceUndoStep.mock.calls.at(-1)![1].document;
    expect(stored.header.printed_total).toBeNull();
    expect(stored.parents.map((parent) => parent.printed_total)).toEqual([22]);
    expect(stored.items.map((item) => item.points)).toEqual([10, 9, 9, 10, 8, 10, 5, 5, null]);

    expect(lineLabels(wrapper)).toEqual(["Del 3 i provtexten säger 22 p, frågorna ger 19 p."]);

    await undo(wrapper);
    expect(lineLabels(wrapper)).toHaveLength(2);
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 66 p");
  });

  it("change on a part line clears only that part, and the exam line stays", async () => {
    const wrapper = await openDocument(mockupDocument());

    await wrapper.findAll(CHANGE).at(1)!.trigger("click");
    await flushPromises();

    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(1);
    const stored = apiMocks.storeExamWorkspaceUndoStep.mock.calls.at(-1)![1].document;
    expect(stored.header.printed_total).toBe(70);
    expect(stored.parents.map((parent) => parent.printed_total)).toEqual([null]);

    expect(lineLabels(wrapper)).toEqual(["Provtexten säger 70 p, frågorna ger 66 p."]);

    await undo(wrapper);
    expect(lineLabels(wrapper)).toHaveLength(2);
  });

  it("names the change in the tooltip and aria-label only, with no visible text", async () => {
    const wrapper = await openDocument(mockupDocument());
    const change = wrapper.findAll(CHANGE).at(0)!;

    expect(change.text()).toBe("");
    expect(change.attributes("aria-label")).toBe("Godta frågornas summa, 66 p");
    expect(change.attributes("title")).toBe("Godta frågornas summa, 66 p");
  });

  it("show selects the first differing question of the line's scope", async () => {
    const wrapper = await openDocument(mockupDocument());

    await wrapper.findAll(SHOW).at(0)!.trigger("click");
    expect(wrapper.get('[data-test="exam-workspace-row-item_001"]').attributes("aria-selected")).toBe("true");

    await wrapper.findAll(SHOW).at(1)!.trigger("click");
    expect(wrapper.get('[data-test="exam-workspace-row-item_003"]').attributes("aria-selected")).toBe("true");
  });

  it("falls back to the first differing part for the exam line, and hides show with no target", async () => {
    const fallback = documentWithTotals(70, [30, 37], [30, 37]);
    fallback.parents = [{
      parent_id: "parent_001", item_ids: ["item_001"], place: 0,
      printed_total: 31, instruction: [],
    }];
    const wrapper = await openDocument(fallback);
    expect(lineLabels(wrapper)).toEqual([
      "Provtexten säger 70 p, frågorna ger 67 p.",
      "Del 1 i provtexten säger 31 p, frågorna ger 30 p.",
    ]);

    await wrapper.findAll(SHOW).at(0)!.trigger("click");
    expect(wrapper.get('[data-test="exam-workspace-row-parent_001"]').attributes("aria-selected")).toBe("true");

    const targetless = await openDocument(documentWithTotals(70, [30, 37], [30, 37]));
    expect(targetless.findAll(LINE)).toHaveLength(1);
    expect(targetless.findAll(SHOW)).toHaveLength(0);
    expect(targetless.findAll(CHANGE)).toHaveLength(1);
  });

  it("disables the lines' buttons while the workspace is busy", async () => {
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
    expect(wrapper.find(LINE).exists()).toBe(true);

    window.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, cancelable: true, ctrlKey: true, key: "s" }));
    await flushPromises();

    const inner = apiMocks.moveExamWorkspaceHistoryPosition.getMockImplementation();
    if (!inner) {
      throw new Error("expected the history move double");
    }
    let releaseMove!: () => void;
    apiMocks.moveExamWorkspaceHistoryPosition.mockImplementationOnce(
      (...args: unknown[]) =>
        new Promise((resolve) => {
          releaseMove = () => resolve((inner as (...innerArgs: unknown[]) => unknown)(...args));
        }),
    );
    await wrapper.get('[data-test="exam-workspace-undo"]').trigger("click");
    await flushPromises();

    expect(wrapper.findAll(CHANGE).at(0)!.attributes("disabled")).toBeDefined();
    expect(wrapper.findAll(SHOW).at(0)!.attributes("disabled")).toBeDefined();

    releaseMove();
    await flushPromises();
    expect(wrapper.findAll(CHANGE).at(0)!.attributes("disabled")).toBeUndefined();
    expect(wrapper.get('[data-test="exam-workspace-save-as-command"]').attributes("disabled")).toBeUndefined();
  });
});

describe("the lines never move a list row", () => {
  function linesShape(wrapper: ViewWrapper) {
    return {
      foot: Array.from(wrapper.get(".list__foot").element.children).map((child) => `${child.tagName}.${child.classList[0]}`),
      lines: wrapper.findAll(LINE).map((line) => line.attributes("data-test")),
    };
  }

  it("keeps every row's lines when change clears the last line", async () => {
    const wrapper = await openDocument(documentWithTotals(9, [2, 3]));
    const before = ["item_001", "item_002"].map((id) => rowShape(wrapper, id));
    const total = wrapper.get(EXAM_POINTS).element;

    await wrapper.find(CHANGE).trigger("click");
    await flushPromises();

    expect(["item_001", "item_002"].map((id) => rowShape(wrapper, id))).toEqual(before);
    expect(wrapper.get(EXAM_POINTS).element).toBe(total);
    expect(linesShape(wrapper).foot).toEqual(["SPAN.list__total"]);
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 5 p");
  });

  it("keeps every row's lines when change clears a part line", async () => {
    const wrapper = await openDocument(mockupDocument());
    const before = ["parent_001", "item_003"].map((id) => rowShape(wrapper, id));

    await wrapper.findAll(CHANGE).at(1)!.trigger("click");
    await flushPromises();

    expect(["parent_001", "item_003"].map((id) => rowShape(wrapper, id))).toEqual(before);
    expect(wrapper.get(EXAM_POINTS).text()).toBe("Totalt 66 p");
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
