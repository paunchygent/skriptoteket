/**
 * Progressive DOCX conversion completion at the real workspace view boundary
 * (D30): the import is reported done, and its placeholders unlocked, only once
 * the open copy holds the final revision. A final status whose revision cannot
 * be read, or is read without its conversion, keeps the lock and the status
 * visible until a later poll merges the revision.
 */
import { flushPromises } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import type { ExamWorkspaceDocumentResponse } from "../../api/examWorkspace";
import { useToastStore } from "../../stores/toast";
import {
  convertingNoticeShown,
  converted,
  editPoints,
  expectEditable,
  FIRST_STATUS,
  installProgressiveConversionLifecycle,
  placeholder,
  revision,
  SECOND,
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

describe("Exam workspace progressive conversion completion", () => {
  it("keeps a placeholder locked until the final revision that arrived during a save is merged", async () => {
    const view = await uploadFirstBatch();
    await editPoints(view, "item_001", "11");
    let resolveSave!: (value: ExamWorkspaceDocumentResponse) => void;
    apiMocks.saveExamWorkspaceDocument.mockReturnValueOnce(new Promise((resolve) => { resolveSave = resolve; }));
    await view.get('[data-test="exam-workspace-save"]').trigger("click");

    const savedFirst = revision(
      2,
      [{ ...converted(1), points: 11 }, placeholder(2), placeholder(3)],
      FIRST_STATUS,
    );
    const finalItems = [{ ...converted(1), points: 11 }, converted(2), converted(3)];
    const succeeded = status("succeeded", 3, ["ready", "ready", "ready"]);
    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(succeeded);
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(revision(3, finalItems, succeeded));
    await tick();
    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledTimes(1);

    resolveSave(savedFirst);
    await flushPromises();
    // The status already reports every batch ready, but its revision is not merged yet.
    await selectItemRow(view, "item_002");
    expect(convertingNoticeShown(view)).toBe(true);
    expectEditable(view, false);
    await tick();

    expect(convertingNoticeShown(view)).toBe(false);

    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledTimes(2);
    expect(apiMocks.getExamWorkspaceConversionStatus).toHaveBeenCalledTimes(2);
    expect(await pointsOf(view, "item_002")).toBe("22");
    expect(await pointsOf(view, "item_001")).toBe("11");
    expect(view.find('[data-test="exam-workspace-conversion-status"]').exists()).toBe(false);
  });

  it("merges the final batch through a later teacher revision before it reports the import done", async () => {
    const view = await uploadFirstBatch();
    await editPoints(view, "item_001", "11");

    // Conversion finished at revision 2; another tab then saved revision 3 on top of it.
    const done = status("succeeded", 2, ["ready", "ready", "ready"]);
    const otherTab = revision(
      3,
      [converted(1), { ...converted(2), points: 32 }, converted(3)],
      done,
    );
    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(done);
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(otherTab);
    await tick();

    expect(await pointsOf(view, "item_001")).toBe("11");
    expect(await pointsOf(view, "item_002")).toBe("32");
    expect(await pointsOf(view, "item_003")).toBe("23");
    expect(convertingNoticeShown(view)).toBe(false);
    expectEditable(view, true);
    expect(view.find('[data-test="exam-workspace-conversion-status"]').exists()).toBe(false);

    apiMocks.saveExamWorkspaceDocument.mockResolvedValueOnce(revision(4, otherTab.document.items, done));
    await view.get('[data-test="exam-workspace-save"]').trigger("click");
    await flushPromises();
    const [, params] = apiMocks.saveExamWorkspaceDocument.mock.calls[0];
    expect(params.expectedRevision).toBe(3);
    await tick();
    expect(apiMocks.getExamWorkspaceConversionStatus).toHaveBeenCalledTimes(2);
  });

  it("keeps the placeholders locked after a final status while its revision cannot be read", async () => {
    const view = await uploadFirstBatch();
    const done = status("succeeded", 2, ["ready", "ready", "ready"]);
    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(done);
    apiMocks.getExamWorkspaceDocument.mockRejectedValueOnce(new Error("offline"));
    await tick();

    await selectItemRow(view, "item_002");
    expect(convertingNoticeShown(view)).toBe(true);
    expectEditable(view, false);
    expect(view.find('[data-test="exam-workspace-conversion-status"]').exists()).toBe(true);

    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(revision(2, SECOND.document.items, done));
    await tick();
    expect(await pointsOf(view, "item_002")).toBe("22");
    expect(convertingNoticeShown(view)).toBe(false);
    expect(view.find('[data-test="exam-workspace-conversion-status"]').exists()).toBe(false);
  });

  it("keeps the placeholders locked and the import unfinished when the followed exam's revision comes without its conversion", async () => {
    const view = await uploadFirstBatch();
    await editPoints(view, "item_001", "11");

    // The status names revision 2, but the document read returns it without the conversion that owns its units.
    const partial = status("running", 2, ["ready", "ready", "converting"]);
    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(partial);
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(
      revision(2, [converted(1), converted(2), placeholder(3)], null),
    );
    await tick();

    expect(await pointsOf(view, "item_001")).toBe("11");
    for (const itemId of ["item_002", "item_003"]) {
      await selectItemRow(view, itemId);
      expect(convertingNoticeShown(view), itemId).toBe(true);
      expectEditable(view, false);
    }
    expect(view.find('[data-test="exam-workspace-conversion-status"]').exists()).toBe(true);
    expect(vi.mocked(useToastStore().success)).not.toHaveBeenCalled();

    // The next poll reads the revision with its conversion and merges it.
    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(partial);
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(
      revision(2, [converted(1), converted(2), placeholder(3)], partial),
    );
    await tick();
    expect(await pointsOf(view, "item_002")).toBe("22");
    expect(convertingNoticeShown(view)).toBe(false);
    await selectItemRow(view, "item_003");
    expect(convertingNoticeShown(view)).toBe(true);
    expect(await pointsOf(view, "item_001")).toBe("11");
  });
});
