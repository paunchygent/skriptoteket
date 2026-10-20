/**
 * AI suggestions that arrive while Spara som is in flight (TASK-SKRIPT-39-04-07).
 *
 * Expected behavior:
 *   Each arrival has one effect: the P12/P13 transition, run once against
 *   the copy in front of the teacher. A failed Spara som leaves that copy,
 *   so nothing runs again. Its response opens the sent document as the new
 *   exam; an arrival the response was built without stays on the exam it
 *   was copied from. Dirty is true only when the copy differs from the
 *   saved document.
 */

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  ExamWorkspaceDocumentResponse,
  NativeAnswerKeySuggestion,
  NativeExamItem,
} from "../../../api/examWorkspace";
import { buildMatchingItem } from "./examWorkspaceMatchingItem.specSupport";
import {
  currentDocument,
  currentItem,
  deferred,
  type DocumentState,
  openingOf,
  openMatchingDocument as openWith,
  openMatchingDocumentWithFence as openWithFence,
  savedResponse,
} from "./useExamWorkspaceDocument.specSupport";
import type { SyncFence } from "./examWorkspaceSyncFence";

const apiMocks = vi.hoisted(() => ({
  getExamWorkspaceConversionStatus: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  copyExamWorkspaceDocument: vi.fn(),
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
  apiMocks.copyExamWorkspaceDocument.mockReset();
});

function openMatchingDocument(item?: NativeExamItem) {
  return openWith(apiMocks.getExamWorkspaceDocument, item);
}

/**
 * Drive Spara som at document level the way the replacement coordinator
 * does: start the copy candidate and install a settled response, so arrivals
 * that land mid-copy replay onto it. A rejected copy leaves the working copy
 * as the failed Spara som does.
 */
async function startCopyInstall(state: DocumentState, fence: SyncFence): Promise<void> {
  const lineageId = state.summary.value?.lineage_id;
  if (lineageId === undefined || lineageId === null) {
    throw new Error("expected an open exam");
  }
  const posting = state.beginCopy(lineageId, "Kopia");
  if (posting === null) {
    throw new Error("expected the copy to start");
  }
  try {
    const response = await posting;
    state.installReplacementDocument(fence.begin(), response);
  } catch {
    return;
  }
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
  return apiMocks.copyExamWorkspaceDocument.mock.calls[0][2];
}

describe("arriving suggestions during Spara som", () => {

  it("does not downgrade a source key equal to the arriving suggestion when Spara som fails", async () => {
    const { fence, state } = await openWithFence(apiMocks.getExamWorkspaceDocument);
    const pendingSave = deferred<ExamWorkspaceDocumentResponse>();
    apiMocks.copyExamWorkspaceDocument.mockReturnValue(pendingSave.promise);
    const suggestion = matchingSuggestion(SOURCE_PAIRS);

    const copying = startCopyInstall(state, fence);
    state.applyArrivingSuggestions(openingOf(state), [{ item_id: "item_001", suggestion }]);
    pendingSave.reject(new Error("network down"));
    await copying;

    expect(currentItem(state).ai_suggestion).toEqual(suggestion);
    expect(currentItem(state).answer_key.origin).toBe("source_provided");
    expect(currentItem(state).review.state).toBe("review_complete");
    expect(state.isDirty.value).toBe(true);
  });

  it("A4/A5: an arrival that changes nothing on the returned revision leaves it clean", async () => {
    const { fence, state } = await openWithFence(apiMocks.getExamWorkspaceDocument);
    const pendingSave = deferred<ExamWorkspaceDocumentResponse>();
    apiMocks.copyExamWorkspaceDocument.mockReturnValue(pendingSave.promise);
    const suggestion = matchingSuggestion(SOURCE_PAIRS);

    const copying = startCopyInstall(state, fence);
    state.applyArrivingSuggestions(openingOf(state), [{ item_id: "item_001", suggestion }]);
    const sent = sentDocument();
    pendingSave.resolve(
      savedResponse({
        ...sent,
        items: [{ ...currentItem(state), ai_suggestion: matchingSuggestion(SOURCE_PAIRS) }],
      }),
    );
    await copying;

    expect(currentItem(state).ai_suggestion).toEqual(suggestion);
    expect(currentItem(state).answer_key.origin).toBe("source_provided");
    expect(currentItem(state).review.state).toBe("review_complete");
    expect(state.isDirty.value).toBe(false);
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
    const { fence, state } = await openWithFence(
      apiMocks.getExamWorkspaceDocument,
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
    apiMocks.copyExamWorkspaceDocument.mockReturnValue(pendingSave.promise);

    const copying = startCopyInstall(state, fence);
    state.applyArrivingSuggestions(openingOf(state), [
      { item_id: "item_001", suggestion: matchingSuggestion(SOURCE_PAIRS) },
    ]);
    expect(currentItem(state).answer_key.origin).toBe("machine_proposed");
    return { pendingSave, copying, state };
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



  it("A15: after a failed Spara som, which leaves the single effect in place", async () => {
    const { pendingSave, copying, state } = await clearKeyThenSaveWhileSuggestionReturns();

    pendingSave.reject(new Error("network down"));
    await copying;

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
