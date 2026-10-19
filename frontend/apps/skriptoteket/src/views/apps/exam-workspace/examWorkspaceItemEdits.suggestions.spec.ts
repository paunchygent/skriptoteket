/**
 * AI answer-key suggestions kept on each question (TASK-SKRIPT-39-04-07).
 *
 * Expected behavior (T5, T6):
 *   An arriving suggestion is kept on its question and becomes the key —
 *   `machine_proposed`, review required — only where the question has no
 *   key or its key is an unreviewed `machine_proposed` key equal to the
 *   previous suggestion (P12; full matrix in
 *   `examWorkspaceItemEdits.arrivalRule.spec.ts`). Marking reviewed turns
 *   a `machine_proposed` key into `reviewed_advisory`; choosing another
 *   option makes the key `teacher_authored` and keeps the suggestion;
 *   restoring makes the suggestion the key again as `machine_proposed`.
 */

import { describe, expect, it } from "vitest";

import type { NativeAnswerKeySuggestion, NativeExamItem } from "../../../api/examWorkspace";
import { reviewed, withCorrectChoices } from "./examWorkspaceItemEdits";
import { buildGap, gapSuggestion } from "./examWorkspaceKeyedItems.specSupport";
import { plainBody } from "./examWorkspaceRichText";
import { withArrivingSuggestion, withRestoredSuggestion } from "./examWorkspaceSuggestionEdits";

function choiceItem(
  origin: NativeExamItem["answer_key"]["origin"],
  correctChoiceIds: string[] = [],
): NativeExamItem {
  return {
    ai_suggestion: null,
    facit_text: null,
    import_record: null,
    criteria: [],
    printed_label: null,
    print_order: [],
    retry_source: null,
    answer_key: { correct_choice_ids: correctChoiceIds, match_pairs: [], origin },
    body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Vilket är huvudordet?" }] }],
    choices: [
      { choice_id: "choice_001", body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "vägen" }] }] },
      { choice_id: "choice_002", body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "eleverna" }] }] },
    ],
    gaps: [],
    item_id: "item_001",
    kind: "single_choice",
    match_left: [],
    match_right: [],
    points: 1,
    points_estimated: false,
    review: {
      confidence: null,
      parse_origin: "teacher_created",
      reasons: [],
      state: "review_complete",
    },
    sequence: 1,
    source_anchor: null,
    source_points: null,
    suggested_kind: null,
    tick_points: null,
    writing_lines: null,
  };
}

function suggestion(choiceId: string): NativeAnswerKeySuggestion {
  return {
    correct_choice_ids: [choiceId],
    fingerprint: "a".repeat(64),
    gap_accepted_values: [],
    match_pairs: [],
    model: "model",
    prompt_template_version: "v1",
    provider_profile_id: "profile",
  };
}

describe("withArrivingSuggestion", () => {
  it("becomes the key on a keyless question and is kept on it", () => {
    const arrived = withArrivingSuggestion(choiceItem("absent"), suggestion("choice_002"));

    expect(arrived.answer_key).toEqual({
      correct_choice_ids: ["choice_002"],
      match_pairs: [],
      origin: "machine_proposed",
    });
    expect(arrived.review.state).toBe("review_required");
    expect(arrived.ai_suggestion?.correct_choice_ids).toEqual(["choice_002"]);
  });

  it.each(["teacher_authored", "source_provided", "reviewed_advisory"] as const)(
    "never overwrites a %s key but keeps the suggestion",
    (origin) => {
      const item = choiceItem(origin, ["choice_001"]);

      const arrived = withArrivingSuggestion(item, suggestion("choice_002"));

      expect(arrived.answer_key.origin).toBe(origin);
      expect(arrived.answer_key.correct_choice_ids).toEqual(["choice_001"]);
      expect(arrived.review.state).toBe("review_complete");
      expect(arrived.ai_suggestion?.correct_choice_ids).toEqual(["choice_002"]);
    },
  );

  it("replaces a key that is the previous suggestion's key", () => {
    const first = withArrivingSuggestion(choiceItem("absent"), suggestion("choice_002"));

    const second = withArrivingSuggestion(first, suggestion("choice_001"));

    expect(second.answer_key.origin).toBe("machine_proposed");
    expect(second.answer_key.correct_choice_ids).toEqual(["choice_001"]);
  });
});

describe("review, teacher choice and restore (T6)", () => {
  it("marking reviewed turns machine_proposed into reviewed_advisory and keeps the suggestion", () => {
    const arrived = withArrivingSuggestion(choiceItem("absent"), suggestion("choice_002"));

    const marked = reviewed(arrived);

    expect(marked.answer_key.origin).toBe("reviewed_advisory");
    expect(marked.review.state).toBe("review_complete");
    expect(marked.ai_suggestion?.correct_choice_ids).toEqual(["choice_002"]);
  });

  it("choosing another option makes the key teacher_authored and keeps the suggestion", () => {
    const arrived = withArrivingSuggestion(choiceItem("absent"), suggestion("choice_002"));

    const chosen = withCorrectChoices(arrived, ["choice_001"]);

    expect(chosen.answer_key.origin).toBe("teacher_authored");
    expect(chosen.ai_suggestion?.correct_choice_ids).toEqual(["choice_002"]);
  });

  it("restoring makes the suggestion the key again as machine_proposed, review required", () => {
    const arrived = withArrivingSuggestion(choiceItem("absent"), suggestion("choice_002"));
    const chosen = withCorrectChoices(arrived, ["choice_001"]);

    const restored = withRestoredSuggestion(chosen);

    expect(restored.answer_key.origin).toBe("machine_proposed");
    expect(restored.answer_key.correct_choice_ids).toEqual(["choice_002"]);
    expect(restored.review.state).toBe("review_required");
    expect(restored.ai_suggestion?.correct_choice_ids).toEqual(["choice_002"]);
  });

  it("restoring a retained typed-gap suggestion preserves an inline-choice key and review", () => {
    const retainedSuggestion = gapSuggestion([["gap_001", ["Ada"]]]);
    const options = [
      { choice_id: "choice_001", body: plainBody("Ada") },
      { choice_id: "choice_002", body: plainBody("Elsa") },
    ];
    const item: NativeExamItem = {
      ...choiceItem("teacher_authored"),
      ai_suggestion: retainedSuggestion,
      body: [{ heading_level: null, segments: [
        { kind: "text", marks: [], text: "Hon heter " },
        { kind: "gap", gap_id: "gap_001" },
      ] }],
      choices: [],
      gaps: [buildGap("gap_001", [], { options, correct_option_id: "choice_001" })],
      kind: "inline_choice",
    };

    const restored = withRestoredSuggestion(item);

    expect(restored).toBe(item);
    expect(restored.answer_key).toEqual({
      correct_choice_ids: [],
      match_pairs: [],
      origin: "teacher_authored",
    });
    expect(restored.gaps).toEqual([
      buildGap("gap_001", [], { options, correct_option_id: "choice_001" }),
    ]);
    expect(restored.review).toEqual({
      confidence: null,
      parse_origin: "teacher_created",
      reasons: [],
      state: "review_complete",
    });
    expect(restored.ai_suggestion).toBe(retainedSuggestion);
    expect(restored.ai_suggestion).toEqual(gapSuggestion([["gap_001", ["Ada"]]]));
  });

  it("restoring without a suggestion changes nothing", () => {
    const item = choiceItem("teacher_authored", ["choice_001"]);
    expect(withRestoredSuggestion(item)).toBe(item);
  });
});
