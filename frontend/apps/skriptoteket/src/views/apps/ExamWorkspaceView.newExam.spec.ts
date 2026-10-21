/**
 * Teacher exam workspace: Nytt prov (TASK-SKRIPT-40-04-21, D1, D3, D4, D7).
 *
 * Expected behavior:
 *   One click on "Nytt prov" posts once to the blank route, reloads the
 *   saved list and opens the returned untitled exam with no confirm dialog.
 *   The empty state names Nytt prov first.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ExamWorkspaceDocumentSummary } from "../../api/examWorkspace";
import { buildSavedExamSummary } from "./exam-workspace/useExamWorkspaceDocument.specSupport";
import {
  buildResponse,
  mountExamWorkspace,
  resetSliceApiMocks,
  unmountExamWorkspace,
} from "./ExamWorkspaceSlice.specSupport";

const apiMocks = vi.hoisted(() => ({
  createExamWorkspaceBlank: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));
const exportApiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
}));

vi.mock("../../api/examWorkspaceExports", () => exportApiMocks);
vi.mock("../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../test/examCourseCatalog")).getExamCourseCatalog,
}));

const EMPTY_STATE_COPY =
  "Skapa ett nytt prov, öppna ett sparat prov eller importera från Word eller DigiExam.";

const NEW_EXAM_SUMMARY: ExamWorkspaceDocumentSummary = buildSavedExamSummary({
  course_key: null,
  lineage_id: "lineage-new",
  name: "Namnlöst prov.provdokument.zip",
  saved_at: "2026-10-21T10:00:00Z",
  title: "",
  vault_file_id: "file-new",
  version: 1,
});

function newExamResponse() {
  const response = buildResponse({ title: "", version: 1 });
  const document = { ...response.document, document_id: "lineage-new" };
  return { ...response, conversion: null, document, saved_document: document, summary: NEW_EXAM_SUMMARY };
}

beforeEach(() => {
  resetSliceApiMocks(apiMocks);
  for (const mock of Object.values(exportApiMocks)) {
    mock.mockReset();
  }
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [], ordering: "course" });
});

afterEach(() => {
  unmountExamWorkspace();
});

describe("ExamWorkspaceView Nytt prov", () => {
  it("names Nytt prov first in the empty state", async () => {
    const { wrapper } = await mountExamWorkspace();

    expect(wrapper.find('[data-test="exam-workspace-empty"]').text()).toContain(EMPTY_STATE_COPY);
  });

  it("opens the created untitled exam and reloads the saved list", async () => {
    apiMocks.createExamWorkspaceBlank.mockResolvedValue(NEW_EXAM_SUMMARY);
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(newExamResponse());
    const { wrapper } = await mountExamWorkspace();
    expect(wrapper.find('[data-test="exam-workspace-new-confirm"]').exists()).toBe(false);

    await wrapper.get('[data-test="exam-workspace-new"]').trigger("click");
    await flushPromises();

    expect(apiMocks.createExamWorkspaceBlank).toHaveBeenCalledTimes(1);
    expect(apiMocks.createExamWorkspaceBlank).toHaveBeenCalledWith();
    expect(apiMocks.listExamWorkspaceDocuments.mock.calls.length).toBeGreaterThanOrEqual(2);
    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledWith("lineage-new");
    expect(wrapper.find('[data-test="exam-workspace-empty"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe("Namnlöst prov");
    expect(wrapper.find('[data-test="exam-workspace-new-confirm"]').exists()).toBe(false);
  });
});
