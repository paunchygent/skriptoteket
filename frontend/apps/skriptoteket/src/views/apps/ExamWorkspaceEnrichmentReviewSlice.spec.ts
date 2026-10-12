/**
 * Exam workspace answer-key proposal review decisions.
 *
 * Slice purpose:
 *   Lock the review half of the advisory answer-key loop: let the teacher
 *   approve, adjust, or dismiss a proposal shown next to its item.
 *
 * Expected behavior:
 *   Approving unchanged saves the key as `reviewed_advisory` and leaves the
 *   item's review state as it was; adjusting it in the editor saves it as
 *   `teacher_authored`. A dismissed proposal never reaches the document.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  buildUnkeyedResponse,
  lastSavedItem,
  resetEnrichmentApiMocks,
  SUCCEEDED,
} from "./ExamWorkspaceEnrichmentSlice.specSupport";
import {
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
  getExamWorkspaceConversionStatus: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
  startExamWorkspaceEnrichment: vi.fn(),
}));

vi.mock("../../api/examWorkspace", () => apiMocks);

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  resetEnrichmentApiMocks(apiMocks);
});

afterEach(() => {
  vi.useRealTimers();
});

describe("ExamWorkspaceView answer-key proposal review decisions", () => {
  it("saves an unchanged approved proposal as reviewed_advisory without completing review", async () => {
    apiMocks.getExamWorkspaceEnrichment.mockResolvedValue(SUCCEEDED);
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildUnkeyedResponse(2));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_002");
    await wrapper.find('[data-test="exam-workspace-proposal-approve"]').trigger("click");

    expect(wrapper.find('[data-test="exam-workspace-proposal-panel"]').exists()).toBe(false);
    expect(
      wrapper.find('[data-test="exam-workspace-item-status-item_002"]').text(),
    ).toContain("Behöver granskas");

    await saveDocument(wrapper);

    const saved = lastSavedItem(apiMocks.saveExamWorkspaceDocument, "item_002");
    expect(saved?.answer_key).toEqual({
      correct_choice_ids: ["choice_c"],
      match_pairs: [],
      origin: "reviewed_advisory",
    });
    expect(saved?.review).toEqual({
      confidence: 0.9,
      parse_origin: "deterministic",
      reasons: ["facit saknas"],
      state: "review_required",
    });
  });

  it("keeps parse-confidence review required after approving a proposal", async () => {
    const parseReviewResponse = buildUnkeyedResponse(1);
    parseReviewResponse.document.items = parseReviewResponse.document.items.map((item) =>
      item.item_id === "item_002"
        ? {
            ...item,
            review: {
              ...item.review,
              reasons: ["sublines_without_answer_keys"],
              state: "review_required",
            },
          }
        : item,
    );
    apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
      apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(parseReviewResponse);
      return { job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null,
      document_revision: null, questions_total: 0, questions_done: 0, units: [] };
    });
    apiMocks.getExamWorkspaceEnrichment.mockResolvedValue(SUCCEEDED);
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildUnkeyedResponse(2));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_002");
    await wrapper.find('[data-test="exam-workspace-proposal-approve"]').trigger("click");
    await saveDocument(wrapper);

    const saved = lastSavedItem(apiMocks.saveExamWorkspaceDocument, "item_002");
    expect(saved?.answer_key.origin).toBe("reviewed_advisory");
    expect(saved?.review.state).toBe("review_required");
    expect(saved?.review.reasons).toEqual(["sublines_without_answer_keys"]);
  });

  it("saves an adjusted proposal as teacher_authored", async () => {
    apiMocks.getExamWorkspaceEnrichment.mockResolvedValue(SUCCEEDED);
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildUnkeyedResponse(2));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_002");
    await wrapper.find('[data-test="exam-workspace-proposal-edit"]').trigger("click");
    expect(
      wrapper
        .find<HTMLInputElement>('[data-test="exam-workspace-choice-correct-choice_c"]')
        .element.checked,
    ).toBe(true);
    expect(
      wrapper.find('[data-test="exam-workspace-item-status-item_002"]').text(),
    ).toContain("Behöver granskas");

    await wrapper.find('[data-test="exam-workspace-choice-correct-choice_a"]').setValue(true);
    await wrapper.find('[data-test="exam-workspace-mark-reviewed"]').trigger("click");
    await saveDocument(wrapper);

    const saved = lastSavedItem(apiMocks.saveExamWorkspaceDocument, "item_002");
    expect(saved?.answer_key).toEqual({
      correct_choice_ids: ["choice_a"],
      match_pairs: [],
      origin: "teacher_authored",
    });
    expect(saved?.review.state).toBe("review_complete");
  });

  it("keeps a dismissed proposal out of the document", async () => {
    apiMocks.getExamWorkspaceEnrichment.mockResolvedValue(SUCCEEDED);
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_002");
    await wrapper.find('[data-test="exam-workspace-proposal-dismiss"]').trigger("click");

    expect(wrapper.find('[data-test="exam-workspace-proposal-panel"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-dirty-pill"]').exists()).toBe(false);
  });
});
