/**
 * Exam workspace save-rule slice.
 *
 * Expected behavior:
 *   Item states the server refuses to save are flagged at the question and
 *   refused locally with Swedish copy naming the questions: points that are
 *   not greater than zero, and a choice without text. The field is marked
 *   invalid with an inline hint, the question list, the details drawer, and
 *   the Filer readiness list carry the reason, and no save request is sent.
 *   While a save runs, the item editor's inputs are disabled so a typed
 *   edit is not lost when the saved version replaces the document.
 */

import { flushPromises } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useToastStore } from "../../stores/toast";
import ExamWorkspaceBodyEditor from "./exam-workspace/ExamWorkspaceBodyEditor.vue";
import {
  buildResponse,
  importFixtureDocument,
  mountExamWorkspace,
  saveDocument,
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

async function mountImported() {
  const { wrapper } = await mountExamWorkspace();
  await importFixtureDocument(wrapper);
  return wrapper;
}

beforeEach(() => {
  for (const mock of Object.values(apiMocks)) {
    mock.mockReset();
  }
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [] });
  apiMocks.getExamWorkspaceEnrichment.mockResolvedValue({
    document_revision: 1,
    lineage_id: "lineage-1",
    proposals: [],
    state: "not_requested",
  });
  apiMocks.importExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 1 }));
});

describe("ExamWorkspaceView save rules", () => {
  it("flags points of zero at the field and in the drawer, and refuses the save", async () => {
    const wrapper = await mountImported();

    await selectItemRow(wrapper, "item_002");
    const points = wrapper.get('[data-test="exam-workspace-item-points-input"]');
    await points.setValue("0");

    expect(points.attributes("aria-invalid")).toBe("true");
    const hint = wrapper.get('[data-test="exam-workspace-points-hint"]');
    expect(hint.text()).toBe("Poängen måste vara större än noll.");
    expect(points.attributes("aria-describedby")).toBe(hint.attributes("id"));
    expect(wrapper.get('[data-test="exam-workspace-item-row-item_002"]').text()).toContain(
      "Poängen måste vara större än noll.",
    );

    await wrapper.get('[data-test="exam-workspace-item-details-toggle"]').trigger("click");
    expect(wrapper.get('[data-test="exam-workspace-item-readiness"]').text()).toContain(
      "Poängen måste vara större än noll.",
    );

    await saveDocument(wrapper);

    expect(apiMocks.saveExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(vi.mocked(useToastStore().failure)).toHaveBeenCalledWith(
      "Fråga 2 har noll eller negativa poäng. Poängen måste vara större än noll.",
    );
  });

  it("flags negative points in the Filer readiness list", async () => {
    const wrapper = await mountImported();

    await selectItemRow(wrapper, "item_005");
    await wrapper.get('[data-test="exam-workspace-item-points-input"]').setValue("-1");
    await wrapper.get('[data-test="exam-workspace-mode-filer"]').trigger("click");

    expect(
      wrapper.get('[data-test="exam-workspace-readiness-item-item_005"]').text(),
    ).toContain("Poängen måste vara större än noll.");
  });

  it("flags an empty choice text and refuses the save, naming every question", async () => {
    const wrapper = await mountImported();

    await selectItemRow(wrapper, "item_002");
    const choice = wrapper.get('[data-test="exam-workspace-choice-text-choice_b"]');
    await choice.setValue("");

    expect(choice.attributes("aria-invalid")).toBe("true");
    const hint = wrapper.get('[data-test="exam-workspace-choice-text-hint"]');
    expect(hint.text()).toBe("Ett svarsalternativ saknar text.");
    expect(choice.attributes("aria-describedby")).toBe(hint.attributes("id"));
    expect(
      wrapper.get('[data-test="exam-workspace-choice-text-choice_a"]').attributes("aria-invalid"),
    ).toBeUndefined();

    await selectItemRow(wrapper, "item_003");
    await wrapper.get('[data-test="exam-workspace-choice-text-choice_c"]').setValue("");
    await saveDocument(wrapper);

    expect(apiMocks.saveExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(vi.mocked(useToastStore().failure)).toHaveBeenCalledWith(
      "Frågorna 2 och 3 har svarsalternativ utan text. Skriv text i varje svarsalternativ.",
    );
  });

  it("saves again once the refused fields are corrected", async () => {
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 2 }));
    const wrapper = await mountImported();

    await selectItemRow(wrapper, "item_002");
    const points = wrapper.get('[data-test="exam-workspace-item-points-input"]');
    await points.setValue("0");
    await points.setValue("3");
    await saveDocument(wrapper);

    expect(apiMocks.saveExamWorkspaceDocument).toHaveBeenCalledTimes(1);
  });

  it("disables the item editor's inputs while a save runs", async () => {
    let resolveSave: (value: ReturnType<typeof buildResponse>) => void = () => {};
    apiMocks.saveExamWorkspaceDocument.mockReturnValue(
      new Promise((resolve) => {
        resolveSave = resolve;
      }),
    );
    const wrapper = await mountImported();

    await selectItemRow(wrapper, "item_002");
    await wrapper.get('[data-test="exam-workspace-item-title-input"]').setValue("Ny rubrik");
    await wrapper.get('[data-test="exam-workspace-save"]').trigger("click");
    await flushPromises();

    for (const testId of [
      "exam-workspace-item-title-input",
      "exam-workspace-item-points-input",
      "exam-workspace-choice-text-choice_a",
      "exam-workspace-choice-correct-choice_a",
    ]) {
      expect(wrapper.get(`[data-test="${testId}"]`).attributes("disabled")).toBeDefined();
    }
    expect(wrapper.findComponent(ExamWorkspaceBodyEditor).props("disabled")).toBe(true);

    resolveSave(buildResponse({ version: 2 }));
    await flushPromises();

    expect(
      wrapper.get('[data-test="exam-workspace-item-title-input"]').attributes("disabled"),
    ).toBeUndefined();
    expect(wrapper.findComponent(ExamWorkspaceBodyEditor).props("disabled")).toBe(false);
  });
});
