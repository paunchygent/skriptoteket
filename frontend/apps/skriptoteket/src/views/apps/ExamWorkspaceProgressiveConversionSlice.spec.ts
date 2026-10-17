/**
 * Progressive DOCX conversion at the real workspace view boundary (D30): the
 * first saved batch opens for editing while later batches arrive. A
 * placeholder cannot be changed until its batch is merged into the open copy,
 * each later batch replaces its own placeholders, and a reopened unfinished
 * exam keeps its placeholders locked. Completion and save conflicts live in
 * the sibling progressive specs.
 */
import { flushPromises } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import type { NativeExamItem } from "../../api/examWorkspace";
import {
  convertingNoticeShown,
  editPoints,
  expectEditable,
  FIRST,
  forceClick,
  forceInput,
  installProgressiveConversionLifecycle,
  mountTracked,
  revision,
  SECOND,
  SECOND_STATUS,
  status,
  tick,
  pointsOf,
  uploadFirstBatch,
} from "./ExamWorkspaceProgressiveConversionSlice.specSupport";
import { selectItemRow } from "./ExamWorkspaceSlice.specSupport";

const apiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
}));
vi.mock("../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../test/examCourseCatalog")).getExamCourseCatalog,
}));

installProgressiveConversionLifecycle(apiMocks);

describe("Exam workspace progressive conversion", () => {
  it("opens the first batch for editing, marks converting questions and fills them as batches arrive", async () => {
    const view = await uploadFirstBatch();

    expect(view.get('[data-test="exam-workspace-conversion-status"]').text()).toContain(
      "Konverterar provet: 1 av 3 frågor klara.",
    );
    expect(view.get('[data-test="exam-workspace-title"]').text()).toBe("NO-prov HT25");
    await selectItemRow(view, "item_001");
    expect(convertingNoticeShown(view)).toBe(false);
    expectEditable(view, true);
    await selectItemRow(view, "item_002");
    expect(convertingNoticeShown(view)).toBe(true);
    expect(view.text()).toContain("Källtext 2");
    expect(view.find('[data-test="exam-workspace-review"]').exists()).toBe(true);
    expectEditable(view, false);

    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(SECOND_STATUS);
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(SECOND);
    await tick();

    expect(view.get('[data-test="exam-workspace-conversion-status"]').text()).toContain("3 av 3 frågor klara.");
    expect(convertingNoticeShown(view)).toBe(false);
    expectEditable(view, true);
    expect(await pointsOf(view, "item_002")).toBe("22");

    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(status("succeeded", 2, ["ready", "ready", "ready"]));
    await tick();
    expect(view.find('[data-test="exam-workspace-conversion-status"]').exists()).toBe(false);
    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledTimes(2);
    expect(apiMocks.importExamWorkspaceDocument).toHaveBeenCalledTimes(1);
  });

  it("refuses every change to a converting placeholder, even one dispatched past its disabled controls", async () => {
    const view = await uploadFirstBatch();
    await selectItemRow(view, "item_002");
    await forceInput(view, "exam-workspace-item-points-input", "7");
    expect(view.find('[data-test="exam-workspace-criterion-add"]').exists()).toBe(false);
    const pressedBefore = view.get('[data-test="exam-workspace-review"]').attributes("aria-pressed");
    await forceClick(view, "exam-workspace-review");
    expect(view.get('[data-test="exam-workspace-review"]').attributes("aria-pressed")).toBe(pressedBefore);

    expect(view.get('[data-test="exam-workspace-save-state"]').text()).not.toContain("Osparat");
    // Spara stays the available primary action on a clean exam and writes nothing.
    expect(view.get('[data-test="exam-workspace-save"]').attributes("disabled")).toBeUndefined();
    await view.get('[data-test="exam-workspace-save"]').trigger("click");
    await flushPromises();
    expect(apiMocks.saveExamWorkspaceDocument).not.toHaveBeenCalled();
    await selectItemRow(view, "item_001");
    await selectItemRow(view, "item_002");
    expect((view.get('[data-test="exam-workspace-item-points-input"]').element as HTMLInputElement).value).toBe("2");
  });

  it("keeps unsaved edits of converted items and fills a placeholder from its batch when it arrives", async () => {
    const view = await uploadFirstBatch();
    await editPoints(view, "item_001", "11");
    await selectItemRow(view, "item_003");
    await forceInput(view, "exam-workspace-item-points-input", "13");
    expect(await pointsOf(view, "item_001")).toBe("11");
    expect(await pointsOf(view, "item_003")).toBe("2");

    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(SECOND_STATUS);
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(SECOND);
    await tick();

    expect(await pointsOf(view, "item_001")).toBe("11");
    expect(await pointsOf(view, "item_002")).toBe("22");
    expect(await pointsOf(view, "item_003")).toBe("23");
    expectEditable(view, true);

    apiMocks.saveExamWorkspaceDocument.mockResolvedValueOnce(revision(3, SECOND.document.items, SECOND_STATUS));
    await view.get('[data-test="exam-workspace-save"]').trigger("click");
    await flushPromises();
    const [, params] = apiMocks.saveExamWorkspaceDocument.mock.calls[0];
    expect(params.expectedRevision).toBe(2);
    expect(params.document.items.map((item: NativeExamItem) => item.points)).toEqual([11, 22, 23]);
  });

  it("keeps the placeholders locked when the unfinished exam is opened from its address, until their batch arrives", async () => {
    apiMocks.getExamWorkspaceConversionStatus.mockReset();
    apiMocks.getExamWorkspaceDocument.mockReset();
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(FIRST);
    const mounted = await mountTracked({ document: "lineage-1" });
    const view = mounted.wrapper;

    await selectItemRow(view, "item_002");
    expect(convertingNoticeShown(view)).toBe(true);
    expectEditable(view, false);
    await forceInput(view, "exam-workspace-item-points-input", "7");
    expect(view.get('[data-test="exam-workspace-save-state"]').text()).not.toContain("Osparat");
    await selectItemRow(view, "item_001");
    expectEditable(view, true);

    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(SECOND_STATUS);
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(SECOND);
    await tick();

    expect(apiMocks.getExamWorkspaceConversionStatus).toHaveBeenCalledWith("job-1");
    expect(await pointsOf(view, "item_002")).toBe("22");
    expect(convertingNoticeShown(view)).toBe(false);
    expectEditable(view, true);
    expect(apiMocks.importExamWorkspaceDocument).not.toHaveBeenCalled();
  });

  it("opens a finished import without a lock and without following its conversion", async () => {
    apiMocks.getExamWorkspaceConversionStatus.mockReset();
    apiMocks.getExamWorkspaceDocument.mockReset();
    const done = status("succeeded", 2, ["ready", "ready", "ready"]);
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(revision(2, SECOND.document.items, done));
    const mounted = await mountTracked({ document: "lineage-1" });

    await selectItemRow(mounted.wrapper, "item_002");
    expect(convertingNoticeShown(mounted.wrapper)).toBe(false);
    expectEditable(mounted.wrapper, true);
    await tick();
    expect(apiMocks.getExamWorkspaceConversionStatus).not.toHaveBeenCalled();
    expect(mounted.wrapper.find('[data-test="exam-workspace-conversion-status"]').exists()).toBe(false);
  });
});
