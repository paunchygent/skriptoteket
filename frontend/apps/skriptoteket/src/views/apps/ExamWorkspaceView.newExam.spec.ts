/**
 * Exam workspace view: Nytt prov for a signed-in teacher (TASK-SKRIPT-40-04-21, F1 repair).
 *
 * Expected behavior:
 *   One click on Nytt prov saves the open exam first (the coordinator's
 *   settle runs before the blank POST), installs the created exam, reloads
 *   the Prov list, and never shows a confirm dialog.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ExamWorkspaceDocumentResponse } from "../../api/examWorkspace";
import {
  arrangeViewApis,
  buildDocument,
  buildResponse,
  editPoints,
  importFixture,
  mountView,
  queuedImport,
  unmountViews,
} from "./ExamWorkspaceView.specSupport";
import { buildSavedExamSummary } from "./exam-workspace/useExamWorkspaceDocument.specSupport";

const apiMocks = vi.hoisted(() => ({
  copyExamWorkspaceDocument: vi.fn(),
  createExamWorkspaceBlank: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  importExamWorkspaceDigiExam: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceQti: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));

vi.mock("../../api/examWorkspaceExports", () => ({
  downloadExamWorkspaceExport: vi.fn(),
}));
vi.mock("../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../test/examCourseCatalog")).getExamCourseCatalog,
}));

afterEach(unmountViews);

beforeEach(() => {
  arrangeViewApis(apiMocks);
});

/** The blank exam the signed-in route creates: one empty question, no title. */
function blankCreatedResponse(): ExamWorkspaceDocumentResponse {
  const base = buildResponse();
  const document = { ...buildDocument(), document_id: "lineage-new", title: "" };
  return {
    ...base,
    conversion: null,
    document,
    history_cursor: "cursor-new",
    notes: [],
    saved_document: { ...document },
    summary: {
      ...base.summary,
      lineage_id: "lineage-new",
      name: "",
      title: "",
      vault_file_id: "lineage-new",
    },
  };
}

describe("ExamWorkspaceView teacher Nytt prov", () => {
  it("saves the open exam first, installs the created exam and reloads the saved list with no dialog", async () => {
    const created = blankCreatedResponse();
    apiMocks.createExamWorkspaceBlank.mockResolvedValue(
      buildSavedExamSummary({ lineage_id: "lineage-new", name: "", title: "", vault_file_id: "lineage-new" }),
    );
    apiMocks.importExamWorkspaceDocument.mockResolvedValue(queuedImport);
    apiMocks.getExamWorkspaceDocument.mockImplementation(async (lineageId: string) => {
      if (lineageId === "lineage-new") {
        return created;
      }
      return buildResponse();
    });
    const fallbackHistory = apiMocks.getExamWorkspaceHistory.getMockImplementation();
    apiMocks.getExamWorkspaceHistory.mockImplementation(async (lineageId: string) => {
      if (lineageId === "lineage-new") {
        return {
          baseline_step_id: "cursor-new",
          cursor: "cursor-new",
          position_step_id: "cursor-new",
          step_ids: [],
        };
      }
      if (!fallbackHistory) {
        throw new Error("expected the arranged step history");
      }
      return fallbackHistory(lineageId);
    });
    const wrapper = await mountView();

    await importFixture(wrapper);
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(false);

    await editPoints(wrapper, "5");
    await vi.waitFor(
      () => expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalled(),
      { timeout: 5000 },
    );
    await vi.waitFor(
      () => expect(wrapper.find('[data-test="exam-workspace-save-state"]').text()).toMatch(/^Sparat/),
      { timeout: 5000 },
    );

    await wrapper.get('[data-test="exam-workspace-new-exam"]').trigger("click");
    await vi.waitFor(
      () => expect(apiMocks.createExamWorkspaceBlank).toHaveBeenCalledTimes(1),
      { timeout: 5000 },
    );
    await flushPromises();

    // The open exam is saved first: the settle's store runs before the POST.
    const storedOrder = apiMocks.storeExamWorkspaceUndoStep.mock.invocationCallOrder[0] ?? Infinity;
    const createdOrder = apiMocks.createExamWorkspaceBlank.mock.invocationCallOrder[0] ?? -Infinity;
    expect(storedOrder).toBeLessThan(createdOrder);
    // The created exam is installed and the saved list reloads.
    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledWith("lineage-new");
    expect(apiMocks.listExamWorkspaceDocuments.mock.calls.length).toBeGreaterThan(1);
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-question-list"]').exists()).toBe(true);
    // No confirm dialog, for a teacher or anyone else on this path.
    expect(wrapper.find('[data-test="exam-workspace-new-exam-confirm"]').exists()).toBe(false);
  });
});
