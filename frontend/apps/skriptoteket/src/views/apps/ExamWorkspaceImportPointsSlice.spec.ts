/**
 * Right after an import the question list warns about questions whose
 * points differ from the points the source printed for them
 * (TASK-SKRIPT-40-04-23, P1-P5).
 *
 * Expected behavior:
 *   When a conversion started in this workspace finishes and its exam opens,
 *   one floating line reads "{N} frågor avviker från provtexten" (singular
 *   "1 fråga …") whenever a question's points differ from its
 *   `source_points`, also when the printed totals add up or the source
 *   prints no total. Those rows show their points amber, the selected one
 *   shows "Provtexten: {n} p" next to Poäng, Visa frågorna steps through them
 *   one at a time and Avfärda clears the line and every mark at once. Opening
 *   another exam, coming back to it or reloading never shows it again. The
 *   40-04-10 exam and part total lines read exactly as before.
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
  unmountExamWorkspace,
  type ViewWrapper,
} from "./ExamWorkspaceSlice.specSupport";
import { HISTORY_BASELINE_STEP_ID } from "./ExamWorkspaceHistory.specSupport";

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

const succeeded: ExamWorkspaceConversionStatus = {
  job_id: "job-1", lineage_id: "lineage-1", state: "succeeded", error_message: null, summary: null,
  document_revision: 1, phase: null, phase_started_at: null, questions_total: 0, questions_done: 0, questions_received: 0, units: [],
};
let history: ReturnType<typeof resetSliceApiMocks>;
const IMPORT_LINE = '[data-test="exam-workspace-import-points-line"]';
const IMPORT_SHOW = '[data-test="exam-workspace-import-points-show"]';
const IMPORT_DISMISS = '[data-test="exam-workspace-import-points-dismiss"]';
const PRINTED_LINE = '[data-test="exam-workspace-printed-total-line"]';
const ROW_MARK = '[data-test="exam-workspace-row-points-differ"]';
const SOURCE_HINT = '[data-test="exam-workspace-points-source"]';
const LINES = '[data-test="exam-workspace-printed-total-lines"]';

function question(sequence: number, points: number | null, source: number | null): NativeExamItem {
  return { ...buildFreeTextItem(sequence), points, source_points: source };
}

/** A question whose own lines printed two different values: no single source value, both in print order. */
function conflictQuestion(sequence: number, points: number | null, conflicting: number[]): NativeExamItem {
  return { ...question(sequence, points, null), conflicting_source_points: conflicting };
}

function examOf(printed: number | null, points: (number | null)[], sources: (number | null)[]): NativeExamDocument {
  return {
    ...buildDocument(),
    header: { course_hint: "Svenska 2", printed_total: printed, tags: [] },
    items: points.map((value, index) => question(index + 1, value, sources[index] ?? null)),
  };
}

function serve(lineageId: string, document: NativeExamDocument): void {
  const base = buildResponse({ version: 1, conversion: lineageId === "lineage-1" ? succeeded : null });
  responses.set(lineageId, {
    ...base,
    summary: { ...base.summary, lineage_id: lineageId },
    document,
    saved_document: document,
  });
}

const responses = new Map<string, unknown>();

async function importExam(document: NativeExamDocument): Promise<{ wrapper: ViewWrapper; router: Awaited<ReturnType<typeof mountExamWorkspace>>["router"] }> {
  serve("lineage-1", document);
  history.documents.set(HISTORY_BASELINE_STEP_ID, document);
  const slot = globalThis.document.createElement("div");
  slot.id = "app-topbar-page-slot";
  globalThis.document.body.append(slot);
  const host = globalThis.document.createElement("div");
  globalThis.document.body.append(host);
  const { router, wrapper } = await mountExamWorkspace({}, "desktop", host);
  await importFixtureDocument(wrapper);
  return { router, wrapper };
}

function lineText(wrapper: ViewWrapper): string | null {
  const line = wrapper.find(IMPORT_LINE);
  return line.exists() ? (line.attributes("aria-label") ?? "").replace(/\s+/g, " ").trim() : null;
}

function selectedRowId(wrapper: ViewWrapper): string | null {
  const row = wrapper.find('[role="row"][aria-selected="true"]');
  return row.exists() ? (row.attributes("data-entry-id") ?? null) : null;
}

beforeEach(() => {
  history = resetSliceApiMocks(apiMocks);
  responses.clear();
  for (const mock of Object.values(exportApiMocks)) mock.mockReset();
  apiMocks.getExamWorkspaceDocument.mockImplementation(async (lineageId: string) => responses.get(lineageId));
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [], ordering: "course" });
  apiMocks.getExamWorkspaceConversionStatus.mockResolvedValue(succeeded);
  apiMocks.importExamWorkspaceDocument.mockResolvedValue({ ...succeeded, state: "queued", document_revision: null });
  exportApiMocks.getExamWorkspaceExportChecklist.mockResolvedValue({ entries: [] });
});
afterEach(() => {
  unmountExamWorkspace();
});

describe("the import-time points line", () => {
  it("counts the differing questions after an import whose totals add up", async () => {
    // 5 + 3 + 2 = 10 = printed total, yet questions 1 and 3 differ from the source.
    const { wrapper } = await importExam(examOf(10, [5, 3, 2], [4, 3, 3]));
    expect(lineText(wrapper)).toBe("2 frågor avviker från provtexten");
    expect(wrapper.find(PRINTED_LINE).exists()).toBe(false);
  });

  it("reads in the singular, also when the source prints no total", async () => {
    const { wrapper } = await importExam(examOf(null, [5, 3], [4, null]));
    expect(lineText(wrapper)).toBe("1 fråga avviker från provtexten");
  });

  it("shows no line when no question differs", async () => {
    const { wrapper } = await importExam(examOf(null, [4, 3], [4, null]));
    expect(wrapper.find(IMPORT_LINE).exists()).toBe(false);
    expect(wrapper.find(ROW_MARK).exists()).toBe(false);
  });

  it("marks the differing rows amber and shows the source's value next to Poäng", async () => {
    const { wrapper } = await importExam(examOf(null, [5, 3, 2], [4, 3, 3]));
    const marked = wrapper.findAll(ROW_MARK);
    expect(marked).toHaveLength(2);
    expect(marked.every((mark) => mark.classes().includes("xw-warn"))).toBe(true);
    expect(wrapper.get('[data-test="exam-workspace-row-item_001"]').find(ROW_MARK).exists()).toBe(true);
    expect(wrapper.get('[data-test="exam-workspace-row-item_002"]').find(ROW_MARK).exists()).toBe(false);

    await selectItemRow(wrapper, "item_001");
    await flushPromises();
    expect(wrapper.get(SOURCE_HINT).text()).toBe("Provtexten: 4 p");
    await selectItemRow(wrapper, "item_002");
    await flushPromises();
    expect(wrapper.find(SOURCE_HINT).exists()).toBe(false);
  });

  it("Visa frågorna steps through the differing questions one at a time", async () => {
    const { wrapper } = await importExam(examOf(null, [5, 3, 2], [4, 3, 3]));
    await selectItemRow(wrapper, "item_002");
    await flushPromises();
    const steps: (string | null)[] = [];
    for (let click = 0; click < 3; click += 1) {
      await wrapper.get(IMPORT_SHOW).trigger("click");
      await flushPromises();
      steps.push(selectedRowId(wrapper));
    }
    expect(steps).toEqual(["item_001", "item_003", "item_001"]);
  });

  it("Avfärda clears the line, every row mark and the Poäng hint in one click", async () => {
    const { wrapper } = await importExam(examOf(null, [5, 3, 2], [4, 3, 3]));
    await selectItemRow(wrapper, "item_001");
    await flushPromises();
    expect(wrapper.find(SOURCE_HINT).exists()).toBe(true);

    await wrapper.get(IMPORT_DISMISS).trigger("click");
    await flushPromises();
    expect(wrapper.find(IMPORT_LINE).exists()).toBe(false);
    expect(wrapper.find(ROW_MARK).exists()).toBe(false);
    expect(wrapper.find(SOURCE_HINT).exists()).toBe(false);
  });

  it("never shows again after opening another exam and coming back", async () => {
    const document = examOf(null, [5, 3], [4, 3]);
    const { router, wrapper } = await importExam(document);
    expect(lineText(wrapper)).toBe("1 fråga avviker från provtexten");

    serve("lineage-2", examOf(null, [6], [5]));
    await router.push({ query: { document: "lineage-2" } });
    await flushPromises();
    expect(wrapper.find(IMPORT_LINE).exists()).toBe(false);

    await router.push({ query: { document: "lineage-1" } });
    await flushPromises();
    expect(wrapper.find('[data-test="exam-workspace-row-item_001"]').exists()).toBe(true);
    expect(wrapper.find(IMPORT_LINE).exists()).toBe(false);
    expect(wrapper.find(ROW_MARK).exists()).toBe(false);
  });

  it("never shows when the exam opens after a reload", async () => {
    const document = examOf(null, [5, 3], [4, 3]);
    serve("lineage-1", document);
    history.documents.set(HISTORY_BASELINE_STEP_ID, document);
    const { wrapper } = await mountExamWorkspace({ document: "lineage-1" });
    await flushPromises();
    expect(wrapper.find('[data-test="exam-workspace-row-item_001"]').exists()).toBe(true);
    expect(wrapper.find(IMPORT_LINE).exists()).toBe(false);
    expect(wrapper.find(ROW_MARK).exists()).toBe(false);
  });

  it("counts a two-value question in the line, marks its row amber and names both values (TASK-SKRIPT-40-04-23 P8)", async () => {
    const document = examOf(null, [5, 3], [null, null]);
    document.items = [conflictQuestion(1, 5, [4, 5]), question(2, 3, null)];
    const { wrapper } = await importExam(document);
    expect(lineText(wrapper)).toBe("1 fråga avviker från provtexten");
    const marked = wrapper.findAll(ROW_MARK);
    expect(marked).toHaveLength(1);
    expect(wrapper.get('[data-test="exam-workspace-row-item_001"]').find(ROW_MARK).exists()).toBe(true);
    expect(wrapper.get('[data-test="exam-workspace-row-item_002"]').find(ROW_MARK).exists()).toBe(false);

    await selectItemRow(wrapper, "item_001");
    await flushPromises();
    expect(wrapper.get(SOURCE_HINT).text()).toBe("Provtexten: 4 p och 5 p");
  });

  it("leaves the exam and part total lines as they were and sits first in the floating stack", async () => {
    const document = examOf(12, [5, 3, 2], [4, 3, 3]);
    document.parents = [{
      parent_id: "parent_001", item_ids: ["item_002", "item_003"], place: 1, printed_total: 6,
      instruction: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Del 2" }] }],
    }];
    const { wrapper } = await importExam(document);
    const printed = wrapper.findAll(PRINTED_LINE).map((line) => line.attributes("aria-label"));
    expect(printed).toEqual([
      "Provtexten säger 12 p, frågorna ger 10 p.",
      "Del 2 i provtexten säger 6 p, frågorna ger 5 p.",
    ]);
    expect(wrapper.findAll('[data-test="exam-workspace-printed-total-change"]')).toHaveLength(2);
    const stack = wrapper.get(LINES).element.children;
    expect(stack[0]?.getAttribute("data-test")).toBe("exam-workspace-import-points-line");
    expect(stack).toHaveLength(3);
  });
});
