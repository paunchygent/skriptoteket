/**
 * Dirty state is the difference between the open copy and the saved exam
 * file (TASK-SKRIPT-40-04-14, one save model: every confirmed autosave step
 * updates the saved baseline through `noteStored`).
 *
 * Expected behavior:
 *   Dirty is true exactly while the copy differs from the last confirmed
 *   snapshot. An edit back to the saved value, or an edit that changes
 *   nothing, leaves the copy clean.
 */

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  NativeAnswerKeySuggestion,
} from "../../../api/examWorkspace";
import { buildMatchingItem } from "./examWorkspaceMatchingItem.specSupport";
import {
  openMatchingDocument as openWith,
} from "./useExamWorkspaceDocument.specSupport";

const apiMocks = vi.hoisted(() => ({
  getExamWorkspaceConversionStatus: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
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
});

type Pairs = Array<[string, string]>;

const SAVED_PAIRS: Pairs = [
  ["left_001", "right_001"],
  ["left_002", "right_002"],
  ["left_003", "right_003"],
];
const SAVED_TICK_POINTS = "1";
const CHANGED_TICK_POINTS = "2";

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
