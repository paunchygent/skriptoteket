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

import { DOMWrapper, flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useToastStore } from "../../stores/toast";
import {
  buildResponse,
  importFixtureDocument,
  mountExamWorkspace,
  saveDocument,
  selectItemRow,
  unmountExamWorkspace,
} from "./ExamWorkspaceSlice.specSupport";
import {
  addQuestion,
  buildTwoGapResponse,
  clickGap,
  clickWord,
  commitGapRow,
  firstStoreRequest,
  gapRowInputs,
  lastStoredDocument,
  rowStatus,
  succeededConversion,
} from "./ExamWorkspaceWalkingSkeletonSlice.specSupport";

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
  requestExamWorkspaceAnswerMisspellings: vi.fn(),
}));
const exportApiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
}));

vi.mock("../../api/examWorkspaceExports", () => exportApiMocks);
vi.mock("../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../test/examCourseCatalog")).getExamCourseCatalog,
}));

beforeEach(() => {
  apiMocks.getExamWorkspaceConversionStatus.mockResolvedValue(succeededConversion);
  apiMocks.getExamWorkspaceDocument.mockReset();
  apiMocks.importExamWorkspaceDocument.mockReset();
  apiMocks.storeExamWorkspaceUndoStep.mockReset();
  arrangeStepHistory(apiMocks);
  apiMocks.listExamWorkspaceDocuments.mockReset();
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [], ordering: "course" });
  apiMocks.requestExamWorkspaceAnswerMisspellings.mockReset();
  apiMocks.requestExamWorkspaceAnswerMisspellings.mockResolvedValue({ automatic_values: [] });
  apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(
      buildResponse({ conversion: succeededConversion, version: 1 }),
    );
    return { job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null, summary: null,
      document_revision: null, questions_total: 0, questions_done: 0, units: [] };
  });
});

afterEach(() => {
  unmountExamWorkspace();
});

describe("ExamWorkspaceView walking skeleton slice", () => {
  it("shows the extracted items with Swedish type labels and review status after import", async () => {
    const { wrapper } = await mountExamWorkspace();

    await importFixtureDocument(wrapper);

    expect(wrapper.findAll('[data-test^="exam-workspace-row-"]')).toHaveLength(8);
    expect(wrapper.text()).toContain("Fritext");
    expect(wrapper.text()).toContain("Flerval: ett val");
    expect(wrapper.text()).toContain("Flerval: flera val");
    expect(wrapper.text()).toContain("Lucktext");
    expect(rowStatus(wrapper, "item_003")).toBe("Behöver granskas");
    expect(rowStatus(wrapper, "item_001")).toBe("Granskad");
    expect(wrapper.find('[data-test="exam-workspace-item-editor"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-save-state"]').text()).toBe("Sparat");
  });

  it("marks the workspace as unsaved when the selected item points are edited", async () => {
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_002");
    await wrapper
      .find('[data-test="exam-workspace-item-points-input"]')
      .setValue("5");

    expect(wrapper.find('[data-test="exam-workspace-save-state"]').text()).toBe("Sparar …");
    expect(wrapper.find('[data-test="exam-workspace-row-item_002"]').text()).toContain(
      "Fråga 2",
    );
  });

  it("adds a new free-text question with the next free item id after the selected question", async () => {
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await addQuestion(wrapper, "free_text");

    expect(wrapper.findAll('[data-test^="exam-workspace-row-"]')).toHaveLength(9);
    const newRow = wrapper.find('[data-test="exam-workspace-row-item_009"]');
    expect(newRow.exists()).toBe(true);
    expect(newRow.text()).toContain("Fritext");
    expect(wrapper.find('[data-test="exam-workspace-item-editor"]').text()).toContain(
      "Fråga 2",
    );
    // A structural add stores at once.
    expect(wrapper.find('[data-test="exam-workspace-save-state"]').text()).toMatch(/^Sparat /);
  });

  it("stores the pending edit as a step without bumping the revision", async () => {
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_002");
    await wrapper
      .find('[data-test="exam-workspace-item-points-input"]')
      .setValue("5");
    expect(wrapper.find('[data-test="exam-workspace-save-state"]').text()).toBe("Sparar …");
    await saveDocument(wrapper);

    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(1);
    const { lineageId, params } = firstStoreRequest(apiMocks.storeExamWorkspaceUndoStep);
    expect(lineageId).toBe("lineage-1");
    expect(params.document.revision).toBe(1);
    const savedItem = params.document.items.find((item) => item.item_id === "item_002");
    expect(savedItem?.points).toBe(5);
    expect(wrapper.find('[data-test="exam-workspace-save-state"]').text()).toMatch(/^Sparat /);
    expect(vi.mocked(useToastStore().success)).not.toHaveBeenCalled();
  });

  it("marks a machine-proposed answer key as reviewed_advisory when the item is marked reviewed", async () => {
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_003");
    expect(wrapper.find('[data-test="exam-workspace-review"]').attributes("aria-pressed")).toBe("false");
    await wrapper.find('[data-test="exam-workspace-review"]').trigger("click");

    expect(wrapper.find('[data-test="exam-workspace-review"]').attributes("aria-pressed")).toBe("true");
    expect(rowStatus(wrapper, "item_003")).toBe("Granskad");

    await saveDocument(wrapper);

    const savedItem = lastStoredDocument(apiMocks.storeExamWorkspaceUndoStep).items.find(
      (item) => item.item_id === "item_003",
    );
    expect(savedItem?.review.state).toBe("review_complete");
    expect(savedItem?.answer_key.origin).toBe("reviewed_advisory");
  });

  it("stores teacher answer-key edits as teacher_authored for choices and gaps", async () => {
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_002");
    await wrapper
      .find('[data-test="exam-workspace-choice-correct-choice_002"]')
      .setValue(true);

    await selectItemRow(wrapper, "item_004");
    await clickGap(wrapper, "gap_001");
    const firstRow = new DOMWrapper(gapRowInputs("gap_001")[0]!);
    firstRow.element.value = "hundra";
    await firstRow.trigger("input");
    await new DOMWrapper(
      document.querySelector<HTMLButtonElement>(
        '[data-test="exam-workspace-gap-values-gap_001-add"]',
      )!,
    ).trigger("click");
    await flushPromises();
    expect(gapRowInputs("gap_001")).toHaveLength(2);
    await commitGapRow("gap_001", 1, "100");

    await saveDocument(wrapper);

    const savedDocument = lastStoredDocument(apiMocks.storeExamWorkspaceUndoStep);
    const choiceItem = savedDocument.items.find((item) => item.item_id === "item_002");
    expect(choiceItem?.answer_key).toEqual({
      correct_choice_ids: ["choice_002"],
      match_pairs: [],
      origin: "teacher_authored",
    });
    const gapItem = savedDocument.items.find((item) => item.item_id === "item_004");
    expect(gapItem?.answer_key.origin).toBe("teacher_authored");
    expect(gapItem?.gaps[0]?.accepted_values).toEqual(["hundra", "100"]);
  });

  it("makes the answer key absent when the teacher clears every key value", async () => {
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_003");
    await wrapper.find('[data-test="exam-workspace-choice-correct-choice_001"]').setValue(false);
    await wrapper.find('[data-test="exam-workspace-choice-correct-choice_002"]').setValue(false);

    await selectItemRow(wrapper, "item_004");
    await clickGap(wrapper, "gap_001");
    await commitGapRow("gap_001", 0, "  ");

    await saveDocument(wrapper);

    const savedDocument = lastStoredDocument(apiMocks.storeExamWorkspaceUndoStep);
    const choiceItem = savedDocument.items.find((item) => item.item_id === "item_003");
    expect(choiceItem?.answer_key).toEqual({ correct_choice_ids: [], match_pairs: [], origin: "absent" });
    const gapItem = savedDocument.items.find((item) => item.item_id === "item_004");
    expect(gapItem?.answer_key.origin).toBe("absent");
    expect(gapItem?.gaps[0]?.accepted_values).toEqual([]);
  });

  it("refuses to save a gap item keyed in only some gaps and says why in Swedish", async () => {
    apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
      apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(buildTwoGapResponse());
      return { job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null, summary: null,
      document_revision: null, questions_total: 0, questions_done: 0, units: [] };
    });
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_004");
    await clickGap(wrapper, "gap_002");
    await commitGapRow("gap_002", 0, "");

    expect(wrapper.find('[data-test="exam-workspace-gap-key-hint"]').text()).toContain(
      "lämna alla luckor tomma",
    );
    await saveDocument(wrapper);

    expect(apiMocks.storeExamWorkspaceUndoStep).not.toHaveBeenCalled();
    expect(vi.mocked(useToastStore().failure)).not.toHaveBeenCalled();
    expect(wrapper.find('[data-test="exam-workspace-save-state"]').text()).toBe("Inte sparat");
    expect(wrapper.find('[data-test="exam-workspace-save-state"]').attributes("title")).toBe(
      "Fråga 4 saknar godkända svar i vissa luckor. Fyll i godkända svar för varje lucka, eller lämna alla luckor tomma om frågan ska sakna facit.",
    );
  });

  it("names every partially keyed gap item in the plural refusal copy", async () => {
    apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
      apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(buildTwoGapResponse(["item_004", "item_005"]));
      return { job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null, summary: null,
      document_revision: null, questions_total: 0, questions_done: 0, units: [] };
    });
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    for (const itemId of ["item_004", "item_005"]) {
      await selectItemRow(wrapper, itemId);
      await clickGap(wrapper, "gap_002");
      await commitGapRow("gap_002", 0, "");
    }

    await saveDocument(wrapper);

    // The in-between snapshot was still fully keyed, so it stored; the final
    // draft refuses and is held with its reason, without a toast.
    expect(apiMocks.storeExamWorkspaceUndoStep).toHaveBeenCalledTimes(1);
    expect(vi.mocked(useToastStore().failure)).not.toHaveBeenCalled();
    expect(wrapper.find('[data-test="exam-workspace-save-state"]').text()).toBe("Inte sparat");
    expect(wrapper.find('[data-test="exam-workspace-save-state"]').attributes("title")).toContain(
      "saknar godkända svar i vissa luckor",
    );
  });

  it("returns the answer key to teacher_authored when cleared key values are filled in again", async () => {
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_003");
    const choiceA = wrapper.find('[data-test="exam-workspace-choice-correct-choice_001"]');
    await choiceA.setValue(false);
    await wrapper.find('[data-test="exam-workspace-choice-correct-choice_002"]').setValue(false);
    await choiceA.setValue(true);

    await selectItemRow(wrapper, "item_004");
    await clickGap(wrapper, "gap_001");
    await commitGapRow("gap_001", 0, "");
    await commitGapRow("gap_001", 0, "100");

    await saveDocument(wrapper);

    const savedDocument = lastStoredDocument(apiMocks.storeExamWorkspaceUndoStep);
    const choiceItem = savedDocument.items.find((item) => item.item_id === "item_003");
    expect(choiceItem?.answer_key).toEqual({
      correct_choice_ids: ["choice_001"],
      match_pairs: [],
      origin: "teacher_authored",
    });
    const gapItem = savedDocument.items.find((item) => item.item_id === "item_004");
    expect(gapItem?.answer_key.origin).toBe("teacher_authored");
    expect(gapItem?.gaps[0]?.accepted_values).toEqual(["100"]);
  });


  it("offers only Spara som in the save menu, and no reload of the saved version", async () => {
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await wrapper.find('[data-test="exam-workspace-save-menu"]').trigger("click");

    const menu = document.body.querySelector<HTMLElement>('[role="menu"]')!;
    expect(Array.from(menu.querySelectorAll('[role="menuitem"]')).map((entry) => entry.textContent?.trim()))
      .toEqual(["Spara som …"]);
    expect(menu.textContent).not.toContain("Läs in på nytt");
  });

  it("makes two gaps with the gap tool and no popover, then turns it off with Escape", async () => {
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_004");
    await wrapper.find('[data-test="exam-workspace-toolbar-gap-tool"]').trigger("click");
    expect(
      wrapper.find('[data-test="exam-workspace-toolbar-gap-tool"]').attributes("aria-pressed"),
    ).toBe("true");

    await clickWord(wrapper, "kokar");
    await clickWord(wrapper, "grader");
    await flushPromises();

    expect(document.querySelector('[data-test="exam-workspace-gap-popover"]')).toBeNull();

    wrapper.get('[data-test="exam-workspace-body-editor-surface"]').element.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }),
    );
    await flushPromises();
    expect(
      wrapper.find('[data-test="exam-workspace-toolbar-gap-tool"]').attributes("aria-pressed"),
    ).toBe("false");

    await saveDocument(wrapper);

    const gapItem = lastStoredDocument(apiMocks.storeExamWorkspaceUndoStep).items.find(
      (item) => item.item_id === "item_004",
    );
    // `withNewGap` keeps the gap records in body order: the clicked words sit
    // around the imported gap_001.
    expect(gapItem?.gaps.map((gap) => gap.gap_id)).toEqual(["gap_002", "gap_001", "gap_003"]);
    expect(gapItem?.gaps.map((gap) => gap.accepted_values)).toEqual([["kokar"], ["100"], ["grader"]]);
  });
});
