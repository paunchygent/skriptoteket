/**
 * Dirty state is the difference between the open copy and the last server
 * document (TASK-SKRIPT-39-04-07, repair 4 case space F).
 *
 * Expected behavior:
 *   Dirty is true exactly while the copy differs from the document the
 *   server last returned. Edits, arrivals and replays never raise or clear
 *   it on their own: an edit back to the saved value, an edit that changes
 *   nothing, or replayed arrivals that bring the copy back to the returned
 *   revision all leave a clean copy, and any remaining difference keeps it
 *   dirty.
 *
 * Rows follow case space F in the retained design note
 * `evidence/implementation/TASK-SKRIPT-39-04-07/repair4/design.md`.
 */

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../api/client";
import type {
  ExamWorkspaceDocumentResponse,
  NativeAnswerKeySuggestion,
} from "../../../api/examWorkspace";
import { buildMatchingItem } from "./examWorkspaceMatchingItem.specSupport";
import {
  currentDocument,
  currentItem,
  deferred,
  openingOf,
  openMatchingDocument as openWith,
  savedResponse,
} from "./useExamWorkspaceDocument.specSupport";

const apiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
}));

vi.mock("../../../api/examWorkspace", () => apiMocks);

beforeEach(() => {
  setActivePinia(createPinia());
  apiMocks.getExamWorkspaceDocument.mockReset();
  apiMocks.saveExamWorkspaceDocument.mockReset();
});

type Pairs = Array<[string, string]>;

const SAVED_PAIRS: Pairs = [
  ["left_001", "right_001"],
  ["left_002", "right_002"],
  ["left_003", "right_003"],
];
const OTHER_PAIRS: Pairs = [
  ["left_001", "right_003"],
  ["left_002", "right_002"],
  ["left_003", "right_001"],
];
const SAVED_TICK_POINTS = "1";
const CHANGED_TICK_POINTS = "2";
const SAVED_PAIRS_REORDERED: Pairs = [SAVED_PAIRS[2], SAVED_PAIRS[0], SAVED_PAIRS[1]];

function suggestion(pairs: Pairs): NativeAnswerKeySuggestion {
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

/** An unreviewed machine key equal to its kept suggestion, so each arrival becomes the key (P12). */
function openFollowingMachineKey() {
  const item = buildMatchingItem({
    ai_suggestion: suggestion(SAVED_PAIRS),
    answer_key: {
      correct_choice_ids: [],
      match_pairs: suggestion(SAVED_PAIRS).match_pairs,
      origin: "machine_proposed",
    },
  });
  return openWith(apiMocks.getExamWorkspaceDocument, {
    ...item,
    review: { ...item.review, state: "review_required" },
  });
}

function sentDocument() {
  return apiMocks.saveExamWorkspaceDocument.mock.calls[0][1].document;
}

/**
 * Edit the grid's tick value, save, and land two arrivals while the save is in
 * flight. Each arrival keeps three ticks, so the points stay at the edited total.
 */
async function saveWhileArrivalsLand(first: Pairs, second: Pairs) {
  const state = await openFollowingMachineKey();
  const pendingSave = deferred<ExamWorkspaceDocumentResponse>();
  apiMocks.saveExamWorkspaceDocument.mockReturnValue(pendingSave.promise);
  state.updateItemTickPoints("item_001", CHANGED_TICK_POINTS);
  const saving = state.saveDocument();
  state.applyArrivingSuggestions(openingOf(state), [{ item_id: "item_001", suggestion: suggestion(first) }]);
  state.applyArrivingSuggestions(openingOf(state), [{ item_id: "item_001", suggestion: suggestion(second) }]);
  return { pendingSave, saving, state };
}

describe("teacher edits", () => {
  it("F3: an edit back to the saved value leaves the copy clean", async () => {
    const state = await openFollowingMachineKey();

    state.updateItemTickPoints("item_001", CHANGED_TICK_POINTS);
    expect(state.isDirty.value).toBe(true);
    state.updateItemTickPoints("item_001", SAVED_TICK_POINTS);

    expect(state.isDirty.value).toBe(false);
  });

  it("F4: an edit that changes nothing leaves the copy clean", async () => {
    const state = await openFollowingMachineKey();

    state.updateItemTickPoints("item_001", SAVED_TICK_POINTS);

    expect(state.isDirty.value).toBe(false);
  });
});

describe("arrivals replayed after a save's outcome", () => {
  it("F9: arrivals that bring the copy back to the returned revision leave it clean (reviewer F12)", async () => {
    const { pendingSave, saving, state } = await saveWhileArrivalsLand(OTHER_PAIRS, SAVED_PAIRS);
    const sent = sentDocument();

    pendingSave.resolve(savedResponse(sent));
    expect(await saving).toBe(true);

    expect(currentDocument(state)).toEqual(sent);
    expect(state.isDirty.value).toBe(false);
  });

  it("F10: arrivals that rebuild an equal key in another order keep it dirty", async () => {
    const { pendingSave, saving, state } = await saveWhileArrivalsLand(
      OTHER_PAIRS,
      SAVED_PAIRS_REORDERED,
    );

    pendingSave.resolve(savedResponse(sentDocument()));
    await saving;

    expect(currentItem(state).answer_key.match_pairs).toEqual(
      suggestion(SAVED_PAIRS_REORDERED).match_pairs,
    );
    expect(state.isDirty.value).toBe(true);
  });

  it("F13: arrivals that net to the head reloaded after a conflict leave it clean", async () => {
    const { pendingSave, saving, state } = await saveWhileArrivalsLand(OTHER_PAIRS, SAVED_PAIRS);
    const head = savedResponse(sentDocument());
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(head);

    pendingSave.reject(new ApiError({ code: "CONFLICT", message: "Konflikt", status: 409 }));
    await saving;

    expect(currentDocument(state)).toEqual(head.document);
    expect(state.isDirty.value).toBe(false);
  });

  it("F8: one arrival that changed the returned revision keeps it dirty", async () => {
    const state = await openFollowingMachineKey();
    const pendingSave = deferred<ExamWorkspaceDocumentResponse>();
    apiMocks.saveExamWorkspaceDocument.mockReturnValue(pendingSave.promise);
    const saving = state.saveDocument();
    state.applyArrivingSuggestions(openingOf(state), [{ item_id: "item_001", suggestion: suggestion(OTHER_PAIRS) }]);

    pendingSave.resolve(savedResponse(sentDocument()));
    await saving;

    expect(currentItem(state).answer_key.match_pairs).toEqual(suggestion(OTHER_PAIRS).match_pairs);
    expect(state.isDirty.value).toBe(true);
  });

  it("F11: a failed save keeps the unsaved copy dirty", async () => {
    const state = await openFollowingMachineKey();
    apiMocks.saveExamWorkspaceDocument.mockRejectedValue(new Error("network down"));
    state.updateItemTickPoints("item_001", CHANGED_TICK_POINTS);

    expect(await state.saveDocument()).toBe(false);

    expect(state.isDirty.value).toBe(true);
  });
});
