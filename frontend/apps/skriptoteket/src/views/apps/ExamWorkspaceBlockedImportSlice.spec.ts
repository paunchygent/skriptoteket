/**
 * Importing over unsaved edits is impossible (TASK-SKRIPT-39-04-09 P4).
 *
 * Expected behavior:
 *   While the open exam has unsaved changes, the file picker is disabled and
 *   a dropped .docx is ignored, by the one `importBlocked` rule both paths
 *   read; the Öppna drawer line "Vänta tills ändringarna har sparats."
 *   explains why and the teacher's edits stay. Once the copy is clean again
 *   (saved, or edited back), the picker and drops import as before.
 */

import { flushPromises } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ExamWorkspaceConversionStatus } from "../../api/examWorkspace";
import {
  buildResponse,
  importFixtureDocument,
  mountExamWorkspace,
  resetSliceApiMocks,
  saveDocument,
  selectItemRow,
} from "./ExamWorkspaceSlice.specSupport";

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

const PENDING_COPY = "Vänta tills ändringarna har sparats.";

const succeededConversion: ExamWorkspaceConversionStatus = {
  job_id: "job-1", lineage_id: "lineage-1", state: "succeeded", error_message: null, summary: null,
  document_revision: 1, questions_total: 0, questions_done: 0, units: [],
};

beforeEach(() => {
  resetSliceApiMocks(apiMocks);
  for (const mock of Object.values(exportApiMocks)) {
    mock.mockReset();
  }
  apiMocks.findExamWorkspaceAnswerKeySuggestions.mockResolvedValue(null);
  apiMocks.getExamWorkspaceConversionStatus.mockResolvedValue(succeededConversion);
  apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(
      buildResponse({ conversion: succeededConversion, version: 1 }),
    );
    return { job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null, summary: null,
      document_revision: null, questions_total: 0, questions_done: 0, units: [] };
  });
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [], ordering: "course" });
});

type Wrapper = Awaited<ReturnType<typeof mountExamWorkspace>>["wrapper"];

/** An imported exam whose first question's points the teacher changed and did not save. */
async function examWithUnsavedEdit(): Promise<Wrapper> {
  const { wrapper } = await mountExamWorkspace();
  await importFixtureDocument(wrapper);
  await selectItemRow(wrapper, "item_001");
  await wrapper.find('[data-test="exam-workspace-item-points-input"]').setValue("7");
  await flushPromises();
  expect(wrapper.get('[data-test="exam-workspace-save-state"]').text()).toContain("Sparar …");
  return wrapper;
}

async function dropDocx(wrapper: Wrapper): Promise<void> {
  await wrapper.find('[data-test="exam-workspace-drop-zone"]').trigger("drop", {
    dataTransfer: {
      files: [new File(["prov"], "Annat_prov.docx", { type: "application/octet-stream" })],
    },
  });
  await flushPromises();
}

function picker(wrapper: Wrapper) {
  return wrapper.find<HTMLInputElement>('[data-test="exam-workspace-source-file-input"]');
}

describe("import while the open exam has unsaved changes", () => {
  it("disables the picker and explains why", async () => {
    const wrapper = await examWithUnsavedEdit();

    expect(picker(wrapper).element.disabled).toBe(true);
    expect(wrapper.get('[data-test="exam-workspace-open-dirty-hint"]').text()).toContain(
      PENDING_COPY,
    );
    expect(wrapper.get('[data-test="exam-workspace-pick-file"]').attributes("disabled")).toBeDefined();
  });

  it("ignores a dropped .docx and keeps the unsaved edit", async () => {
    const wrapper = await examWithUnsavedEdit();

    await dropDocx(wrapper);

    expect(apiMocks.importExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(wrapper.find('[data-test="exam-workspace-source-file-error"]').exists()).toBe(false);
    expect(wrapper.get('[data-test="exam-workspace-save-state"]').text()).toContain("Sparar …");
    expect(
      wrapper.find<HTMLInputElement>('[data-test="exam-workspace-item-points-input"]').element
        .value,
    ).toBe("7");
  });

  it("ignores a dropped file of the wrong type without guidance", async () => {
    const wrapper = await examWithUnsavedEdit();

    await wrapper.find('[data-test="exam-workspace-drop-zone"]').trigger("drop", {
      dataTransfer: { files: [new File(["pdf"], "Prov.pdf", { type: "application/pdf" })] },
    });
    await flushPromises();

    expect(wrapper.find('[data-test="exam-workspace-source-file-error"]').exists()).toBe(false);
  });

  it("imports again once the edit is saved", async () => {
    const wrapper = await examWithUnsavedEdit();
    await saveDocument(wrapper);

    expect(picker(wrapper).element.disabled).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-open-dirty-hint"]').exists()).toBe(false);
    expect(wrapper.get('[data-test="exam-workspace-save-state"]').text()).not.toContain("Sparar …");
    await dropDocx(wrapper);
    expect(apiMocks.importExamWorkspaceDocument).toHaveBeenCalledTimes(2);
  });
});
