/**
 * Saved exam list merge rules.
 *
 * Purpose:
 *   Lock how a fetched saved-exam list merges into entries already known
 *   locally, so an import or save that lands while the list request is in
 *   flight is never dropped or rolled back to an older version.
 */

import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { effectScope } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceDocumentSummary,
  NativeAnswerKeySuggestion,
  NativeExamItem,
} from "../../../api/examWorkspace";
import { buildMatchingItem } from "./examWorkspaceMatchingItem.specSupport";
import { mergeSavedDocuments, useExamWorkspaceDocument } from "./useExamWorkspaceDocument";

const apiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
}));

vi.mock("../../../api/examWorkspace", () => apiMocks);

function summary(lineageId: string, version: number): ExamWorkspaceDocumentSummary {
  return {
    lineage_id: lineageId,
    name: `${lineageId}.provdokument.zip`,
    saved_at: "2026-10-09T08:00:00Z",
    vault_file_id: `file-${lineageId}-${version}`,
    version,
  };
}

describe("mergeSavedDocuments", () => {
  it("keeps local entries the response does not know about", () => {
    const merged = mergeSavedDocuments([summary("imported", 1)], [summary("older", 2)]);

    expect(merged.map((entry) => entry.lineage_id)).toEqual(["imported", "older"]);
  });

  it("keeps a newer local version over the fetched one", () => {
    const merged = mergeSavedDocuments([summary("exam", 3)], [summary("exam", 2)]);

    expect(merged).toEqual([summary("exam", 3)]);
  });

  it("takes the fetched entry when it is as new or newer", () => {
    const merged = mergeSavedDocuments([summary("exam", 2)], [summary("exam", 4)]);

    expect(merged).toEqual([summary("exam", 4)]);
  });
});

function buildResponse(item: NativeExamItem = buildMatchingItem()): ExamWorkspaceDocumentResponse {
  return {
    conversion: null,
    document: {
      assets: [],
      document_id: "doc-1",
      instructions: [],
      items: [item],
      origin: {
        extractor_version: "docx-extractor-1",
        kind: "docx_import",
        source_filename: "english-1.docx",
        source_sha256: "abc123",
      },
      parents: [],
      revision: 1,
      schema_version: "native_exam_document_v1",
      title: "English 1",
    },
    notes: [],
    summary: {
      lineage_id: "lineage-1",
      name: "english-1.provdokument.zip",
      saved_at: "2026-10-11T08:00:00Z",
      vault_file_id: "file-1",
      version: 1,
    },
  };
}

async function openMatchingDocument(item?: NativeExamItem) {
  apiMocks.getExamWorkspaceDocument.mockResolvedValue(buildResponse(item));
  const state = effectScope().run(() => useExamWorkspaceDocument());
  if (!state) {
    throw new Error("expected the document state to be created");
  }
  await state.openDocument("lineage-1");
  await flushPromises();
  return state;
}

function currentItem(state: Awaited<ReturnType<typeof openMatchingDocument>>) {
  const item = state.workspaceDocument.value?.items[0];
  if (!item) {
    throw new Error("expected a loaded matching item");
  }
  return item;
}

beforeEach(() => {
  setActivePinia(createPinia());
  apiMocks.getExamWorkspaceDocument.mockReset();
  apiMocks.saveExamWorkspaceDocument.mockReset();
});

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((pendingResolve, pendingReject) => {
    resolve = pendingResolve;
    reject = pendingReject;
  });
  return { promise, reject, resolve };
}

describe("arriving suggestions during a save", () => {
  it("keeps a suggestion that arrives while the save is in flight and stays dirty", async () => {
    const state = await openMatchingDocument();
    const pendingSave = deferred<ExamWorkspaceDocumentResponse>();
    apiMocks.saveExamWorkspaceDocument.mockReturnValue(pendingSave.promise);
    const suggestion: NativeAnswerKeySuggestion = {
      correct_choice_ids: [],
      fingerprint: "a".repeat(64),
      gap_accepted_values: [],
      match_pairs: [{ left_id: "left_001", right_id: "right_001" }],
      model: "model",
      prompt_template_version: "v1",
      provider_profile_id: "profile",
    };

    state.updateItemTitle("item_001", "Ändrad titel");
    const saving = state.saveDocument();
    state.applyArrivingSuggestions([{ item_id: "item_001", suggestion }]);
    expect(currentItem(state).ai_suggestion).toEqual(suggestion);

    const savedDocument = apiMocks.saveExamWorkspaceDocument.mock.calls[0][1].document;
    expect(savedDocument.items[0].ai_suggestion ?? null).toBeNull();
    pendingSave.resolve({
      ...buildResponse(),
      document: savedDocument,
      summary: { ...buildResponse().summary, version: 2 },
    });
    await saving;

    expect(currentItem(state).ai_suggestion).toEqual(suggestion);
    expect(currentItem(state).answer_key.origin).toBe("source_provided");
    expect(state.isDirty.value).toBe(true);
  });

  function matchingSuggestion(
    pairs: Array<[string, string]>,
  ): NativeAnswerKeySuggestion {
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

  it("does not downgrade a source key equal to the arriving suggestion when the save fails", async () => {
    const state = await openMatchingDocument();
    const pendingSave = deferred<ExamWorkspaceDocumentResponse>();
    apiMocks.saveExamWorkspaceDocument.mockReturnValue(pendingSave.promise);
    const suggestion = matchingSuggestion(SOURCE_PAIRS);

    const saving = state.saveDocument();
    state.applyArrivingSuggestions([{ item_id: "item_001", suggestion }]);
    pendingSave.reject(new Error("network down"));
    await saving;

    expect(currentItem(state).ai_suggestion).toEqual(suggestion);
    expect(currentItem(state).answer_key.origin).toBe("source_provided");
    expect(currentItem(state).review.state).toBe("review_complete");
    expect(state.isDirty.value).toBe(true);
  });

  it("does not reapply an arrival the returned revision already contains", async () => {
    const state = await openMatchingDocument();
    const pendingSave = deferred<ExamWorkspaceDocumentResponse>();
    apiMocks.saveExamWorkspaceDocument.mockReturnValue(pendingSave.promise);
    const suggestion = matchingSuggestion(SOURCE_PAIRS);

    const saving = state.saveDocument();
    state.applyArrivingSuggestions([{ item_id: "item_001", suggestion }]);
    const alreadySaved = JSON.parse(
      JSON.stringify(state.workspaceDocument.value),
    ) as ExamWorkspaceDocumentResponse["document"];
    pendingSave.resolve({
      ...buildResponse(),
      document: alreadySaved,
      summary: { ...buildResponse().summary, version: 2 },
    });
    await saving;

    expect(currentItem(state).ai_suggestion).toEqual(suggestion);
    expect(currentItem(state).answer_key.origin).toBe("source_provided");
    expect(currentItem(state).review.state).toBe("review_complete");
    expect(state.isDirty.value).toBe(false);
  });

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

    const saving = state.saveDocument();
    state.applyArrivingSuggestions([
      { item_id: "item_001", suggestion: matchingSuggestion(FIRST_PAIRS) },
    ]);
    state.applyArrivingSuggestions([
      { item_id: "item_001", suggestion: matchingSuggestion(SECOND_PAIRS) },
    ]);
    const savedDocument = apiMocks.saveExamWorkspaceDocument.mock.calls[0][1].document;
    pendingSave.resolve({
      ...buildResponse(),
      document: savedDocument,
      summary: { ...buildResponse().summary, version: 2 },
    });
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
    const previousPairs: Array<[string, string]> = [
      ["left_001", "right_002"],
      ["left_002", "right_001"],
      ["left_003", "right_003"],
    ];
    const state = await saveWhileTwoArrivalsLand(
      previousPairs,
      "machine_proposed",
      "review_required",
      previousPairs,
    );

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

    const saving = state.saveDocument();
    state.applyArrivingSuggestions([{ item_id: "item_001", suggestion }]);
    pendingSave.reject(
      new ApiError({ code: "CONFLICT", message: "Konflikt", status: 409 }),
    );
    await saving;

    expect(currentItem(state).ai_suggestion).toEqual(suggestion);
    expect(currentItem(state).answer_key.origin).toBe("source_provided");
    expect(state.isDirty.value).toBe(true);
  });
});

describe("matching edits in useExamWorkspaceDocument", () => {
  it("changes only the named entry text on its own side", async () => {
    const state = await openMatchingDocument();

    state.updateItemMatchEntryText("item_001", "left", "left_002", "being locked up");
    state.updateItemMatchEntryText("item_001", "right", "right_003", "contempt");

    const item = currentItem(state);
    expect(item.match_left.map((entry) => entry.text)).toEqual([
      "absence from school without permission",
      "being locked up",
      "a feeling that someone deserves no respect",
    ]);
    expect(item.match_right.map((entry) => entry.text)).toEqual([
      "incarceration",
      "truancy",
      "contempt",
    ]);
    expect(item.answer_key.match_pairs).toHaveLength(3);
    expect(state.isDirty.value).toBe(true);
  });

  it("keys the item as teacher authored when pairs are chosen", async () => {
    const state = await openMatchingDocument();

    state.updateItemMatchPairs("item_001", [{ left_id: "left_001", right_id: "right_001" }]);

    expect(currentItem(state).answer_key).toEqual({
      correct_choice_ids: [],
      match_pairs: [{ left_id: "left_001", right_id: "right_001" }],
      origin: "teacher_authored",
    });
  });

  it("makes the key absent when every pair is cleared, and the save goes through", async () => {
    const state = await openMatchingDocument();
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildResponse());

    state.updateItemMatchPairs("item_001", []);

    expect(currentItem(state).answer_key.origin).toBe("absent");
    expect(currentItem(state).answer_key.match_pairs).toEqual([]);
    await expect(state.saveDocument()).resolves.toBe(true);
    expect(apiMocks.saveExamWorkspaceDocument).toHaveBeenCalledTimes(1);
  });

  it("refuses to save a keyed item that uses a right entry twice", async () => {
    const state = await openMatchingDocument();

    state.updateItemMatchPairs("item_001", [
      { left_id: "left_001", right_id: "right_002" },
      { left_id: "left_002", right_id: "right_002" },
      { left_id: "left_003", right_id: "right_003" },
    ]);

    await expect(state.saveDocument()).resolves.toBe(false);
    expect(apiMocks.saveExamWorkspaceDocument).not.toHaveBeenCalled();
  });

  it("refuses to save an empty entry text", async () => {
    const state = await openMatchingDocument();

    state.updateItemMatchEntryText("item_001", "right", "right_001", "");

    await expect(state.saveDocument()).resolves.toBe(false);
    expect(apiMocks.saveExamWorkspaceDocument).not.toHaveBeenCalled();
  });
});
