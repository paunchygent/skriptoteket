/**
 * Importing over unsaved edits is impossible (TASK-SKRIPT-39-04-09 P4).
 *
 * Expected behavior:
 *   While the open exam has unsaved changes, the file picker is disabled and
 *   a dropped .docx is ignored, by the one `importBlocked` rule both paths
 *   read; the line "Spara det öppna provet innan du importerar ett annat."
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
  saveDocument,
  selectItemRow,
} from "./ExamWorkspaceSlice.specSupport";

const apiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
}));

vi.mock("../../api/examWorkspace", async () => ({
  ...apiMocks,
  EXAM_PARENT_DELETE_READY: false,
  getExamCourseCatalog: (await import("../../test/examCourseCatalog")).getExamCourseCatalog,
}));

const SAVE_FIRST_COPY = "Spara det öppna provet innan du importerar ett annat.";

const succeededConversion: ExamWorkspaceConversionStatus = {
  job_id: "job-1", lineage_id: "lineage-1", state: "succeeded", error_message: null, summary: null,
  document_revision: 1, questions_total: 0, questions_done: 0, units: [],
};

beforeEach(() => {
  for (const mock of Object.values(apiMocks)) {
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
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [] });
});

type Wrapper = Awaited<ReturnType<typeof mountExamWorkspace>>["wrapper"];

/** An imported exam whose first question's points the teacher changed and did not save. */
async function examWithUnsavedEdit(): Promise<Wrapper> {
  const { wrapper } = await mountExamWorkspace();
  await importFixtureDocument(wrapper);
  await selectItemRow(wrapper, "item_001");
  await wrapper.find('[data-test="exam-workspace-item-points-input"]').setValue("7");
  await flushPromises();
  expect(wrapper.find('[data-test="exam-workspace-dirty-pill"]').exists()).toBe(true);
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
    expect(wrapper.text()).toContain(SAVE_FIRST_COPY);
  });

  it("ignores a dropped .docx and keeps the unsaved edit", async () => {
    const wrapper = await examWithUnsavedEdit();

    await dropDocx(wrapper);

    expect(apiMocks.importExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(wrapper.find('[data-test="exam-workspace-source-file-error"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-dirty-pill"]').exists()).toBe(true);
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
    apiMocks.saveExamWorkspaceDocument.mockResolvedValueOnce(
      buildResponse({ conversion: succeededConversion, version: 2 }),
    );
    await saveDocument(wrapper);

    expect(picker(wrapper).element.disabled).toBe(false);
    expect(wrapper.text()).not.toContain(SAVE_FIRST_COPY);
    await dropDocx(wrapper);
    expect(apiMocks.importExamWorkspaceDocument).toHaveBeenCalledTimes(2);
  });
});
