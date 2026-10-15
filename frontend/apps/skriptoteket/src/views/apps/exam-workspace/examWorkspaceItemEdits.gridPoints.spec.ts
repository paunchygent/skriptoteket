/**
 * Exam workspace item edits, Kategorisera grid points after key transitions.
 *
 * Expected behavior:
 *   A grid's points are its tick value times its ticks, and an unkeyed grid
 *   has no points (Q10). Every route that replaces or clears the key keeps
 *   that total: undoing an interpreted key, an arriving suggestion becoming
 *   the key, and restoring a kept suggestion. A changed total is no longer an
 *   estimate; the tick value never changes.
 */

import { describe, expect, it } from "vitest";

import type { NativeAnswerKeySuggestion, NativeExamItem } from "../../../api/examWorkspace";
import {
  withArrivingSuggestion,
  withMatchPairs,
  withoutInterpretedKey,
  withRestoredSuggestion,
} from "./examWorkspaceItemEdits";
import { buildMatchingItem } from "./examWorkspaceMatchingItem.specSupport";

const FOUR_TICKS = [
  { left_id: "left_001", right_id: "right_002" },
  { left_id: "left_002", right_id: "right_001" },
  { left_id: "left_003", right_id: "right_003" },
  { left_id: "left_003", right_id: "right_001" },
];

function gridSuggestion(match_pairs = FOUR_TICKS): NativeAnswerKeySuggestion {
  return {
    correct_choice_ids: [],
    fingerprint: "b".repeat(64),
    gap_accepted_values: [],
    match_pairs,
    model: "model",
    prompt_template_version: "v1",
    provider_profile_id: "profile",
  };
}

function unkeyedGrid(): NativeExamItem {
  return buildMatchingItem({
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "absent" },
    points: null,
    review: { confidence: null, parse_origin: "llm_parsed", reasons: [], state: "review_required" },
    tick_points: "0.5",
  });
}

describe("grid points follow every key transition", () => {
  it("undoing an interpreted key leaves an unkeyed grid without points", () => {
    const interpreted = buildMatchingItem({
      answer_key: { ...buildMatchingItem().answer_key, origin: "ai_interpreted" },
      points_estimated: true,
    });

    const undone = withoutInterpretedKey(interpreted);

    expect(undone.answer_key.match_pairs).toEqual([]);
    expect(undone.points).toBeNull();
    expect(undone.points_estimated).toBe(false);
    expect(undone.tick_points).toBe("1");
  });

  it("an arriving suggestion on an unkeyed grid sets the points from its ticks", () => {
    const arrived = withArrivingSuggestion(unkeyedGrid(), gridSuggestion());

    expect(arrived.answer_key.origin).toBe("machine_proposed");
    expect(arrived.answer_key.match_pairs).toHaveLength(4);
    expect(arrived.points).toBe(2);
    expect(arrived.tick_points).toBe("0.5");
  });

  it("restoring a suggestion with another tick count re-derives the points", () => {
    const arrived = withArrivingSuggestion(unkeyedGrid(), gridSuggestion());
    const teacherKeyed = withMatchPairs(arrived, FOUR_TICKS.slice(0, 3));
    expect(teacherKeyed.points).toBe(1.5);

    const restored = withRestoredSuggestion(teacherKeyed);

    expect(restored.answer_key.match_pairs).toHaveLength(4);
    expect(restored.points).toBe(2);
    expect(restored.points_estimated).toBe(false);
  });
});
