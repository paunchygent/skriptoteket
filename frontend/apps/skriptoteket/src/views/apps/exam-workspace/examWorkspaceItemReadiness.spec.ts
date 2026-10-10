/**
 * Exam workspace per-item export readiness.
 *
 * Expected behavior:
 *   Each question reports the same reasons the server export gate refuses
 *   with (review required, unreviewed machine key, keyed question without a
 *   key, missing points) plus the states the save refuses (a partial gap
 *   key, points not greater than zero, a choice without text), in a stable
 *   order; ready
 *   questions report nothing and are left out of the per-item copy map.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import {
  examWorkspaceItemReadiness,
  examWorkspaceReadinessByItemId,
} from "./examWorkspaceItemReadiness";
import { PARTIAL_GAP_KEY_GUIDANCE } from "./examWorkspaceAnswerKeyRules";

function buildChoiceItem(overrides: Partial<NativeExamItem> = {}): NativeExamItem {
  return {
    answer_key: { correct_choice_ids: ["choice_a"], origin: "teacher_authored" },
    body: [{ segments: [{ kind: "text", text: "Vilket ämne är en gas?" }] }],
    choices: [
      { choice_id: "choice_a", text: "Syre" },
      { choice_id: "choice_b", text: "Järn" },
    ],
    gaps: [],
    item_id: "item_001",
    kind: "single_choice",
    points: 1,
    review: {
      confidence: 0.95,
      parse_origin: "deterministic",
      reasons: [],
      state: "review_complete",
    },
    sequence: 1,
    source_anchor: null,
    title: "Gaser",
    ...overrides,
  };
}

describe("examWorkspaceItemReadiness", () => {
  it("reports nothing for a reviewed, keyed question with points", () => {
    expect(examWorkspaceItemReadiness(buildChoiceItem())).toEqual([]);
  });

  it("reports every server gate reason in order", () => {
    const item = buildChoiceItem({
      answer_key: { correct_choice_ids: ["choice_a"], origin: "machine_proposed" },
      points: null,
      review: {
        confidence: 0.4,
        parse_origin: "llm_parsed",
        reasons: [],
        state: "review_required",
      },
    });

    expect(examWorkspaceItemReadiness(item)).toEqual([
      "review_required",
      "machine_proposed_key_unreviewed",
      "missing_points",
    ]);
  });

  it("reports a missing key only for keyed kinds", () => {
    const keyed = buildChoiceItem({
      answer_key: { correct_choice_ids: [], origin: "absent" },
    });
    const freeText = buildChoiceItem({
      answer_key: { correct_choice_ids: [], origin: "not_applicable" },
      choices: [],
      kind: "free_text",
    });

    expect(examWorkspaceItemReadiness(keyed)).toEqual(["missing_answer_key"]);
    expect(examWorkspaceItemReadiness(freeText)).toEqual([]);
  });

  it("reports a partial gap key", () => {
    const item = buildChoiceItem({
      choices: [],
      gaps: [
        { accepted_values: ["100"], gap_id: "gap_001", hint: null },
        { accepted_values: [], gap_id: "gap_002", hint: null },
      ],
      kind: "gap_fill",
    });

    expect(examWorkspaceItemReadiness(item)).toEqual(["partial_gap_key"]);
  });

  it("reports points that are not greater than zero, but not missing points twice", () => {
    expect(examWorkspaceItemReadiness(buildChoiceItem({ points: 0 }))).toEqual([
      "non_positive_points",
    ]);
    expect(examWorkspaceItemReadiness(buildChoiceItem({ points: -2 }))).toEqual([
      "non_positive_points",
    ]);
    expect(examWorkspaceItemReadiness(buildChoiceItem({ points: 0.5 }))).toEqual([]);
  });

  it("reports a choice without text, and accepts whitespace as the server does", () => {
    const empty = buildChoiceItem({
      choices: [
        { choice_id: "choice_a", text: "Syre" },
        { choice_id: "choice_b", text: "" },
      ],
    });
    const blank = buildChoiceItem({
      choices: [
        { choice_id: "choice_a", text: "Syre" },
        { choice_id: "choice_b", text: " " },
      ],
    });

    expect(examWorkspaceItemReadiness(empty)).toEqual(["empty_choice_text"]);
    expect(examWorkspaceItemReadiness(blank)).toEqual([]);
  });
});

describe("examWorkspaceReadinessByItemId", () => {
  it("maps only questions that stop an export to Swedish copy", () => {
    const ready = buildChoiceItem();
    const partial = buildChoiceItem({
      choices: [],
      gaps: [{ accepted_values: [], gap_id: "gap_001", hint: null }],
      item_id: "item_002",
      kind: "gap_fill",
      points: null,
      sequence: 2,
    });

    expect(examWorkspaceReadinessByItemId([ready, partial])).toEqual({
      item_002: [PARTIAL_GAP_KEY_GUIDANCE, "Poäng saknas."],
    });
  });

  it("maps the save-refused states to their Swedish copy", () => {
    const item = buildChoiceItem({
      choices: [
        { choice_id: "choice_a", text: "Syre" },
        { choice_id: "choice_b", text: "" },
      ],
      points: 0,
    });

    expect(examWorkspaceReadinessByItemId([item])).toEqual({
      item_001: ["Poängen måste vara större än noll.", "Ett svarsalternativ saknar text."],
    });
  });
});
