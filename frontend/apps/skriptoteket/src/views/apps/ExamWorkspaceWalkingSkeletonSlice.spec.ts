/**
 * Exam workspace walking-skeleton slice behavior.
 *
 * Slice purpose:
 *   Lock the end-to-end teacher loop: import a .docx exam, review extracted
 *   items, edit the selected item, add a new question, save a versioned
 *   revision, recover from a stale-save conflict, and reload the latest saved
 *   version.
 *
 * Expected behavior:
 *   Saving bumps the document revision client-side and sends the previous
 *   revision as `expected_revision`. A 409 shows Swedish conflict handling and
 *   reloads the latest saved version. Teacher answer-key edits become
 *   `teacher_authored`; clearing every key value makes the key `absent`; a
 *   gap item keyed in only some gaps is refused locally with Swedish copy;
 *   marking a machine proposal as reviewed becomes `reviewed_advisory`.
 */

import { flushPromises } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../api/client";
import type { ExamWorkspaceDocumentResponse, NativeExamDocument } from "../../api/examWorkspace";
import { useToastStore } from "../../stores/toast";
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

function lastSavedDocument(): NativeExamDocument {
  const calls = apiMocks.saveExamWorkspaceDocument.mock.calls;
  const [, params] = calls[calls.length - 1] as [
    string,
    { document: NativeExamDocument; expectedRevision: number },
  ];
  return params.document;
}

/** The given items as gap items keyed in two gaps, so one gap can be cleared on its own. */
function buildTwoGapResponse(
  gapItemIds: string[] = ["item_004"],
): ExamWorkspaceDocumentResponse {
  const response = buildResponse({ version: 1 });
  return {
    ...response,
    document: {
      ...response.document,
      items: response.document.items.map((item) =>
        gapItemIds.includes(item.item_id)
          ? {
              ...item,
              answer_key: { correct_choice_ids: [], origin: "teacher_authored" },
              kind: "gap_fill",
              body: [
                {
                  segments: [
                    { kind: "text", text: "Vatten kokar vid" },
                    { gap_id: "gap_001", kind: "gap" },
                    { kind: "text", text: "grader och fryser vid" },
                    { gap_id: "gap_002", kind: "gap" },
                    { kind: "text", text: "grader." },
                  ],
                },
              ],
              gaps: [
                { accepted_values: ["100"], gap_id: "gap_001", hint: null },
                { accepted_values: ["0"], gap_id: "gap_002", hint: null },
              ],
            }
          : item,
      ),
    },
  };
}

beforeEach(() => {
  apiMocks.getExamWorkspaceDocument.mockReset();
  apiMocks.importExamWorkspaceDocument.mockReset();
  apiMocks.saveExamWorkspaceDocument.mockReset();
  apiMocks.listExamWorkspaceDocuments.mockReset();
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [] });
  apiMocks.getExamWorkspaceEnrichment.mockReset();
  apiMocks.getExamWorkspaceEnrichment.mockResolvedValue({
    document_revision: 1,
    lineage_id: "lineage-1",
    proposals: [],
    state: "not_requested",
  });
  apiMocks.importExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 1 }));
});

describe("ExamWorkspaceView walking skeleton slice", () => {
  it("shows the extracted items with Swedish type labels and review status after import", async () => {
    const { wrapper } = await mountExamWorkspace();

    await importFixtureDocument(wrapper);

    expect(wrapper.findAll('[data-test^="exam-workspace-item-row-"]')).toHaveLength(8);
    expect(wrapper.text()).toContain("Fritext");
    expect(wrapper.text()).toContain("Flerval: ett val");
    expect(wrapper.text()).toContain("Flerval: flera val");
    expect(wrapper.text()).toContain("Lucktext");
    expect(
      wrapper.find('[data-test="exam-workspace-item-status-item_003"]').text(),
    ).toContain("Behöver granskas");
    expect(
      wrapper.find('[data-test="exam-workspace-item-status-item_001"]').text(),
    ).toContain("Granskad");
    expect(wrapper.find('[data-test="exam-workspace-item-editor"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-dirty-pill"]').exists()).toBe(false);
  });

  it("marks the workspace as unsaved when the selected item title is edited", async () => {
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_002");
    await wrapper
      .find('[data-test="exam-workspace-item-title-input"]')
      .setValue("Helt ny rubrik");

    expect(wrapper.find('[data-test="exam-workspace-dirty-pill"]').text()).toBe("Osparat");
    expect(wrapper.find('[data-test="exam-workspace-item-row-item_002"]').text()).toContain(
      "Helt ny rubrik",
    );
  });

  it("adds a new teacher-created free-text question with the next free item id", async () => {
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await wrapper.find('[data-test="exam-workspace-add-item"]').trigger("click");

    expect(wrapper.findAll('[data-test^="exam-workspace-item-row-"]')).toHaveLength(9);
    const newRow = wrapper.find('[data-test="exam-workspace-item-row-item_009"]');
    expect(newRow.exists()).toBe(true);
    expect(newRow.text()).toContain("Fritext");
    expect(wrapper.find('[data-test="exam-workspace-item-editor"]').text()).toContain(
      "Fråga 9",
    );
    expect(wrapper.find('[data-test="exam-workspace-dirty-pill"]').exists()).toBe(true);
  });

  it("saves with the bumped client-side revision and the previous expected revision", async () => {
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 2 }));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_002");
    await wrapper
      .find('[data-test="exam-workspace-item-title-input"]')
      .setValue("Helt ny rubrik");
    await saveDocument(wrapper);

    expect(apiMocks.saveExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    const [lineageId, params] = apiMocks.saveExamWorkspaceDocument.mock.calls[0] as [
      string,
      { document: NativeExamDocument; expectedRevision: number },
    ];
    expect(lineageId).toBe("lineage-1");
    expect(params.expectedRevision).toBe(1);
    expect(params.document.revision).toBe(2);
    const savedItem = params.document.items.find((item) => item.item_id === "item_002");
    expect(savedItem?.title).toBe("Helt ny rubrik");
    expect(wrapper.find('[data-test="exam-workspace-dirty-pill"]').exists()).toBe(false);
    expect(wrapper.text()).toContain("Version 2");
  });

  it("marks a machine-proposed answer key as reviewed_advisory when the item is marked reviewed", async () => {
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 2 }));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_003");
    await wrapper.find('[data-test="exam-workspace-mark-reviewed"]').trigger("click");

    expect(
      wrapper.find('[data-test="exam-workspace-item-status-item_003"]').text(),
    ).toContain("Granskad");

    await saveDocument(wrapper);

    const savedItem = lastSavedDocument().items.find(
      (item) => item.item_id === "item_003",
    );
    expect(savedItem?.review.state).toBe("review_complete");
    expect(savedItem?.answer_key.origin).toBe("reviewed_advisory");
  });

  it("stores teacher answer-key edits as teacher_authored for choices and gaps", async () => {
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 2 }));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_002");
    await wrapper
      .find('[data-test="exam-workspace-choice-correct-choice_b"]')
      .setValue(true);

    await selectItemRow(wrapper, "item_004");
    const gapInput = wrapper.find('[data-test="exam-workspace-gap-values-gap_001"]');
    await gapInput.setValue("hundra, 100");
    await gapInput.trigger("change");

    await saveDocument(wrapper);

    const savedDocument = lastSavedDocument();
    const choiceItem = savedDocument.items.find((item) => item.item_id === "item_002");
    expect(choiceItem?.answer_key).toEqual({
      correct_choice_ids: ["choice_b"],
      origin: "teacher_authored",
    });
    const gapItem = savedDocument.items.find((item) => item.item_id === "item_004");
    expect(gapItem?.answer_key.origin).toBe("teacher_authored");
    expect(gapItem?.gaps[0]?.accepted_values).toEqual(["hundra", "100"]);
  });

  it("makes the answer key absent when the teacher clears every key value", async () => {
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 2 }));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_003");
    await wrapper.find('[data-test="exam-workspace-choice-correct-choice_a"]').setValue(false);
    await wrapper.find('[data-test="exam-workspace-choice-correct-choice_b"]').setValue(false);

    await selectItemRow(wrapper, "item_004");
    const gapInput = wrapper.find('[data-test="exam-workspace-gap-values-gap_001"]');
    await gapInput.setValue("  ");
    await gapInput.trigger("change");

    await saveDocument(wrapper);

    const savedDocument = lastSavedDocument();
    const choiceItem = savedDocument.items.find((item) => item.item_id === "item_003");
    expect(choiceItem?.answer_key).toEqual({ correct_choice_ids: [], origin: "absent" });
    const gapItem = savedDocument.items.find((item) => item.item_id === "item_004");
    expect(gapItem?.answer_key.origin).toBe("absent");
    expect(gapItem?.gaps[0]?.accepted_values).toEqual([]);
  });

  it("refuses to save a gap item keyed in only some gaps and says why in Swedish", async () => {
    apiMocks.importExamWorkspaceDocument.mockResolvedValue(buildTwoGapResponse());
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_004");
    const gapInput = wrapper.find('[data-test="exam-workspace-gap-values-gap_002"]');
    await gapInput.setValue("");
    await gapInput.trigger("change");

    expect(wrapper.find('[data-test="exam-workspace-gap-key-hint"]').text()).toContain(
      "lämna alla luckor tomma",
    );
    await saveDocument(wrapper);

    expect(apiMocks.saveExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(vi.mocked(useToastStore().failure)).toHaveBeenCalledWith(
      "Fråga 4 saknar godkända svar i vissa luckor. Fyll i godkända svar för varje lucka, eller lämna alla luckor tomma om frågan ska sakna facit.",
    );
  });

  it("names every partially keyed gap item in the plural refusal copy", async () => {
    apiMocks.importExamWorkspaceDocument.mockResolvedValue(
      buildTwoGapResponse(["item_004", "item_005"]),
    );
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    for (const itemId of ["item_004", "item_005"]) {
      await selectItemRow(wrapper, itemId);
      const gapInput = wrapper.find('[data-test="exam-workspace-gap-values-gap_002"]');
      await gapInput.setValue("");
      await gapInput.trigger("change");
    }

    await saveDocument(wrapper);

    expect(apiMocks.saveExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(vi.mocked(useToastStore().failure)).toHaveBeenCalledWith(
      "Frågorna 4 och 5 saknar godkända svar i vissa luckor. Fyll i godkända svar för varje lucka, eller lämna alla luckor tomma om frågan ska sakna facit.",
    );
  });

  it("returns the answer key to teacher_authored when cleared key values are filled in again", async () => {
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 2 }));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_003");
    const choiceA = wrapper.find('[data-test="exam-workspace-choice-correct-choice_a"]');
    await choiceA.setValue(false);
    await wrapper.find('[data-test="exam-workspace-choice-correct-choice_b"]').setValue(false);
    await choiceA.setValue(true);

    await selectItemRow(wrapper, "item_004");
    const gapInput = wrapper.find('[data-test="exam-workspace-gap-values-gap_001"]');
    await gapInput.setValue("");
    await gapInput.trigger("change");
    await gapInput.setValue("100");
    await gapInput.trigger("change");

    await saveDocument(wrapper);

    const savedDocument = lastSavedDocument();
    const choiceItem = savedDocument.items.find((item) => item.item_id === "item_003");
    expect(choiceItem?.answer_key).toEqual({
      correct_choice_ids: ["choice_a"],
      origin: "teacher_authored",
    });
    const gapItem = savedDocument.items.find((item) => item.item_id === "item_004");
    expect(gapItem?.answer_key.origin).toBe("teacher_authored");
    expect(gapItem?.gaps[0]?.accepted_values).toEqual(["100"]);
  });

  it("maps a stale save to Swedish conflict handling and reloads the latest version", async () => {
    apiMocks.saveExamWorkspaceDocument.mockRejectedValue(
      new ApiError({
        code: "CONFLICT_STALE_REVISION",
        message: "Stale revision",
        status: 409,
      }),
    );
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(
      buildResponse({ title: "Serverversion av provet", version: 2 }),
    );
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_002");
    await wrapper
      .find('[data-test="exam-workspace-item-title-input"]')
      .setValue("Helt ny rubrik");
    await saveDocument(wrapper);

    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledWith("lineage-1");
    expect(wrapper.find('[data-test="exam-workspace-conflict-notice"]').text()).toContain(
      "ändrades någon annanstans",
    );
    expect(wrapper.text()).toContain("Serverversion av provet");
    expect(wrapper.text()).toContain("Version 2");
    expect(wrapper.find('[data-test="exam-workspace-dirty-pill"]').exists()).toBe(false);
  });

  it("reloads the latest saved version on request", async () => {
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(
      buildResponse({ title: "Uppdaterat prov", version: 1 }),
    );
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await wrapper.find('[data-test="exam-workspace-reload"]').trigger("click");
    await flushPromises();

    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledWith("lineage-1");
    expect(wrapper.text()).toContain("Uppdaterat prov");
  });
});
