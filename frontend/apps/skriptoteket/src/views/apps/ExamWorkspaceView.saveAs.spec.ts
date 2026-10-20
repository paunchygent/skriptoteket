/**
 * Exam workspace Spara som behavior.
 *
 * Expected behavior:
 *   Spara som refuses a taken name at the field and reports success as state,
 *   not as a toast.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../api/client";
import { useToastStore } from "../../stores/toast";
import { buildSavedExamSummary } from "./exam-workspace/useExamWorkspaceDocument.specSupport";
import {
  arrangeViewApis,
  buildResponse,
  importFixture,
  importsTheFixture,
  mountView,
  unmountViews,
  type ViewWrapper,
} from "./ExamWorkspaceView.specSupport";

const apiMocks = vi.hoisted(() => ({
  copyExamWorkspaceDocument: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  importExamWorkspaceDigiExam: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
}));
const exportApiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
}));
const unreadable = vi.hoisted(() => ({ listUnreadableExamWorkspaceDocuments: vi.fn() }));

vi.mock("../../api/examWorkspaceExports", () => exportApiMocks);
vi.mock("../../api/examWorkspaceUnreadableFiles", () => unreadable);
vi.mock("../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../test/examCourseCatalog")).getExamCourseCatalog,
}));

afterEach(unmountViews);

beforeEach(() => {
  arrangeViewApis(apiMocks);
  unreadable.listUnreadableExamWorkspaceDocuments.mockReset();
  unreadable.listUnreadableExamWorkspaceDocuments.mockResolvedValue({ documents: [] });
});

describe("ExamWorkspaceView Spara som", () => {
  async function openSaveAs(wrapper: ViewWrapper) {
    await wrapper.find('[data-test="exam-workspace-save-as-command"]').trigger("click");
    await flushPromises();
  }

  async function submitName(wrapper: ViewWrapper, name: string) {
    await wrapper.find('[data-test="exam-workspace-save-as-name"]').setValue(name);
    await wrapper.find('[data-test="exam-workspace-save-as"] form').trigger("submit");
    await flushPromises();
  }

  function submit(wrapper: ViewWrapper) {
    return wrapper.find<HTMLButtonElement>('[data-test="exam-workspace-save-as-submit"]');
  }

  it("prefills the name as '<name> (kopia)'", async () => {
    importsTheFixture(apiMocks);
    const wrapper = await mountView();
    await importFixture(wrapper);

    await openSaveAs(wrapper);

    expect(wrapper.find('[data-test="exam-workspace-save-as"]').exists()).toBe(true);
    expect(
      wrapper.find<HTMLInputElement>('[data-test="exam-workspace-save-as-name"]').element.value,
    ).toBe("NO-prov HT25 (kopia)");
    expect(submit(wrapper).element.disabled).toBe(false);
  });

  it("refuses a name another file uses at the field and keeps the dialog open", async () => {
    importsTheFixture(apiMocks);
    apiMocks.copyExamWorkspaceDocument.mockRejectedValue(
      new ApiError({
        code: "VALIDATION_ERROR",
        details: { code: "vault_name_in_use" },
        message: "Name in use",
        status: 422,
      }),
    );
    const wrapper = await mountView();
    await importFixture(wrapper);
    await openSaveAs(wrapper);

    await wrapper.find('[data-test="exam-workspace-save-as"] form').trigger("submit");
    await flushPromises();

    expect(apiMocks.copyExamWorkspaceDocument).toHaveBeenCalledExactlyOnceWith(
      "lineage-1",
      "NO-prov HT25 (kopia)",
      expect.objectContaining({ title: "NO-prov HT25" }),
    );
    expect(wrapper.find('[data-test="exam-workspace-save-as"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-save-as-error"]').text()).toContain(
      "Namnet används redan av en annan fil.",
    );
    expect(submit(wrapper).element.disabled).toBe(true);
    expect(vi.mocked(useToastStore().failure)).not.toHaveBeenCalled();

    await wrapper.find('[data-test="exam-workspace-save-as-name"]').setValue("Annat namn");
    expect(wrapper.find('[data-test="exam-workspace-save-as-error"]').exists()).toBe(false);
    expect(submit(wrapper).element.disabled).toBe(false);

    await wrapper.find('[data-test="exam-workspace-save-as-name"]').setValue("  NO-prov HT25 (kopia) ");
    expect(wrapper.find('[data-test="exam-workspace-save-as-error"]').exists()).toBe(true);
    expect(submit(wrapper).element.disabled).toBe(true);
  });

  it("closes on success, opens the copy and shows no toast", async () => {
    importsTheFixture(apiMocks);
    const copy = buildResponse();
    apiMocks.copyExamWorkspaceDocument.mockResolvedValue({
      ...copy,
      document: { ...copy.document, title: "Kopia av provet" },
      saved_document: { ...copy.saved_document, title: "Kopia av provet" },
      summary: buildSavedExamSummary({
        lineage_id: "lineage-2",
        name: "Provkopia",
        title: "Kopia av provet",
        version: 1,
      }),
    });
    const wrapper = await mountView();
    await importFixture(wrapper);
    await openSaveAs(wrapper);

    await submitName(wrapper, "Provkopia");

    expect(apiMocks.copyExamWorkspaceDocument).toHaveBeenCalledExactlyOnceWith(
      "lineage-1",
      "Provkopia",
      expect.objectContaining({ title: "NO-prov HT25" }),
    );
    expect(wrapper.find('[data-test="exam-workspace-save-as"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe("Kopia av provet");
    const toasts = useToastStore();
    expect(vi.mocked(toasts.failure)).not.toHaveBeenCalled();
    expect(vi.mocked(toasts.success)).not.toHaveBeenCalled();
    expect(vi.mocked(toasts.info)).not.toHaveBeenCalled();
  });
});
