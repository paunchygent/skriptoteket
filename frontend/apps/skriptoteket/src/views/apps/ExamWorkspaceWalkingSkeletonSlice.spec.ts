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

import type { Editor } from "@tiptap/core";
import { DOMWrapper, flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../api/client";
import type {
  ExamWorkspaceConversionStatus,
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
} from "../../api/examWorkspace";
import { useToastStore } from "../../stores/toast";
import {
  buildResponse,
  importFixtureDocument,
  mountExamWorkspace,
  saveDocument,
  selectItemRow,
  type ViewWrapper,
} from "./ExamWorkspaceSlice.specSupport";

import { arrangeStepHistory } from "./ExamWorkspaceHistory.specSupport";

/** Every input of one accepted-answer row list (a gap popover's or the Kort svar Svar field's). */
function answerRowInputs(groupTestId: string): HTMLInputElement[] {
  return Array.from(
    document.querySelectorAll<HTMLInputElement>(`[data-test="${groupTestId}-input"]`),
  );
}

/** The accepted-answer row inputs of one gap in the open popover (teleported to the body). */
function gapRowInputs(gapId: string): HTMLInputElement[] {
  return answerRowInputs(`exam-workspace-gap-values-${gapId}`);
}

/** Type a value into one accepted-answer row and commit the list, as leaving the row does. */
async function commitAnswerRow(groupTestId: string, index: number, value: string): Promise<void> {
  const row = new DOMWrapper(answerRowInputs(groupTestId)[index]!);
  row.element.value = value;
  await row.trigger("input");
  row.element.dispatchEvent(new Event("change", { bubbles: true }));
  await flushPromises();
}

/** Type a value into one gap popover row and commit, as leaving the row does. */
async function commitGapRow(gapId: string, index: number, value: string): Promise<void> {
  await commitAnswerRow(`exam-workspace-gap-values-${gapId}`, index, value);
}

const apiMocks = vi.hoisted(() => ({
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
  downloadExamWorkspaceExport: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  requestExamWorkspaceAnswerMisspellings: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
}));

vi.mock("../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../test/examCourseCatalog")).getExamCourseCatalog,
}));

function lastSavedDocument(): NativeExamDocument {
  const calls = apiMocks.saveExamWorkspaceDocument.mock.calls;
  const [, params] = calls[calls.length - 1] as [
    string,
    { document: NativeExamDocument; expectedRevision: number },
  ];
  return params.document;
}

/** Choose a question type from the list's Ny fråga menu (teleported to the body). */
/**
 * Click a gap in the question text as a user does. jsdom has no layout, so the
 * editor's own click handler is called with the gap as the clicked node.
 */
async function clickGap(wrapper: ViewWrapper, gapId: string): Promise<void> {
  const { editor } = wrapper.get('[data-test="exam-workspace-body-editor-surface"]')
    .element as HTMLElement & { editor: Editor };
  let pos = -1;
  editor.state.doc.descendants((node, nodePos) => {
    if (pos < 0 && node.type.name === "examGap" && node.attrs.gapId === gapId) pos = nodePos;
    return pos < 0;
  });
  const node = editor.state.doc.nodeAt(pos)!;
  editor.view.someProp("handleClickOn", (handler) =>
    handler(editor.view, pos, node, pos, new MouseEvent("click"), true),
  );
  await flushPromises();
}

async function addQuestion(wrapper: ViewWrapper, kind: string) {
  await wrapper.find('[data-test="exam-workspace-new"]').trigger("click");
  document.body.querySelector<HTMLElement>(`[data-test="exam-workspace-new-${kind}"]`)!.click();
  await flushPromises();
}

function rowStatus(wrapper: ViewWrapper, itemId: string): string | undefined {
  return wrapper
    .find(`[data-test="exam-workspace-row-${itemId}"] [role="img"][aria-label$="granskas"], [data-test="exam-workspace-row-${itemId}"] [role="img"][aria-label="Granskad"]`)
    .attributes("aria-label");
}

/** The imported exam with the given items as gap items keyed in two gaps, so one gap can be cleared on its own. */
function buildTwoGapResponse(
  gapItemIds: string[] = ["item_004"],
): ExamWorkspaceDocumentResponse {
  const response = buildResponse({ conversion: succeededConversion, version: 1 });
  return {
    ...response,
    document: {
      ...response.document,
      items: response.document.items.map((item) =>
        gapItemIds.includes(item.item_id)
          ? {
              ...item,
              answer_key: { correct_choice_ids: [], match_pairs: [], origin: "teacher_authored" },
              kind: "gap_fill",
              body: [
                { heading_level: null, segments: [
                    { kind: "text", marks: [], text: "Vatten kokar vid" },
                    { gap_id: "gap_001", kind: "gap" },
                    { kind: "text", marks: [], text: "grader och fryser vid" },
                    { gap_id: "gap_002", kind: "gap" },
                    { kind: "text", marks: [], text: "grader." },
                  ],
                },
              ],
              gaps: [
                { accepted_values: ["100"], automatic_values: [], excluded_automatic_values: [], gap_id: "gap_001", options: [], correct_option_id: null },
                { accepted_values: ["0"], automatic_values: [], excluded_automatic_values: [], gap_id: "gap_002", options: [], correct_option_id: null },
              ],
            }
          : item,
      ),
    },
  };
}

/** The finished import: its poll status, and the conversion its fetched document carries. */
const succeededConversion: ExamWorkspaceConversionStatus = {
  job_id: "job-1", lineage_id: "lineage-1", state: "succeeded", error_message: null, summary: null,
  document_revision: 1, questions_total: 0, questions_done: 0, units: [],
};

beforeEach(() => {
  apiMocks.getExamWorkspaceConversionStatus.mockResolvedValue(succeededConversion);
  apiMocks.getExamWorkspaceDocument.mockReset();
  apiMocks.importExamWorkspaceDocument.mockReset();
  apiMocks.saveExamWorkspaceDocument.mockReset();
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
  window.history.replaceState({}, "", "/");
  document.body.replaceChildren();
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
    expect(wrapper.find('[data-test="exam-workspace-save-state"]').text()).toMatch(/^Sparat /);
  });

  it("marks the workspace as unsaved when the selected item points are edited", async () => {
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_002");
    await wrapper
      .find('[data-test="exam-workspace-item-points-input"]')
      .setValue("5");

    expect(wrapper.find('[data-test="exam-workspace-save-state"]').text()).toBe("Osparat");
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
    expect(wrapper.find('[data-test="exam-workspace-save-state"]').text()).toBe("Osparat");
  });

  it("adds a short answer as a Kort svar with one unkeyed gap after the question text", async () => {
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 2 }));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await addQuestion(wrapper, "short_answer");

    const newRow = wrapper.find('[data-test="exam-workspace-row-item_009"]');
    expect(newRow.text()).toContain("Kort svar");
    await saveDocument(wrapper);

    const [, params] = apiMocks.saveExamWorkspaceDocument.mock.calls[0] as [
      string,
      { document: NativeExamDocument; expectedRevision: number },
    ];
    const added = params.document.items.find((item) => item.item_id === "item_009")!;
    expect(added.kind).toBe("gap_fill");
    expect(added.answer_key.origin).toBe("absent");
    expect(added.body).toEqual([
      { heading_level: null, segments: [{ kind: "gap", gap_id: "gap_001" }] },
    ]);
    expect(added.gaps).toEqual([
      { gap_id: "gap_001", accepted_values: [], automatic_values: [], excluded_automatic_values: [], options: [], correct_option_id: null },
    ]);
    expect(added.points).toBeNull();
  });

  it("a Kort svar shows only Fråga and Svar and saves a one-gap Lucktext", async () => {
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 2 }));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await addQuestion(wrapper, "short_answer");

    expect(wrapper.find('[data-test="exam-workspace-row-item_009"]').text()).toContain("Kort svar");
    expect(wrapper.find('[data-test="exam-workspace-type"]').text()).toContain("Kort svar");
    expect(wrapper.find('[data-test="exam-workspace-short-answer"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-body-editor"]').exists()).toBe(false);

    const surface = wrapper.get('[data-test="exam-workspace-short-answer-question"]')
      .element as HTMLElement & { editor: Editor };
    surface.editor.commands.insertContent("Vad heter Sveriges huvudstad?");
    await flushPromises();
    const svarRow = wrapper.find<HTMLInputElement>(
      '[data-test="exam-workspace-short-answer-values-input"]',
    );
    svarRow.element.value = "Stockholm";
    await svarRow.trigger("input");
    svarRow.element.dispatchEvent(new Event("change", { bubbles: true }));
    await flushPromises();

    await saveDocument(wrapper);

    const added = lastSavedDocument().items.find((item) => item.item_id === "item_009")!;
    expect(added.kind).toBe("gap_fill");
    expect(added.body).toEqual([
      { heading_level: null, segments: [{ kind: "text", marks: [], text: "Vad heter Sveriges huvudstad?" }] },
      { heading_level: null, segments: [{ gap_id: "gap_001", kind: "gap" }] },
    ]);
    expect(added.gaps[0]?.accepted_values).toEqual(["Stockholm"]);
  });

  it("a new Lucktext saves empty and shows the Frågetext editor with the Lucka button", async () => {
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 2 }));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await addQuestion(wrapper, "gap_fill");

    expect(wrapper.find('[data-test="exam-workspace-row-item_009"]').text()).toContain("Lucktext");
    expect(wrapper.find('[data-test="exam-workspace-short-answer"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-body-editor"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-body-editor"]').text()).toContain("Frågetext");
    expect(wrapper.find('[data-test="exam-workspace-toolbar-make-gap"]').exists()).toBe(true);

    await saveDocument(wrapper);

    const added = lastSavedDocument().items.find((item) => item.item_id === "item_009")!;
    expect(added.kind).toBe("gap_fill");
    expect(added.body).toEqual([]);
    expect(added.gaps).toEqual([]);
  });

  it("saves with the bumped client-side revision and the previous expected revision", async () => {
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 2 }));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_002");
    await wrapper
      .find('[data-test="exam-workspace-item-points-input"]')
      .setValue("5");
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
    expect(savedItem?.points).toBe(5);
    expect(wrapper.find('[data-test="exam-workspace-save-state"]').text()).toMatch(/^Sparat /);
    expect(vi.mocked(useToastStore().success)).not.toHaveBeenCalled();
  });

  it("marks a machine-proposed answer key as reviewed_advisory when the item is marked reviewed", async () => {
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 2 }));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_003");
    expect(wrapper.find('[data-test="exam-workspace-review"]').attributes("aria-pressed")).toBe("false");
    await wrapper.find('[data-test="exam-workspace-review"]').trigger("click");

    expect(wrapper.find('[data-test="exam-workspace-review"]').attributes("aria-pressed")).toBe("true");
    expect(rowStatus(wrapper, "item_003")).toBe("Granskad");

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

    const savedDocument = lastSavedDocument();
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
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 2 }));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_003");
    await wrapper.find('[data-test="exam-workspace-choice-correct-choice_001"]').setValue(false);
    await wrapper.find('[data-test="exam-workspace-choice-correct-choice_002"]').setValue(false);

    await selectItemRow(wrapper, "item_004");
    await clickGap(wrapper, "gap_001");
    await commitGapRow("gap_001", 0, "  ");

    await saveDocument(wrapper);

    const savedDocument = lastSavedDocument();
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

    expect(apiMocks.saveExamWorkspaceDocument).not.toHaveBeenCalled();
    expect(vi.mocked(useToastStore().failure)).toHaveBeenCalledWith(
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
    const choiceA = wrapper.find('[data-test="exam-workspace-choice-correct-choice_001"]');
    await choiceA.setValue(false);
    await wrapper.find('[data-test="exam-workspace-choice-correct-choice_002"]').setValue(false);
    await choiceA.setValue(true);

    await selectItemRow(wrapper, "item_004");
    await clickGap(wrapper, "gap_001");
    await commitGapRow("gap_001", 0, "");
    await commitGapRow("gap_001", 0, "100");

    await saveDocument(wrapper);

    const savedDocument = lastSavedDocument();
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
      .find('[data-test="exam-workspace-item-points-input"]')
      .setValue("5");
    await saveDocument(wrapper);

    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledWith("lineage-1");
    expect(wrapper.find('[data-test="exam-workspace-conflict-notice"]').text()).toContain(
      "ändrades någon annanstans",
    );
    expect(wrapper.find('[data-test="exam-workspace-title"]').text()).toBe("Serverversion av provet");
    expect(wrapper.find('[data-test="exam-workspace-save-state"]').text()).toMatch(/^Sparat /);
  });

  it("offers Spara and Spara som in the save menu, and no reload of the saved version", async () => {
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await wrapper.find('[data-test="exam-workspace-save-menu"]').trigger("click");

    const menu = document.body.querySelector<HTMLElement>('[role="menu"]')!;
    expect(Array.from(menu.querySelectorAll('[role="menuitem"]')).map((entry) => entry.textContent?.trim()))
      .toEqual([expect.stringContaining("Spara"), "Spara som …"]);
    expect(menu.textContent).not.toContain("Läs in på nytt");
  });
});
