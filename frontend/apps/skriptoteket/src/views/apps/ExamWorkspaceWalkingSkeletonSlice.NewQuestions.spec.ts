/**
 * Exam workspace walking-skeleton slice: new questions.
 *
 * Slice purpose:
 *   Lock how a teacher adds Kort svar and Lucktext questions: a new Kort svar
 *   starts as one unkeyed gap after the question text, shows only Frågetext
 *   and Godkända svar, and saves as a one-gap Lucktext; a new Lucktext saves
 *   empty and shows the Frågetext editor with the Lucka button.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { saveExamWorkspaceDocument } from "../../api/examWorkspace";
import {
  buildResponse,
  importFixtureDocument,
  mountExamWorkspace,
  saveDocument,
} from "./ExamWorkspaceSlice.specSupport";
import {
  addQuestion,
  firstSaveRequest,
  lastSavedDocument,
  shortAnswerEditor,
  succeededConversion,
} from "./ExamWorkspaceWalkingSkeletonSlice.specSupport";

import { arrangeStepHistory } from "./ExamWorkspaceHistory.specSupport";

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
  saveExamWorkspaceDocument: vi.fn<typeof saveExamWorkspaceDocument>(),
}));

vi.mock("../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../test/examCourseCatalog")).getExamCourseCatalog,
}));

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

describe("ExamWorkspaceView walking skeleton slice: new questions", () => {
  it("adds a short answer as a Kort svar with one unkeyed gap after the question text", async () => {
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 2 }));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await addQuestion(wrapper, "short_answer");

    const newRow = wrapper.find('[data-test="exam-workspace-row-item_009"]');
    expect(newRow.text()).toContain("Kort svar");
    await saveDocument(wrapper);

    const { params } = firstSaveRequest(apiMocks.saveExamWorkspaceDocument);
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

  it("a Kort svar shows only Frågetext and Godkända svar and saves a one-gap Lucktext", async () => {
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildResponse({ version: 2 }));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await addQuestion(wrapper, "short_answer");

    expect(wrapper.find('[data-test="exam-workspace-row-item_009"]').text()).toContain("Kort svar");
    expect(wrapper.find('[data-test="exam-workspace-type"]').text()).toContain("Kort svar");
    expect(wrapper.find('[data-test="exam-workspace-short-answer"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="exam-workspace-body-editor"]').exists()).toBe(false);

    shortAnswerEditor(wrapper).commands.insertContent("Vad heter Sveriges huvudstad?");
    await flushPromises();
    const svarRow = wrapper.find<HTMLInputElement>(
      '[data-test="exam-workspace-short-answer-values-input"]',
    );
    svarRow.element.value = "Stockholm";
    await svarRow.trigger("input");
    svarRow.element.dispatchEvent(new Event("change", { bubbles: true }));
    await flushPromises();

    await saveDocument(wrapper);

    const added = lastSavedDocument(apiMocks.saveExamWorkspaceDocument).items.find((item) => item.item_id === "item_009")!;
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

    const added = lastSavedDocument(apiMocks.saveExamWorkspaceDocument).items.find((item) => item.item_id === "item_009")!;
    expect(added.kind).toBe("gap_fill");
    expect(added.body).toEqual([]);
    expect(added.gaps).toEqual([]);
  });
});
