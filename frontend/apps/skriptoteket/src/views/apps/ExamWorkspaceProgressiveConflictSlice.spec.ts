/**
 * Progressive DOCX conversion save conflicts at the real workspace view
 * boundary (D30): when a batch is committed during the teacher's save, the
 * newer revision is merged with the teacher's edits and the save is repeated
 * on it. A revision that cannot be fetched, or a save the server refuses,
 * leaves the teacher's copy intact.
 */
import { flushPromises } from "@vue/test-utils";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { ApiError } from "../../api/client";
import type { ExamWorkspaceConversionStatus, NativeExamItem } from "../../api/examWorkspace";
import { EXAM_WORKSPACE_CONFLICT_COPY } from "./exam-workspace/useExamWorkspaceDocument";
import {
  converted,
  editPoints,
  installProgressiveConversionLifecycle,
  revision,
  SECOND,
  SECOND_STATUS,
  status,
  tick,
  pointsOf,
  uploadFirstBatch,
} from "./ExamWorkspaceProgressiveConversionSlice.specSupport";

import { arrangeStepHistory } from "./ExamWorkspaceHistory.specSupport";

const apiMocks = vi.hoisted(() => ({
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
}));
const exportApiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
}));
vi.mock("../../api/examWorkspaceExports", () => exportApiMocks);
vi.mock("../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../test/examCourseCatalog")).getExamCourseCatalog,
}));

installProgressiveConversionLifecycle(apiMocks);
beforeEach(() => {
  arrangeStepHistory(apiMocks);
});

describe("Exam workspace progressive conversion save conflicts", () => {
  it("saves again on the newer revision when conversion saved one during the teacher's save", async () => {
    const view = await uploadFirstBatch();
    await editPoints(view, "item_001", "11");

    apiMocks.saveExamWorkspaceDocument
      .mockRejectedValueOnce(new ApiError({ code: "CONFLICT", message: "Konflikt", status: 409 }))
      .mockResolvedValueOnce(revision(3, SECOND.document.items, SECOND_STATUS));
    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(SECOND_STATUS);
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(SECOND);
    await view.get('[data-test="exam-workspace-save"]').trigger("click");
    await flushPromises();

    expect(apiMocks.saveExamWorkspaceDocument).toHaveBeenCalledTimes(2);
    const [, retry] = apiMocks.saveExamWorkspaceDocument.mock.calls[1];
    expect(retry.expectedRevision).toBe(2);
    expect(retry.document.items.map((item: NativeExamItem) => item.points)).toEqual([11, 22, 23]);
    expect(view.text()).not.toContain(EXAM_WORKSPACE_CONFLICT_COPY);
  });

  it("merges and saves the teacher's edits when a save conflicts while a status poll is still in flight", async () => {
    const view = await uploadFirstBatch();
    await editPoints(view, "item_001", "11");

    let resolvePoll!: (value: ExamWorkspaceConversionStatus) => void;
    apiMocks.getExamWorkspaceConversionStatus
      .mockReturnValueOnce(new Promise((resolve) => { resolvePoll = resolve; }))
      .mockResolvedValueOnce(SECOND_STATUS);
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(SECOND);
    apiMocks.saveExamWorkspaceDocument
      .mockRejectedValueOnce(new ApiError({ code: "CONFLICT", message: "Konflikt", status: 409 }))
      .mockResolvedValueOnce(revision(3, SECOND.document.items, SECOND_STATUS));
    await tick();
    await view.get('[data-test="exam-workspace-save"]').trigger("click");
    await flushPromises();
    resolvePoll(SECOND_STATUS);
    await flushPromises();

    expect(apiMocks.saveExamWorkspaceDocument).toHaveBeenCalledTimes(2);
    const [, retry] = apiMocks.saveExamWorkspaceDocument.mock.calls[1];
    expect(retry.expectedRevision).toBe(2);
    expect(retry.document.items.map((item: NativeExamItem) => item.points)).toEqual([11, 22, 23]);
    expect(view.text()).not.toContain(EXAM_WORKSPACE_CONFLICT_COPY);
  });

  it("merges and saves again at once when another batch moves the head past the conflict's status", async () => {
    const view = await uploadFirstBatch();
    await editPoints(view, "item_001", "11");

    // The save from revision 1 conflicts; the status then describes revision 2,
    // but another batch commits revision 3 before the document is read. The
    // document response names revision 3's own units, so it merges directly.
    const thirdStatus = status("running", 3, ["ready", "ready", "ready"]);
    const third = revision(3, [converted(1), converted(2), converted(3)], thirdStatus);
    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(SECOND_STATUS);
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(third);
    apiMocks.saveExamWorkspaceDocument
      .mockRejectedValueOnce(new ApiError({ code: "CONFLICT", message: "Konflikt", status: 409 }))
      .mockResolvedValueOnce(revision(4, third.document.items, thirdStatus));
    await view.get('[data-test="exam-workspace-save"]').trigger("click");
    await flushPromises();

    expect(view.text()).not.toContain(EXAM_WORKSPACE_CONFLICT_COPY);
    expect(apiMocks.saveExamWorkspaceDocument).toHaveBeenCalledTimes(2);
    const [, retry] = apiMocks.saveExamWorkspaceDocument.mock.calls[1];
    expect(retry.expectedRevision).toBe(3);
    expect(retry.document.items.map((item: NativeExamItem) => item.points)).toEqual([11, 22, 23]);
  });

  it("keeps the teacher's copy when the conflicting revision cannot be fetched", async () => {
    const view = await uploadFirstBatch();
    await editPoints(view, "item_001", "11");

    apiMocks.getExamWorkspaceConversionStatus.mockRejectedValueOnce(new Error("offline"));
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(SECOND);
    apiMocks.saveExamWorkspaceDocument.mockRejectedValueOnce(
      new ApiError({ code: "CONFLICT", message: "Konflikt", status: 409 }),
    );
    await view.get('[data-test="exam-workspace-save"]').trigger("click");
    await flushPromises();

    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(await pointsOf(view, "item_001")).toBe("11");
  });

  it("keeps the teacher's copy when the server refuses a save that changed a converting question", async () => {
    const view = await uploadFirstBatch();
    await editPoints(view, "item_001", "11");
    apiMocks.saveExamWorkspaceDocument.mockRejectedValueOnce(
      new ApiError({
        code: "VALIDATION_ERROR",
        message: "Vägrad",
        status: 422,
        details: { item_ids: ["item_002"] },
      }),
    );
    await view.get('[data-test="exam-workspace-save"]').trigger("click");
    await flushPromises();

    expect(await pointsOf(view, "item_001")).toBe("11");
    expect(view.get('[data-test="exam-workspace-save-state"]').text()).toContain("Osparat");
    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(view.text()).not.toContain(EXAM_WORKSPACE_CONFLICT_COPY);
  });
});
