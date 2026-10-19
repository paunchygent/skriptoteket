/**
 * Exam workspace reopen slice behavior.
 *
 * Slice purpose:
 *   Lock reopening a saved exam after leaving the page: the
 *   `?document=<lineage_id>` address reopens the head version directly, and
 *   the rail lists the teacher's saved exams (one entry per exam, newest
 *   saved version) to open from.
 *
 * Expected behavior:
 *   Importing or opening a document writes its lineage into the address so a
 *   reload or a shared link reopens it, and a later address change opens the
 *   named exam. Opening another exam is blocked while the current one has
 *   unsaved edits. An import that finishes while the saved list is loading
 *   stays in the list.
 */

import { flushPromises } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  ExamWorkspaceConversionStatus,
  ExamWorkspaceDocumentSummary,
} from "../../api/examWorkspace";
import { buildSavedExamSummary } from "./exam-workspace/useExamWorkspaceDocument.specSupport";
import {
  buildResponse,
  importFixtureDocument,
  mountExamWorkspace,
  selectItemRow,
  unmountExamWorkspace,
} from "./ExamWorkspaceSlice.specSupport";
import { arrangeStepHistory } from "./ExamWorkspaceHistory.specSupport";

const apiMocks = vi.hoisted(() => ({
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
}));
const exportApiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
}));

vi.mock("../../api/examWorkspaceExports", () => exportApiMocks);
vi.mock("../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../test/examCourseCatalog")).getExamCourseCatalog,
}));

const OTHER_EXAM: ExamWorkspaceDocumentSummary = buildSavedExamSummary({
  lineage_id: "lineage-2",
  name: "Matteprov_v48.provdokument.zip",
  saved_at: "2026-10-08T07:30:00Z",
  title: "Matteprov v48",
  vault_file_id: "file-9",
  version: 3,
});

function otherExamResponse() {
  const response = buildResponse({ title: "Matteprov v48", version: 3 });
  return {
    ...response,
    document: { ...response.document, document_id: "lineage-2" },
    summary: OTHER_EXAM,
  };
}

/** The finished import: its poll status, and the conversion its fetched document carries. */
const succeededConversion: ExamWorkspaceConversionStatus = {
  job_id: "job-1", lineage_id: "lineage-1", state: "succeeded", error_message: null, summary: null,
  document_revision: 1, questions_total: 0, questions_done: 0, units: [],
};

beforeEach(() => {
  for (const mock of [...Object.values(apiMocks), ...Object.values(exportApiMocks)]) {
    mock.mockReset();
  }
  arrangeStepHistory(apiMocks);
  apiMocks.getExamWorkspaceConversionStatus.mockResolvedValue(succeededConversion);
  apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(
      buildResponse({ conversion: succeededConversion, version: 1 }),
    );
    return { job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null, summary: null,
      document_revision: null, questions_total: 0, questions_done: 0, units: [] };
  });
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [OTHER_EXAM], ordering: "course" });
});

afterEach(() => {
  unmountExamWorkspace();
});

describe("ExamWorkspaceView reopen slice", () => {
  it("reopens the head version named in the address", async () => {
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(
      buildResponse({ title: "Sparat prov", version: 4 }),
    );

    const { wrapper } = await mountExamWorkspace({ document: "lineage-1" });

    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledWith("lineage-1");
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe(
      "Sparat prov",
    );
    expect(wrapper.find('[data-test="exam-workspace-save-state"]').text()).toBe("Sparat");
    expect(wrapper.findAll('[data-test^="exam-workspace-row-"]')).toHaveLength(8);
  });

  it("lists saved exams by name and newest version and opens one", async () => {
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(otherExamResponse());
    const { router, wrapper } = await mountExamWorkspace();

    expect(apiMocks.getExamWorkspaceDocument).not.toHaveBeenCalled();
    const entry = wrapper.find('[data-test="exam-workspace-open-lineage-2"]');
    expect(entry.text()).toContain("Matteprov_v48");
    expect(entry.text()).not.toContain(".provdokument.zip");
    expect(entry.text()).toContain("Sparad ");
    expect(entry.attributes("aria-current")).toBeUndefined();

    await entry.trigger("click");
    await flushPromises();

    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledWith("lineage-2");
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe(
      "Matteprov v48",
    );
    expect(router.currentRoute.value.query.document).toBe("lineage-2");
    // On desktop the drawer stays open and marks the opened exam as the current one.
    expect(wrapper.find('[data-test="exam-workspace-open-lineage-2"]').attributes("aria-current")).toBe("true");
  });

  it("writes the imported document into the address so a reload reopens it", async () => {
    const { router, wrapper } = await mountExamWorkspace();

    await importFixtureDocument(wrapper);

    expect(router.currentRoute.value.query.document).toBe("lineage-1");
  });

  it("opens the exam named by a later address change", async () => {
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(otherExamResponse());
    const { router, wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await router.push({ query: { document: "lineage-2" } });
    await flushPromises();

    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledTimes(2);
    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledWith("lineage-2");
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe(
      "Matteprov v48",
    );
    expect(router.currentRoute.value.query.document).toBe("lineage-2");
  });

  it("keeps the edited exam and restores the address when it changes with unsaved edits", async () => {
    const { router, wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);
    await selectItemRow(wrapper, "item_001");
    await wrapper.find('[data-test="exam-workspace-item-points-input"]').setValue("7");

    await router.push({ query: { document: "lineage-2" } });
    await flushPromises();

    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledExactlyOnceWith("lineage-1");
    expect(router.currentRoute.value.query.document).toBe("lineage-1");
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe(
      "NO-prov HT25",
    );
    expect(wrapper.find('[data-test="exam-workspace-save-state"]').text()).toBe("Sparar …");
  });

  it("restores the address to the open exam when the named exam fails to open", async () => {
    const { router, wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);
    apiMocks.getExamWorkspaceDocument.mockRejectedValue(new Error("network"));

    await router.push({ query: { document: "lineage-2" } });
    await flushPromises();

    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledWith("lineage-2");
    expect(router.currentRoute.value.query.document).toBe("lineage-1");
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe(
      "NO-prov HT25",
    );
  });

  it("keeps an import that finishes while the saved list is still loading", async () => {
    let resolveList: (value: { documents: ExamWorkspaceDocumentSummary[]; ordering: "course" }) => void = () => {};
    apiMocks.listExamWorkspaceDocuments.mockReturnValue(
      new Promise((resolve) => {
        resolveList = resolve;
      }),
    );
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(otherExamResponse());
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    resolveList({ documents: [OTHER_EXAM], ordering: "course" });
    await flushPromises();
    await wrapper.find('[data-test="exam-workspace-open-lineage-2"]').trigger("click");
    await flushPromises();

    expect(wrapper.find('[data-test="exam-workspace-open-lineage-1"]').exists()).toBe(true);
  });

  it("blocks opening another exam while the current one has unsaved edits", async () => {
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(otherExamResponse());
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_001");
    await wrapper.find('[data-test="exam-workspace-item-points-input"]').setValue("7");

    const entry = wrapper.find('[data-test="exam-workspace-open-lineage-2"]');
    expect(entry.attributes("aria-disabled")).toBe("true");
    expect(entry.attributes("title")).toBe("Spara det öppna provet innan du öppnar ett annat.");
    expect(wrapper.find('[data-test="exam-workspace-open-dirty-hint"]').text()).toContain(
      "Spara det öppna provet innan du importerar eller öppnar ett annat.",
    );
    expect(wrapper.find('[data-test="exam-workspace-pick-file"]').attributes("disabled")).toBeDefined();

    await entry.trigger("click");
    await flushPromises();

    expect(apiMocks.getExamWorkspaceDocument).not.toHaveBeenCalledWith("lineage-2");
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe("NO-prov HT25");
  });
});
