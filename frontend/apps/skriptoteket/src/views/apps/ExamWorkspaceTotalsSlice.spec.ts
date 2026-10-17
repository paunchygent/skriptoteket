/** Printed totals are advisory, live signals, never an export gate. */
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
import { examWorkspaceTotalSignal } from "./exam-workspace/examWorkspaceTotals";

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

function documentWithTotals(printed: number | null, points: (number | null)[]): NativeExamDocument {
  return {
    ...buildDocument(),
    header: { course_hint: "Svenska 2", printed_total: printed },
    items: points.map((value, index) => ({ ...buildFreeTextItem(index + 1), points: value })),
  };
}

async function openDocument(document: NativeExamDocument) {
  apiMocks.getExamWorkspaceDocument.mockResolvedValue({
    ...buildResponse({ version: 1, conversion: succeeded }),
    document,
  });
  const { wrapper } = await mountExamWorkspace();
  mounted.push(wrapper);
  await importFixtureDocument(wrapper);
  return wrapper;
}

beforeEach(() => {
  for (const mock of Object.values(apiMocks)) mock.mockReset();
  downloadMocks.triggerBrowserDownload.mockReset();
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [] });
  apiMocks.getExamWorkspaceConversionStatus.mockResolvedValue(succeeded);
  apiMocks.importExamWorkspaceDocument.mockResolvedValue({ ...succeeded, state: "queued", document_revision: null });
  apiMocks.getExamWorkspaceExportChecklist.mockResolvedValue({ entries: [] });
});
afterEach(() => {
  for (const wrapper of mounted.splice(0)) wrapper.unmount();
});

describe("workspace printed exam totals", () => {
  it.each([
    { printed: null, points: [2, 3] },
    { printed: 5, points: [2, 3] },
    { printed: 7.5, points: [2.5, 5] },
    { printed: 0, points: [null, 0] },
  ])("does not signal an absent or matching total ($printed)", async ({ printed, points }) => {
    const wrapper = await openDocument(documentWithTotals(printed, points));
    expect(wrapper.find('[data-test="exam-workspace-total-signal"]').exists()).toBe(false);
  });

  it("shows both decimal totals and still downloads the saved export", async () => {
    const wrapper = await openDocument(documentWithTotals(7.5, [2.5, 4, null]));
    expect(wrapper.get('[data-test="exam-workspace-total-signal"]').text()).toBe(
      "Tryckt totalsumma 7,5 p, frågorna ger 6,5 p",
    );
    apiMocks.downloadExamWorkspaceExport.mockResolvedValue({
      blob: new Blob(["export"]), contentType: "application/zip", filename: "prov.zip",
    });
    const button = wrapper.get('[data-test="exam-workspace-export-qti"]');
    expect(button.attributes("disabled")).toBeUndefined();
    await button.trigger("click");
    await flushPromises();
    expect(apiMocks.downloadExamWorkspaceExport).toHaveBeenCalledWith("lineage-1", "qti", 1);
    expect(downloadMocks.triggerBrowserDownload).toHaveBeenCalledTimes(1);
  });

  it("recomputes the exam and parent signals on a point edit without a save or reload", async () => {
    const document = documentWithTotals(7.5, [2.5, 5]);
    document.parents = [{
      parent_id: "parent_001", item_ids: ["item_001", "item_002"],
      printed_total: 7.5, instruction: [],
    }];
    const wrapper = await openDocument(document);
    expect(wrapper.find('[data-test="exam-workspace-total-signal"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-parent-total-signal"]').exists()).toBe(false);
    await selectItemRow(wrapper, "item_001");
    await wrapper.get('[data-test="exam-workspace-item-points-input"]').setValue("3.5");
    expect(wrapper.get('[data-test="exam-workspace-total-signal"]').text()).toBe(
      "Tryckt totalsumma 7,5 p, frågorna ger 8,5 p",
    );
    expect(wrapper.get('[data-test="exam-workspace-parent-parent_001"]').text()).toContain(
      "Tryckt delsumma 7,5 p, frågorna ger 8,5 p",
    );
    await wrapper.get('[data-test="exam-workspace-item-points-input"]').setValue("2.5");
    expect(wrapper.find('[data-test="exam-workspace-total-signal"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-parent-total-signal"]').exists()).toBe(false);
    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(apiMocks.saveExamWorkspaceDocument).not.toHaveBeenCalled();
  });

  it("does not show a parent signal without a printed part total", async () => {
    const document = documentWithTotals(null, [2, 3]);
    document.parents = [{
      parent_id: "parent_001", item_ids: ["item_001", "item_002"],
      printed_total: null, instruction: [],
    }];
    const wrapper = await openDocument(document);
    expect(wrapper.find('[data-test="exam-workspace-parent-parent_001"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-parent-total-signal"]').exists()).toBe(false);
  });

  it("places a part mismatch only on its own parent, with adjacent parents in reverse metadata order", async () => {
    const document = documentWithTotals(null, [2, 3, 1, 4]);
    document.parents = [
      { parent_id: "parent_002", item_ids: ["item_003", "item_004"], printed_total: 8, instruction: [] },
      { parent_id: "parent_001", item_ids: ["item_001", "item_002"], printed_total: 5, instruction: [] },
    ];
    const wrapper = await openDocument(document);
    const first = wrapper.get('[data-test="exam-workspace-parent-parent_001"]');
    const second = wrapper.get('[data-test="exam-workspace-parent-parent_002"]');
    expect(first.find('[data-test="exam-workspace-parent-total-signal"]').exists()).toBe(false);
    expect(second.get('[data-test="exam-workspace-parent-total-signal"]').text()).toBe(
      "Tryckt delsumma 8 p, frågorna ger 5 p",
    );
    expect(wrapper.findAll('[data-test="exam-workspace-parent-total-signal"]')).toHaveLength(1);
  });
});

describe("total comparison edge cases", () => {
  it("treats a printed zero as a real total, not a missing value", () => {
    expect(examWorkspaceTotalSignal(0, [buildFreeTextItem(1)])).toBe(
      "Tryckt totalsumma 0 p, frågorna ger 2 p",
    );
  });

  it("keeps a sub-hundredth difference visible instead of showing identical numbers", () => {
    const item = { ...buildFreeTextItem(1), points: 7.502 };
    expect(examWorkspaceTotalSignal(7.501, [item])).toBe(
      "Tryckt totalsumma 7,501 p, frågorna ger 7,502 p",
    );
  });

  it("does not invent a mismatch from binary floating-point addition", () => {
    const items = [0.1, 0.2].map((points, index) => ({ ...buildFreeTextItem(index + 1), points }));
    expect(examWorkspaceTotalSignal(0.3, items)).toBeNull();
    expect(examWorkspaceTotalSignal(0.4, items)).toBe("Tryckt totalsumma 0,4 p, frågorna ger 0,3 p");
  });
});
