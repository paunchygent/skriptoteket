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

import type { ExamWorkspaceDocumentSummary } from "../../api/examWorkspace";
import {
  buildResponse,
  importFixtureDocument,
  mountExamWorkspace,
  selectItemRow,
} from "./ExamWorkspaceSlice.specSupport";

const apiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceEnrichment: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
  startExamWorkspaceEnrichment: vi.fn(),
}));

vi.mock("../../api/examWorkspace", () => apiMocks);

const OTHER_EXAM: ExamWorkspaceDocumentSummary = {
  lineage_id: "lineage-2",
  name: "Matteprov_v48.provdokument.zip",
  saved_at: "2026-10-08T07:30:00Z",
  vault_file_id: "file-9",
  version: 3,
};

function otherExamResponse() {
  const response = buildResponse({ title: "Matteprov v48", version: 3 });
  return {
    ...response,
    document: { ...response.document, document_id: "lineage-2" },
    summary: OTHER_EXAM,
  };
}

beforeEach(() => {
  for (const mock of Object.values(apiMocks)) {
    mock.mockReset();
  }
  apiMocks.importExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 1 }));
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [OTHER_EXAM] });
  apiMocks.getExamWorkspaceEnrichment.mockResolvedValue({
    document_revision: 1,
    lineage_id: "lineage-1",
    proposals: [],
    state: "not_requested",
  });
});

describe("ExamWorkspaceView reopen slice", () => {
  it("reopens the head version named in the address", async () => {
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(
      buildResponse({ title: "Sparat prov", version: 4 }),
    );

    const { wrapper } = await mountExamWorkspace({ document: "lineage-1" });

    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledWith("lineage-1");
    expect(wrapper.find('[data-test="exam-workspace-summary-title"]').text()).toBe(
      "Sparat prov",
    );
    expect(wrapper.find('[data-test="exam-workspace-summary-version"]').text()).toBe(
      "Version 4",
    );
    expect(wrapper.findAll('[data-test^="exam-workspace-item-row-"]')).toHaveLength(8);
  });

  it("lists saved exams by name and newest version and opens one", async () => {
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(otherExamResponse());
    const { router, wrapper } = await mountExamWorkspace();

    expect(apiMocks.getExamWorkspaceDocument).not.toHaveBeenCalled();
    const entry = wrapper.find('[data-test="exam-workspace-open-lineage-2"]');
    expect(entry.text()).toContain("Matteprov_v48");
    expect(entry.text()).not.toContain(".provdokument.zip");
    expect(entry.text()).toContain("Version 3");

    await entry.trigger("click");
    await flushPromises();

    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledWith("lineage-2");
    expect(wrapper.find('[data-test="exam-workspace-summary-title"]').text()).toBe(
      "Matteprov v48",
    );
    expect(router.currentRoute.value.query.document).toBe("lineage-2");
    expect(wrapper.find('[data-test="exam-workspace-open-lineage-2"]').exists()).toBe(false);
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

    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledWith("lineage-2");
    expect(wrapper.find('[data-test="exam-workspace-summary-title"]').text()).toBe(
      "Matteprov v48",
    );
    expect(router.currentRoute.value.query.document).toBe("lineage-2");
  });

  it("keeps the edited exam and restores the address when it changes with unsaved edits", async () => {
    const { router, wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);
    await selectItemRow(wrapper, "item_001");
    await wrapper.find('[data-test="exam-workspace-item-title-input"]').setValue("Ändrad");

    await router.push({ query: { document: "lineage-2" } });
    await flushPromises();

    expect(apiMocks.getExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(router.currentRoute.value.query.document).toBe("lineage-1");
    expect(wrapper.find('[data-test="exam-workspace-summary-title"]').text()).toBe(
      "NO-prov HT25",
    );
    expect(wrapper.find('[data-test="exam-workspace-dirty-pill"]').exists()).toBe(true);
  });

  it("keeps an import that finishes while the saved list is still loading", async () => {
    let resolveList: (value: { documents: ExamWorkspaceDocumentSummary[] }) => void = () => {};
    apiMocks.listExamWorkspaceDocuments.mockReturnValue(
      new Promise((resolve) => {
        resolveList = resolve;
      }),
    );
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(otherExamResponse());
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    resolveList({ documents: [OTHER_EXAM] });
    await flushPromises();
    await wrapper.find('[data-test="exam-workspace-open-lineage-2"]').trigger("click");
    await flushPromises();

    expect(wrapper.find('[data-test="exam-workspace-open-lineage-1"]').exists()).toBe(true);
  });

  it("blocks opening another exam while the current one has unsaved edits", async () => {
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_001");
    await wrapper.find('[data-test="exam-workspace-item-title-input"]').setValue("Ändrad");

    expect(
      wrapper.find('[data-test="exam-workspace-open-lineage-2"]').attributes("disabled"),
    ).toBeDefined();
    expect(wrapper.text()).toContain("Spara det öppna provet innan du öppnar ett annat.");
  });
});
