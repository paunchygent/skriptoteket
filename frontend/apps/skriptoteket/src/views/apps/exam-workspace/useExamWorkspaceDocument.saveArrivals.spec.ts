/**
 * AI suggestions that arrive while a save is in flight (TASK-SKRIPT-39-04-07).
 *
 * Expected behavior:
 *   Each arrival has one effect: the P12/P13 transition, run once against
 *   the copy in front of the teacher. A failed save leaves that copy, so
 *   nothing runs again. A save response or a conflict reload replaces the
 *   copy with a document built without the arrivals that landed during the
 *   save. Those arrivals, and only those, run once more, in arrival order,
 *   against the replacing document. Which arrivals run again depends on when
 *   they arrived, never on whether the replacing document stores an equal
 *   older suggestion. Dirty is true only when the copy differs from the last
 *   server document.
 *
 * Rows follow case space A in the retained design note
 * `evidence/implementation/TASK-SKRIPT-39-04-07/repair3/design.md`.
 */

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import type {
  ExamWorkspaceDocumentResponse,
  NativeAnswerKeySuggestion,
  NativeExamItem,
} from "../../../api/examWorkspace";
import { buildMatchingItem } from "./examWorkspaceMatchingItem.specSupport";
import {
  buildResponse,
  currentDocument,
  currentItem,
  deferred,
  openingOf,
  openMatchingDocument as openWith,
  savedResponse,
} from "./useExamWorkspaceDocument.specSupport";

const apiMocks = vi.hoisted(() => ({
  getExamWorkspaceConversionStatus: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
}));
const exportApiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
}));

vi.mock("../../../api/examWorkspaceExports", () => exportApiMocks);
vi.mock("../../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../../test/examCourseCatalog")).getExamCourseCatalog,
}));

beforeEach(() => {
  setActivePinia(createPinia());
  apiMocks.getExamWorkspaceDocument.mockReset();
  apiMocks.saveExamWorkspaceDocument.mockReset();
});

function openMatchingDocument(item?: NativeExamItem) {
  return openWith(apiMocks.getExamWorkspaceDocument, item);
}

function matchingSuggestion(pairs: Array<[string, string]>): NativeAnswerKeySuggestion {
  return {
    correct_choice_ids: [],
    fingerprint: "a".repeat(64),
    gap_accepted_values: [],
    match_pairs: pairs.map(([left_id, right_id]) => ({ left_id, right_id })),
    model: "model",
    prompt_template_version: "v1",
    provider_profile_id: "profile",
  };
}

const SOURCE_PAIRS: Array<[string, string]> = [
  ["left_001", "right_002"],
  ["left_002", "right_001"],
  ["left_003", "right_003"],
];
const FIRST_PAIRS: Array<[string, string]> = [
  ["left_001", "right_001"],
  ["left_002", "right_002"],
  ["left_003", "right_003"],
];
const SECOND_PAIRS: Array<[string, string]> = [
  ["left_001", "right_003"],
  ["left_002", "right_002"],
  ["left_003", "right_001"],
];

function sentDocument() {
  return apiMocks.saveExamWorkspaceDocument.mock.calls[0][1].document;
}

describe("arriving suggestions during a save", () => {
  it("keeps a suggestion that arrives while the save is in flight and stays dirty", async () => {
    const state = await openMatchingDocument();
    const pendingSave = deferred<ExamWorkspaceDocumentResponse>();
    apiMocks.saveExamWorkspaceDocument.mockReturnValue(pendingSave.promise);
    const suggestion = matchingSuggestion([["left_001", "right_001"]]);

    state.updateItemPoints("item_001", 7);
    const saving = state.saveDocument("position-1");
    state.applyArrivingSuggestions(openingOf(state), [{ item_id: "item_001", suggestion }]);
    expect(currentItem(state).ai_suggestion).toEqual(suggestion);

    expect(sentDocument().items[0].ai_suggestion ?? null).toBeNull();
    pendingSave.resolve(savedResponse(sentDocument()));
    await saving;

    expect(currentItem(state).ai_suggestion).toEqual(suggestion);
    expect(currentItem(state).answer_key.origin).toBe("source_provided");
    expect(state.isDirty.value).toBe(true);
  });

  it("does not downgrade a source key equal to the arriving suggestion when the save fails", async () => {
    const state = await openMatchingDocument();
    const pendingSave = deferred<ExamWorkspaceDocumentResponse>();
    apiMocks.saveExamWorkspaceDocument.mockReturnValue(pendingSave.promise);
    const suggestion = matchingSuggestion(SOURCE_PAIRS);

    const saving = state.saveDocument("position-1");
    state.applyArrivingSuggestions(openingOf(state), [{ item_id: "item_001", suggestion }]);
    pendingSave.reject(new Error("network down"));
    await saving;

    expect(currentItem(state).ai_suggestion).toEqual(suggestion);
    expect(currentItem(state).answer_key.origin).toBe("source_provided");
    expect(currentItem(state).review.state).toBe("review_complete");
    expect(state.isDirty.value).toBe(true);
  });

  it("A4/A5: an arrival that changes nothing on the returned revision leaves it clean", async () => {
    const state = await openMatchingDocument();
    const pendingSave = deferred<ExamWorkspaceDocumentResponse>();
    apiMocks.saveExamWorkspaceDocument.mockReturnValue(pendingSave.promise);
    const suggestion = matchingSuggestion(SOURCE_PAIRS);

    const saving = state.saveDocument("position-1");
    state.applyArrivingSuggestions(openingOf(state), [{ item_id: "item_001", suggestion }]);
    const sent = sentDocument();
    pendingSave.resolve(
      savedResponse({
        ...sent,
        items: [{ ...currentItem(state), ai_suggestion: matchingSuggestion(SOURCE_PAIRS) }],
      }),
    );
    await saving;

    expect(currentItem(state).ai_suggestion).toEqual(suggestion);
    expect(currentItem(state).answer_key.origin).toBe("source_provided");
    expect(currentItem(state).review.state).toBe("review_complete");
    expect(state.isDirty.value).toBe(false);
  });

  async function saveWhileTwoArrivalsLand(
    keyPairs: Array<[string, string]>,
    origin: NativeExamItem["answer_key"]["origin"],
    reviewState: NativeExamItem["review"]["state"],
    previousPairs: Array<[string, string]>,
  ) {
    const item = buildMatchingItem({
      ai_suggestion: matchingSuggestion(previousPairs),
      answer_key: {
        correct_choice_ids: [],
        match_pairs: keyPairs.map(([left_id, right_id]) => ({ left_id, right_id })),
        origin,
      },
    });
    const state = await openMatchingDocument({
      ...item,
      review: { ...item.review, state: reviewState },
    });
    const pendingSave = deferred<ExamWorkspaceDocumentResponse>();
    apiMocks.saveExamWorkspaceDocument.mockReturnValue(pendingSave.promise);

    const saving = state.saveDocument("position-1");
    state.applyArrivingSuggestions(openingOf(state), [
      { item_id: "item_001", suggestion: matchingSuggestion(FIRST_PAIRS) },
    ]);
    state.applyArrivingSuggestions(openingOf(state), [
      { item_id: "item_001", suggestion: matchingSuggestion(SECOND_PAIRS) },
    ]);
    pendingSave.resolve(savedResponse(sentDocument()));
    await saving;
    return state;
  }

  it("replays two arrivals in order and keeps a teacher key equal to the first (P12)", async () => {
    const state = await saveWhileTwoArrivalsLand(FIRST_PAIRS, "teacher_authored", "review_complete", [
      ["left_001", "right_001"],
      ["left_002", "right_003"],
      ["left_003", "right_002"],
    ]);

    expect(currentItem(state).ai_suggestion).toEqual(matchingSuggestion(SECOND_PAIRS));
    expect(currentItem(state).answer_key.origin).toBe("teacher_authored");
    expect(currentItem(state).answer_key.match_pairs).toEqual(
      matchingSuggestion(FIRST_PAIRS).match_pairs,
    );
    expect(currentItem(state).review.state).toBe("review_complete");
    expect(state.isDirty.value).toBe(true);
  });

  it("replays two arrivals in order, each following an unreviewed machine key", async () => {
    const state = await saveWhileTwoArrivalsLand(
      SOURCE_PAIRS,
      "machine_proposed",
      "review_required",
      SOURCE_PAIRS,
    );

    expect(currentItem(state).ai_suggestion).toEqual(matchingSuggestion(SECOND_PAIRS));
    expect(currentItem(state).answer_key.origin).toBe("machine_proposed");
    expect(currentItem(state).answer_key.match_pairs).toEqual(
      matchingSuggestion(SECOND_PAIRS).match_pairs,
    );
    expect(currentItem(state).review.state).toBe("review_required");
    expect(state.isDirty.value).toBe(true);
  });

  it("A6: replays every arrival although the returned revision stores an older suggestion equal to the last", async () => {
    const state = await saveWhileTwoArrivalsLand([], "absent", "review_complete", SECOND_PAIRS);

    expect(currentItem(state).ai_suggestion).toEqual(matchingSuggestion(SECOND_PAIRS));
    expect(currentItem(state).answer_key.origin).toBe("machine_proposed");
    expect(currentItem(state).answer_key.match_pairs).toEqual(
      matchingSuggestion(SECOND_PAIRS).match_pairs,
    );
    expect(currentItem(state).review.state).toBe("review_required");
    expect(state.isDirty.value).toBe(true);
  });

  it("reapplies an arrival onto the revision reloaded after a conflict", async () => {
    const state = await openMatchingDocument();
    const pendingSave = deferred<ExamWorkspaceDocumentResponse>();
    apiMocks.saveExamWorkspaceDocument.mockReturnValue(pendingSave.promise);
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(buildResponse());
    const suggestion = matchingSuggestion([["left_001", "right_001"]]);

    const saving = state.saveDocument("position-1");
    state.applyArrivingSuggestions(openingOf(state), [{ item_id: "item_001", suggestion }]);
    pendingSave.reject(new ApiError({ code: "CONFLICT", message: "Konflikt", status: 409 }));
    await saving;

    expect(currentItem(state).ai_suggestion).toEqual(suggestion);
    expect(currentItem(state).answer_key.origin).toBe("source_provided");
    expect(state.isDirty.value).toBe(true);
  });
});

describe("a newly promoted key survives a revision that stores an equal older suggestion (F8)", () => {
  /**
   * The reviewer's scenario: a reviewed key with its kept suggestion S is
   * cleared, so the key is absent and S stays. During the save, S arrives
   * again and becomes the key. The replacing document still holds the
   * absent key beside the older S.
   */
  async function clearKeyThenSaveWhileSuggestionReturns() {
    const kept = matchingSuggestion(SOURCE_PAIRS);
    const state = await openMatchingDocument(
      buildMatchingItem({
        ai_suggestion: kept,
        answer_key: {
          correct_choice_ids: [],
          match_pairs: kept.match_pairs,
          origin: "reviewed_advisory",
        },
      }),
    );
    state.updateItemMatchPairs("item_001", []);
    expect(currentItem(state).answer_key.origin).toBe("absent");
    const pendingSave = deferred<ExamWorkspaceDocumentResponse>();
    apiMocks.saveExamWorkspaceDocument.mockReturnValue(pendingSave.promise);

    const saving = state.saveDocument("position-1");
    state.applyArrivingSuggestions(openingOf(state), [
      { item_id: "item_001", suggestion: matchingSuggestion(SOURCE_PAIRS) },
    ]);
    expect(currentItem(state).answer_key.origin).toBe("machine_proposed");
    return { pendingSave, saving, state };
  }

  function expectPromoted(state: Awaited<ReturnType<typeof openMatchingDocument>>) {
    expect(currentItem(state).ai_suggestion).toEqual(matchingSuggestion(SOURCE_PAIRS));
    expect(currentItem(state).answer_key).toEqual({
      correct_choice_ids: [],
      match_pairs: matchingSuggestion(SOURCE_PAIRS).match_pairs,
      origin: "machine_proposed",
    });
    expect(currentItem(state).review.state).toBe("review_required");
    expect(state.isDirty.value).toBe(true);
  }

  it("A3: after a successful save", async () => {
    const { pendingSave, saving, state } = await clearKeyThenSaveWhileSuggestionReturns();

    pendingSave.resolve(savedResponse(sentDocument()));
    await saving;

    expectPromoted(state);
  });

  it("A12: after a conflict reload", async () => {
    const { pendingSave, saving, state } = await clearKeyThenSaveWhileSuggestionReturns();
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(savedResponse(sentDocument()));

    pendingSave.reject(new ApiError({ code: "CONFLICT", message: "Konflikt", status: 409 }));
    await saving;

    expectPromoted(state);
  });

  it("A15: after a failed save, which leaves the single effect in place", async () => {
    const { pendingSave, saving, state } = await clearKeyThenSaveWhileSuggestionReturns();

    pendingSave.reject(new Error("network down"));
    await saving;

    expectPromoted(state);
  });
});

describe("dirty state follows real change (I2)", () => {
  it("A22: an arrival that changes nothing leaves a clean document clean", async () => {
    const kept = matchingSuggestion(FIRST_PAIRS);
    const state = await openMatchingDocument(buildMatchingItem({ ai_suggestion: kept }));

    state.applyArrivingSuggestions(openingOf(state), [
      { item_id: "item_001", suggestion: matchingSuggestion(FIRST_PAIRS) },
    ]);

    expect(currentDocument(state).items[0].ai_suggestion).toEqual(kept);
    expect(state.isDirty.value).toBe(false);
  });

  it("an arrival that changes the suggestion marks the document dirty", async () => {
    const state = await openMatchingDocument(
      buildMatchingItem({ ai_suggestion: matchingSuggestion(FIRST_PAIRS) }),
    );

    state.applyArrivingSuggestions(openingOf(state), [
      { item_id: "item_001", suggestion: matchingSuggestion(SECOND_PAIRS) },
    ]);

    expect(state.isDirty.value).toBe(true);
  });
});
