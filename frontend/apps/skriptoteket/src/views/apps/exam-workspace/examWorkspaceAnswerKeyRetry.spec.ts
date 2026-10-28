/**
 * Undo of any AI answer key and the question's one retry (TASK-SKRIPT-40-04-26 D4, D5).
 *
 * Expected behavior:
 *   Undo removes an `ai_interpreted` or `machine_proposed` key and opens the
 *   question's one retry: the saved retry state goes from `none` to `offered`
 *   and stays as it is otherwise, so a spent retry stays spent. An arriving
 *   suggestion on a question whose retry is open spends it.
 */

import { describe, expect, it, vi } from "vitest";

import type { NativeAnswerKeySuggestion, NativeExamItem } from "../../../api/examWorkspace";
import { buildFreeTextItem } from "../../../test/examWorkspaceFixtures";
import {
  canUndoAiKey,
  newTeacherItem,
  reviewed,
  withoutAiKey,
  withCorrectChoices,
} from "./examWorkspaceItemEdits";
import { choiceItem, gapItem, keyedSuggestion } from "./examWorkspaceKeyedItems.specSupport";
import { withArrivingSuggestion } from "./examWorkspaceSuggestionEdits";
import { useExamWorkspaceItemEdits } from "./useExamWorkspaceItemEdits";

type RetryState = NativeExamItem["answer_key_retry"];

function retried(item: NativeExamItem, retry: RetryState): NativeExamItem {
  return { ...item, answer_key_retry: retry };
}

function priorSuggestion(): NativeAnswerKeySuggestion {
  return keyedSuggestion({ correct_choice_ids: ["choice_001"] });
}

describe("canUndoAiKey", () => {
  it.each(["ai_interpreted", "machine_proposed"] as const)("offers undo for a %s key", (origin) => {
    expect(canUndoAiKey(choiceItem("single_choice", origin, ["choice_001"], null))).toBe(true);
    expect(canUndoAiKey(gapItem(origin, [["gap_001", ["Stockholm"]]], null))).toBe(true);
  });

  it.each([
    "absent",
    "not_applicable",
    "source_provided",
    "teacher_authored",
    "reviewed_advisory",
  ] as const)("offers no undo for a %s key", (origin) => {
    expect(canUndoAiKey(choiceItem("single_choice", origin, ["choice_001"], null))).toBe(false);
  });

  it("offers no undo for an AI-interpreted dropdown, which has no keyless state", () => {
    const dropdown: NativeExamItem = {
      ...choiceItem("single_choice", "ai_interpreted", ["choice_001"], null),
      kind: "inline_choice",
    };
    expect(canUndoAiKey(dropdown)).toBe(false);
    expect(withoutAiKey(dropdown)).toBe(dropdown);
  });

  it("offers no undo once a teacher-reviewed key is in place", () => {
    expect(canUndoAiKey(reviewed(choiceItem("single_choice", "machine_proposed", ["choice_001"], null)))).toBe(false);
  });
});

describe("withoutAiKey", () => {
  it("clears an interpreted gap key, keeps the suggestion and opens the retry", () => {
    const suggestion = keyedSuggestion({ correct_choice_ids: [] });
    const source = retried(
      {
        ...gapItem("ai_interpreted", [["gap_001", ["Stockholm", "Sthlm"]]], suggestion),
        facit_text: "Sveriges huvudstad är Stockholm.",
        gaps: [{ ...gapItem("ai_interpreted", [["gap_001", ["Stockholm"]]], null).gaps[0]!, automatic_values: ["Stockhom"] }],
      },
      "none",
    );

    const undone = withoutAiKey(source);

    expect(undone.answer_key).toEqual({ origin: "absent", correct_choice_ids: [], match_pairs: [] });
    expect(undone.gaps[0]?.accepted_values).toEqual([]);
    expect(undone.gaps[0]?.automatic_values).toEqual([]);
    expect(undone.facit_text).toBe(source.facit_text);
    expect(undone.ai_suggestion).toBe(suggestion);
    expect(undone.answer_key_retry).toBe("offered");
  });

  it("clears a machine-proposed choice key and opens the retry", () => {
    const source = retried(choiceItem("single_choice", "machine_proposed", ["choice_001"], priorSuggestion()), "none");

    const undone = withoutAiKey(source);

    expect(undone.answer_key).toEqual({ origin: "absent", correct_choice_ids: [], match_pairs: [] });
    expect(undone.ai_suggestion).toBe(source.ai_suggestion);
    expect(undone.answer_key_retry).toBe("offered");
  });

  it("clears a used item's key and keeps the retry spent", () => {
    const source = retried(choiceItem("single_choice", "machine_proposed", ["choice_002"], priorSuggestion()), "used");

    const undone = withoutAiKey(source);

    expect(undone.answer_key.origin).toBe("absent");
    expect(undone.answer_key.correct_choice_ids).toEqual([]);
    expect(undone.answer_key_retry).toBe("used");
  });

  it("leaves a question without an AI key unchanged, whatever its retry state", () => {
    const teacher = retried(choiceItem("single_choice", "teacher_authored", ["choice_001"], null), "offered");
    const absent = retried(choiceItem("single_choice", "absent", [], null), "offered");

    expect(withoutAiKey(teacher)).toBe(teacher);
    expect(withoutAiKey(absent)).toBe(absent);
  });
});

describe("withArrivingSuggestion spends an open retry", () => {
  it("writes the key as machine_proposed on an offered keyless question and sets the retry used", () => {
    const item = retried(choiceItem("single_choice", "absent", [], null), "offered");
    const suggestion = keyedSuggestion({ correct_choice_ids: ["choice_002"] });

    const arrived = withArrivingSuggestion(item, suggestion);

    expect(arrived.answer_key).toEqual({
      correct_choice_ids: ["choice_002"],
      match_pairs: [],
      origin: "machine_proposed",
    });
    expect(arrived.review.state).toBe("review_required");
    expect(arrived.ai_suggestion).toBe(suggestion);
    expect(arrived.answer_key_retry).toBe("used");
  });

  it("keeps only the suggestion on an offered teacher-keyed question and still spends the retry", () => {
    const item = retried(choiceItem("single_choice", "teacher_authored", ["choice_001"], null), "offered");
    const suggestion = keyedSuggestion({ correct_choice_ids: ["choice_002"] });

    const arrived = withArrivingSuggestion(item, suggestion);

    expect(arrived.answer_key.origin).toBe("teacher_authored");
    expect(arrived.answer_key.correct_choice_ids).toEqual(["choice_001"]);
    expect(arrived.ai_suggestion).toBe(suggestion);
    expect(arrived.answer_key_retry).toBe("used");
  });

  it("leaves a question with no undo behind it at none", () => {
    const arrived = withArrivingSuggestion(
      retried(choiceItem("single_choice", "absent", [], null), "none"),
      keyedSuggestion({ correct_choice_ids: ["choice_002"] }),
    );

    expect(arrived.answer_key.origin).toBe("machine_proposed");
    expect(arrived.answer_key_retry).toBe("none");
  });

  it("leaves an already spent retry used", () => {
    const arrived = withArrivingSuggestion(
      retried(choiceItem("single_choice", "absent", [], null), "used"),
      keyedSuggestion({ correct_choice_ids: ["choice_002"] }),
    );

    expect(arrived.answer_key.origin).toBe("machine_proposed");
    expect(arrived.answer_key_retry).toBe("used");
  });
});

describe("undoItemAiKey", () => {
  it("patches the item once through patchItem as a structural edit", () => {
    const patchItem = vi.fn(
      (
        _itemId: string,
        _patch: (item: NativeExamItem) => NativeExamItem,
        _structural?: boolean,
      ): boolean => true,
    );
    const editing = useExamWorkspaceItemEdits(patchItem);
    const item = retried(choiceItem("single_choice", "machine_proposed", ["choice_001"], null), "none");

    editing.undoItemAiKey("item_001");

    expect(patchItem).toHaveBeenCalledTimes(1);
    const [itemId, patch, structural] = patchItem.mock.calls[0];
    expect(itemId).toBe("item_001");
    expect(structural).toBe(true);
    expect(patch(item)).toEqual(withoutAiKey(item));
    expect(patch(item).answer_key_retry).toBe("offered");
  });
});

describe("new questions start with the retry unused", () => {
  it("writes answer_key_retry none on a teacher-created question and a fixture item", () => {
    expect(newTeacherItem("item_001", 1, "single_choice").answer_key_retry).toBe("none");
    expect(buildFreeTextItem(1).answer_key_retry).toBe("none");
  });

  it("keeps the retry through a teacher key edit", () => {
    const undone = withoutAiKey(choiceItem("single_choice", "ai_interpreted", ["choice_001"], null));

    expect(withCorrectChoices(undone, ["choice_002"]).answer_key_retry).toBe("offered");
  });
});
