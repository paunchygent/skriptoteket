/**
 * Exam workspace save-rule slice.
 *
 * Expected behavior:
 *   Item states the server refuses to save are flagged at the question and
 *   refused locally with Swedish copy naming the questions: points that are
 *   negative or non-finite, and a choice without text. The field is marked
 *   invalid with an inline hint, the question list, the details drawer, and
 *   the Filer readiness list carry the reason, and no save request is sent.
 *   While a save runs, the item editor's inputs are disabled so a typed
 *   edit is not lost when the saved version replaces the document.
 */

import { flushPromises } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ExamWorkspaceConversionStatus, NativeExamDocument } from "../../api/examWorkspace";
import { buildFreeTextItem } from "../../test/examWorkspaceFixtures";
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

async function mountImported() {
  const { wrapper } = await mountExamWorkspace();
  await importFixtureDocument(wrapper);
  return wrapper;
}

/** The finished import: its poll status, and the conversion its fetched document carries. */
const succeededConversion: ExamWorkspaceConversionStatus = {
  job_id: "job-1", lineage_id: "lineage-1", state: "succeeded", error_message: null, summary: null,
  document_revision: 1, questions_total: 0, questions_done: 0, units: [],
};

beforeEach(() => {
  for (const mock of Object.values(apiMocks)) {
    mock.mockReset();
  }
  apiMocks.getExamWorkspaceConversionStatus.mockResolvedValue(succeededConversion);
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [] });
  apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(
      buildResponse({ conversion: succeededConversion, version: 1 }),
    );
    return { job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null, summary: null,
      document_revision: null, questions_total: 0, questions_done: 0, units: [] };
  });
});

describe("ExamWorkspaceView save rules", () => {
  it("flags negative points at the field and in the drawer, and refuses the save", async () => {
    const wrapper = await mountImported();

    await selectItemRow(wrapper, "item_002");
    const points = wrapper.get('[data-test="exam-workspace-item-points-input"]');
    await points.setValue("-1");

    expect(points.attributes("aria-invalid")).toBe("true");
    const hint = wrapper.get('[data-test="exam-workspace-points-hint"]');
    expect(hint.text()).toBe("Poängen kan inte vara negativ.");
    expect(points.attributes("aria-describedby")).toBe(hint.attributes("id"));
    expect(wrapper.get('[data-test="exam-workspace-item-row-item_002"]').text()).toContain(
      "Poängen kan inte vara negativ.",
    );

    await wrapper.get('[data-test="exam-workspace-item-details-toggle"]').trigger("click");
    expect(wrapper.get('[data-test="exam-workspace-item-readiness"]').text()).toContain(
      "Poängen kan inte vara negativ.",
    );

    await saveDocument(wrapper);

    expect(apiMocks.saveExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(vi.mocked(useToastStore().failure)).toHaveBeenCalledWith(
      "Fråga 2 har negativa poäng. Poängen kan inte vara negativ.",
    );
  });

  it("flags negative points in the Filer readiness list", async () => {
    const wrapper = await mountImported();

    await selectItemRow(wrapper, "item_005");
    await wrapper.get('[data-test="exam-workspace-item-points-input"]').setValue("-1");
    await wrapper.get('[data-test="exam-workspace-mode-filer"]').trigger("click");

    expect(
      wrapper.get('[data-test="exam-workspace-readiness-item-item_005"]').text(),
    ).toContain("Poängen kan inte vara negativ.");
  });

  it("flags an empty choice text and refuses the save, naming every question", async () => {
    const { wrapper } = await mountExamWorkspace();
    // The editor restores an emptied paragraph, so an empty choice is a state
    // a stored document carries (a conversion or an arriving revision).
    const response = buildResponse({ conversion: succeededConversion, version: 1 });
    for (const [itemId, choiceId] of [
      ["item_002", "choice_b"],
      ["item_003", "choice_c"],
    ] as const) {
      const choice = response.document.items
        .find((item) => item.item_id === itemId)!
        .choices.find((entry) => entry.choice_id === choiceId)!;
      choice.body = [
        { heading_level: null, segments: [{ kind: "text", marks: [], text: "" }] },
      ];
    }
    apiMocks.getExamWorkspaceDocument.mockReset();
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(response);
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_002");
    const choice = wrapper.get('[data-test="exam-workspace-choice-text-choice_b"]');

    expect(choice.attributes("aria-invalid")).toBe("true");
    const hint = wrapper.get('[data-test="exam-workspace-choice-text-hint"]');
    expect(hint.text()).toBe("Ett svarsalternativ saknar text.");
    expect(choice.attributes("aria-describedby")).toBe(hint.attributes("id"));
    expect(
      wrapper.get('[data-test="exam-workspace-choice-text-choice_a"]').attributes("aria-invalid"),
    ).toBeUndefined();
    // A teacher edit makes the copy dirty, so the save button sends the refused copy.
    await wrapper.get('[data-test="exam-workspace-item-points-input"]').setValue("5");

    await selectItemRow(wrapper, "item_003");
    await saveDocument(wrapper);

    expect(apiMocks.saveExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(vi.mocked(useToastStore().failure)).toHaveBeenCalledWith(
      "Frågorna 2 och 3 har svarsalternativ utan text. Skriv text i varje svarsalternativ.",
    );
  });

  it("accepts zero points at the field and sends the save", async () => {
    const response = buildResponse({ conversion: succeededConversion, version: 1 });
    const document: NativeExamDocument = {
      ...response.document,
      document_id: "00000000-0000-4000-8000-000000000001",
      origin: {
        kind: "docx_import",
        source_filename: "NO_Prov_HT25.docx",
        source_sha256: "a".repeat(64),
        extractor_version: "docx-extractor-1",
      },
      items: [buildFreeTextItem(1), buildFreeTextItem(2)],
    };
    const savedDocument: NativeExamDocument = {
      ...document,
      revision: 2,
      items: document.items.map((item) => item.item_id === "item_002" ? { ...item, points: 0 } : item),
    };
    apiMocks.importExamWorkspaceDocument.mockResolvedValue({
      ...succeededConversion, state: "queued", document_revision: null,
    });
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce({
      ...response, document, saved_document: document,
    });
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue({
      ...response,
      document: savedDocument,
      saved_document: savedDocument,
      summary: { ...response.summary, version: 2 },
    });
    const wrapper = await mountImported();

    await selectItemRow(wrapper, "item_002");
    const points = wrapper.get('[data-test="exam-workspace-item-points-input"]');
    await points.setValue("0");

    expect(points.attributes("aria-invalid")).toBeUndefined();
    expect(wrapper.find('[data-test="exam-workspace-points-hint"]').exists()).toBe(false);
    await saveDocument(wrapper);

    expect(apiMocks.saveExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(apiMocks.saveExamWorkspaceDocument).toHaveBeenCalledWith(
      "lineage-1",
      expect.objectContaining({
        document: expect.objectContaining({
          items: expect.arrayContaining([expect.objectContaining({ item_id: "item_002", points: 0 })]),
        }),
      }),
    );
  });

  it("saves again once the refused fields are corrected", async () => {
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 2 }));
    const wrapper = await mountImported();

    await selectItemRow(wrapper, "item_002");
    const points = wrapper.get('[data-test="exam-workspace-item-points-input"]');
    await points.setValue("-1");
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
    await wrapper.get('[data-test="exam-workspace-item-points-input"]').setValue("7");
    await wrapper.get('[data-test="exam-workspace-save"]').trigger("click");
    await flushPromises();

    for (const testId of [
      "exam-workspace-item-points-input",
      "exam-workspace-choice-text-choice_a",
      "exam-workspace-choice-correct-choice_a",
    ]) {
      const control = wrapper.get(`[data-test="${testId}"]`);
      if (testId === "exam-workspace-choice-text-choice_a") {
        expect(control.attributes("contenteditable")).toBe("false");
      } else {
        expect(control.attributes("disabled")).toBeDefined();
      }
    }
    expect(wrapper.findComponent(ExamWorkspaceBodyEditor).props("disabled")).toBe(true);

    resolveSave(buildResponse({ version: 2 }));
    await flushPromises();

    expect(
      wrapper.get('[data-test="exam-workspace-item-points-input"]').attributes("disabled"),
    ).toBeUndefined();
    expect(wrapper.findComponent(ExamWorkspaceBodyEditor).props("disabled")).toBe(false);
  });
});
