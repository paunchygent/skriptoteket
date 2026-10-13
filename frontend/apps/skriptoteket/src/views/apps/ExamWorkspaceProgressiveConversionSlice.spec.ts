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
  editTitle,
  expectEditable,
  FIRST,
  forceInput,
  installProgressiveConversionLifecycle,
  mountTracked,
  revision,
  SECOND,
  SECOND_STATUS,
  status,
  tick,
  titleOf,
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
vi.mock("../../api/examWorkspace", () => apiMocks);

installProgressiveConversionLifecycle(apiMocks);

describe("Exam workspace progressive conversion", () => {
  it("opens the first batch for editing, marks converting questions and fills them as batches arrive", async () => {
    const view = await uploadFirstBatch();

    expect(view.get('[data-test="exam-workspace-conversion-status"]').text()).toContain(
      "Konverterar provet: 1 av 3 frågor klara.",
    );
    expect(view.get('[data-test="exam-workspace-summary-title"]').text()).toBe("NO-prov HT25");
    await selectItemRow(view, "item_001");
    expect(convertingNoticeShown(view)).toBe(false);
    expectEditable(view, true);
    await selectItemRow(view, "item_002");
    expect(convertingNoticeShown(view)).toBe(true);
    expect(view.text()).toContain("Källtext 2");
    expect(view.find('[data-test="exam-workspace-mark-reviewed"]').exists()).toBe(true);
    expectEditable(view, false);

    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(SECOND_STATUS);
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(SECOND);
    await tick();

    expect(view.get('[data-test="exam-workspace-conversion-status"]').text()).toContain("3 av 3 frågor klara.");
    expect(convertingNoticeShown(view)).toBe(false);
    expectEditable(view, true);
    expect(await titleOf(view, "item_002")).toBe("Konverterad 2");

    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(status("succeeded", 2, ["ready", "ready", "ready"]));
    await tick();
    expect(view.find('[data-test="exam-workspace-conversion-status"]').exists()).toBe(false);
    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledTimes(2);
    expect(apiMocks.importExamWorkspaceDocument).toHaveBeenCalledTimes(1);
  });

  it("refuses every change to a converting placeholder, even one dispatched past its disabled controls", async () => {
    const view = await uploadFirstBatch();
    await selectItemRow(view, "item_002");
    await forceInput(view, "exam-workspace-item-title-input", "Lärarens rubrik två");
    await forceInput(view, "exam-workspace-item-points-input", "7");
    await forceInput(view, "exam-workspace-marking-guide-input", "Lärarens bedömningsstöd");

    expect(view.find('[data-test="exam-workspace-dirty-pill"]').exists()).toBe(false);
    expect(view.get('[data-test="exam-workspace-save"]').attributes("disabled")).toBe("");
    await selectItemRow(view, "item_001");
    await selectItemRow(view, "item_002");
    expect((view.get('[data-test="exam-workspace-item-title-input"]').element as HTMLInputElement).value).toBe("Fråga 2");
    expect((view.get('[data-test="exam-workspace-item-points-input"]').element as HTMLInputElement).value).toBe("2");
  });

  it("keeps unsaved edits of converted items and fills a placeholder from its batch when it arrives", async () => {
    const view = await uploadFirstBatch();
    await editTitle(view, "item_001", "Lärarens rubrik ett");
    await selectItemRow(view, "item_003");
    await forceInput(view, "exam-workspace-item-title-input", "Lärarens rubrik tre");
    expect(await titleOf(view, "item_001")).toBe("Lärarens rubrik ett");
    expect(await titleOf(view, "item_003")).toBe("Fråga 3");

    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(SECOND_STATUS);
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(SECOND);
    await tick();

    expect(await titleOf(view, "item_001")).toBe("Lärarens rubrik ett");
    expect(await titleOf(view, "item_002")).toBe("Konverterad 2");
    expect(await titleOf(view, "item_003")).toBe("Konverterad 3");
    expectEditable(view, true);

    apiMocks.saveExamWorkspaceDocument.mockResolvedValueOnce(revision(3, SECOND.document.items, SECOND_STATUS));
    await view.get('[data-test="exam-workspace-save"]').trigger("click");
    await flushPromises();
    const [, params] = apiMocks.saveExamWorkspaceDocument.mock.calls[0];
    expect(params.expectedRevision).toBe(2);
    expect(params.document.items.map((item: NativeExamItem) => item.title)).toEqual([
      "Lärarens rubrik ett",
      "Konverterad 2",
      "Konverterad 3",
    ]);
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
    await forceInput(view, "exam-workspace-item-title-input", "Lärarens rubrik två");
    expect(view.find('[data-test="exam-workspace-dirty-pill"]').exists()).toBe(false);
    await selectItemRow(view, "item_001");
    expectEditable(view, true);

    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(SECOND_STATUS);
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(SECOND);
    await tick();

    expect(apiMocks.getExamWorkspaceConversionStatus).toHaveBeenCalledWith("job-1");
    expect(await titleOf(view, "item_002")).toBe("Konverterad 2");
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
